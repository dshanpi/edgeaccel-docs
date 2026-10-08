"""Convert the pinned Qwen3-Embedding-0.6B GPTQ-Int8 source in Pulsar2 7.0-patch1.

Run in the documented container. Reusing decoder outputs requires the exact
published SHA-256 manifest; no partial decoder set is accepted.
"""
import argparse
import dataclasses
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def post_norm(source, output):
    import numpy as np
    import axnn.yasched.llm_builder.llm_utils as u
    import axnn.yasched.llm_builder.qwen3_test as q

    raw = json.loads((source / 'config.json').read_text())
    config = u.Config(**{f.name: raw[f.name] for f in dataclasses.fields(u.Config) if f.name in raw})
    config.model_name = str(source)
    require((config.hidden_size, config.num_hidden_layers, config.vocab_size, config.rms_norm_eps)
            == (1024, 28, 151669, 1e-6), 'Source architecture differs.')
    loader = q.AttrsLoader(u.WeightLoader(source), config)
    attributes = loader.get_attrs('post_norm', 0, 'fp32')
    digest = hashlib.sha256(attributes['scale'].tobytes()).hexdigest()
    require(digest == '7b636f97927d28c622ec9655207d7d4c47aea32bab0a0fefa011e7a45bb31329',
            'Original final RMSNorm weight differs.')
    require(np.array_equal(attributes['bias'], np.zeros(1024, np.float32)), 'Unexpected norm bias.')
    graph = q.build_post_layer(1, batch=1, topk=0, post_weight_type='bf16',
                              m_type=q.datatype.bf16, al=loader, cfg=config)
    require(len(graph.ops) == 2 and 'RMSNorm' in str(graph.ops[0]) and
            'FullyConnected' in str(graph.ops[1]), 'Compiler post graph changed.')
    name = graph.ops[0].outputs_spec['r']
    norm = graph.extract_subgraph(['input'], [name])
    require(len(norm.ops) == 1 and set(norm.tensors) == {'input', name}, 'Unexpected norm graph.')
    tensor = norm.tensors.pop(name)
    require(tuple(tensor.shape) == (1, 1, 1024), 'Unexpected norm shape.')
    tensor.name = 'output_norm'
    norm.tensors['output_norm'] = tensor
    norm.ops[0].outputs_spec['r'] = 'output_norm'
    norm.outputs = ['output_norm']
    norm.ddr_tensor = {'input', 'output_norm'}
    backend_enum = type(inspect.signature(u.run).parameters['be_type'].default)
    backend = next(value for value in backend_enum if value.value == 'AX650')

    def build(count):
        require(count == 1, 'Expected one final valid token.')
        return norm.copy()

    u.dump_post_layer(output, build, 'qwen3', backend, N=1)


def embedding(source, output):
    with (source / 'model.safetensors').open('rb') as stream:
        header_length = struct.unpack('<Q', stream.read(8))[0]
        header = json.loads(stream.read(header_length))
        tensor = header['model.embed_tokens.weight']
        require(tensor['dtype'] == 'BF16' and tensor['shape'] == [151669, 1024], 'Embedding shape differs.')
        start, end = tensor['data_offsets']
        require(end - start == 310618112, 'Embedding length differs.')
        stream.seek(8 + header_length + start)
        with output.open('wb') as target:
            remaining = end - start
            while remaining:
                block = stream.read(min(8 * 1024 * 1024, remaining))
                require(bool(block), 'Source embedding is truncated.')
                target.write(block)
                remaining -= len(block)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decoder-cache', type=Path,
                        help='Optional previously compiled 28 decoders; all published hashes must match.')
    args = parser.parse_args()
    require(os.environ.get('PULSAR2_VERSION') == '7.0-patch1' and
            os.environ.get('PULSAR2_COMMIT') == '29f4c81a', 'Use the documented compiler image.')
    manifest = json.loads(Path(__file__).with_name('tested-package.json').read_text())
    expected = {row['file']: row for row in manifest['files']}
    source = args.source.resolve()
    for row in manifest['sourceFiles']:
        require(sha(source / row['path']) == row['sha256'], 'Source checksum differs: ' + row['path'])
    args.output.mkdir(parents=True, exist_ok=False)
    package = args.output / 'package'
    package.mkdir()
    decoder_names = [f'qwen3_p128_l{i}_together.axmodel' for i in range(28)]
    command = ['/opt/pulsar2/pulsar2', 'llm_build2', '--input_path', str(source),
               '--output_path', str(args.output / 'decoder-build'), '--hidden_state_type', 'bf16',
               '--weight_type', 's8', '--post_weight_type', 'bf16', '--max_context', '1024',
               '--prefill_len', '512', '--prefill_step_size', '128', '--chip', 'AX650',
               '--parallel', '1', '--ret_postnorm', '--check_level', '0']
    exit_code = None
    if args.decoder_cache:
        decoder_dir = args.decoder_cache.resolve()
    else:
        print('Compiling all 28 decoder layers. Follow decoder-build.log for progress.', flush=True)
        with (args.output / 'decoder-build.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        exit_code = result.returncode
        if exit_code != 0:
            log = (args.output / 'decoder-build.log').read_text()
            require(exit_code == 1 and 'dump_post_layer' in log and
                    'TileFailException: AxFullyConnected' in log and "'shape': (151669, 1024)" in log,
                    'Decoder build failed. Inspect decoder-build.log; no package was accepted.')
        decoder_dir = args.output / 'decoder-build'
    # Check every original layer before compiling the task-specific final RMSNorm.
    for name in decoder_names:
        require((decoder_dir / name).stat().st_size == expected[name]['bytes'], 'Incomplete decoder: ' + name)
        if args.decoder_cache:
            require(sha(decoder_dir / name) == expected[name]['sha256'], 'Cached decoder checksum differs: ' + name)
        shutil.copyfile(decoder_dir / name, package / name)
    norm_dir = args.output / 'norm-build'
    norm_dir.mkdir()
    post_norm(source, norm_dir)
    shutil.copyfile(norm_dir / 'qwen3_post.axmodel', package / 'qwen3_post.axmodel')
    embedding(source, package / 'model.embed_tokens.weight.bfloat16.bin')
    shutil.copyfile(source / 'tokenizer.json', package / 'tokenizer.json')
    produced = []
    for name, row in expected.items():
        require((package / name).stat().st_size == row['bytes'], 'Package size differs: ' + name)
        digest = sha(package / name)
        if not name.endswith('.axmodel'):
            require(digest == row['sha256'], 'Original tokenizer or embedding bytes differ: ' + name)
        produced.append(dict(file=name, bytes=row['bytes'], sha256=digest))
    for row in manifest['sourceFiles']:
        require(sha(source / row['path']) == row['sha256'], 'Source changed during conversion.')
    # Compiler scheduling is not byte-deterministic. Record newly generated hashes;
    # the documented card-side examples remain required after a fresh conversion.
    (package / 'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['file']}\n" for r in produced))
    report = dict(completed=True, sourceRevision=manifest['sourceRevision'], files=produced,
                  compiler=manifest['compiler'], decoderCommand=command, decoderExitCode=exit_code,
                  reusedVerifiedDecoders=bool(args.decoder_cache), layers=28, dimensions=1024, maxTokens=512,
                  finalOutput='Original final RMSNorm, last valid token, followed by host L2 normalization')
    (args.output / 'conversion.json').write_text(json.dumps(report, indent=2) + '\n')
    print('READY: ' + str(package), flush=True)


if __name__ == '__main__':
    main()
