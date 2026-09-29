#!/usr/bin/env python3
"""Prepare the official Qwen3-VL-8B Int4 files for AXCL commit 3be4cc3f.

Creates an isolated directory and native-tokenizer launchers. Weights are linked,
not copied or modified. This configuration was tested on an AX8850 16GB card.
"""
import argparse
import json
import shlex
from pathlib import Path


def prepare(model, binary, tokenizer, output):
    model, binary, tokenizer, output = map(lambda p: Path(p).resolve(), (model, binary, tokenizer, output))
    weight = 'Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4'
    required = [model / weight / f'qwen3_vl_text_p128_l{i}_together.axmodel' for i in range(36)]
    required += [model / weight / name for name in [
        'qwen3_vl_text_post.axmodel', 'Qwen3-VL-8B-Instruct_vision.axmodel',
        'model.embed_tokens.weight.bfloat16.bin']]
    required += [model / 'post_config.json', binary, tokenizer]
    missing = [str(p) for p in required if not p.is_file() or not p.stat().st_size]
    if missing:
        raise FileNotFoundError('Missing files: ' + ', '.join(missing))
    post = json.loads((model / 'post_config.json').read_text())
    post.update(enable_temperature=False, enable_repetition_penalty=False,
                enable_top_p_sampling=False, enable_top_k_sampling=True, top_k=1)
    output.mkdir(parents=True, exist_ok=False)
    for name in [weight, 'images', 'video']:
        if (model / name).is_dir():
            (output / name).symlink_to(model / name, target_is_directory=True)
    (output / 'post_config.json').write_text(json.dumps(post, indent=2) + '\n')
    base = [str(binary),
            '--template_filename_axmodel', f'{weight}/qwen3_vl_text_p128_l%d_together.axmodel',
            '--axmodel_num', '36', '--filename_image_encoder_axmodedl', f'{weight}/Qwen3-VL-8B-Instruct_vision.axmodel',
            '--use_mmap_load_embed', '1', '--filename_tokenizer_model', str(tokenizer),
            '--filename_post_axmodel', f'{weight}/qwen3_vl_text_post.axmodel',
            '--filename_tokens_embed', f'{weight}/model.embed_tokens.weight.bfloat16.bin',
            '--tokens_embed_num', '151936', '--tokens_embed_size', '4096',
            '--patch_size', '16', '--live_print', '0', '--img_width', '384', '--img_height', '384',
            '--vision_start_token_id', '151652', '--post_config_path', 'post_config.json', '--devices', '0']
    for mode, flag in [('image', '0'), ('video', '1')]:
        command = base + ['--video', flag]
        (output / f'command-{mode}.json').write_text(json.dumps(command, indent=2) + '\n')
        launcher = '#!/usr/bin/env bash\nset -euo pipefail\n'
        launcher += 'cd -- ' + shlex.quote(str(output)) + '\n'
        launcher += "export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1\n"
        launcher += "export NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost\n"
        launcher += "exec 9>.inference.lock\nflock -n 9 || { echo 'Another session is running.' >&2; exit 1; }\n"
        launcher += 'exec ' + shlex.join(command) + '\n'
        (output / f'run_{mode}.sh').write_text(launcher)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['model-dir', 'binary', 'tokenizer', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    directory = prepare(args.model_dir, args.binary, args.tokenizer, args.output)
    print('Created:', directory)
    print('Image: bash', shlex.quote(str(directory / 'run_image.sh')))
    print('Video: bash', shlex.quote(str(directory / 'run_video.sh')))
