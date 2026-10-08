#!/usr/bin/env python3
"""Create an AXLLM 8501c22b config for the official FastVLM-1.5B AX650 files.

Creates symlinks in a new directory; does not change downloaded weights.
"""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--image-size',type=int,choices=[512,1024],default=1024);a=p.parse_args()
model=a.model_dir.resolve();out=a.output.resolve()
weight=model/'fastvlm_ax650_context_1k_prefill_640'
files=[(weight/f'llava_qwen2_p128_l{i}_together.axmodel',f'llava_qwen2_p128_l{i}_together.axmodel') for i in range(28)]
files += [(weight/'llava_qwen2_post.axmodel','llava_qwen2_post.axmodel'),
          (weight/f'image_encoder_{a.image_size}x{a.image_size}.axmodel',f'image_encoder_{a.image_size}x{a.image_size}.axmodel'),
          (weight/'model.embed_tokens.weight.bfloat16.bin','model.embed_tokens.weight.bfloat16.bin'),
          (model/'FastVLM_tokenizer.txt','FastVLM_tokenizer.txt')]
assert all(f.is_file() and f.stat().st_size>0 for f,_ in files),'Missing model/tokenizer files'
out.mkdir(parents=True,exist_ok=False)
for path,name in files:(out/name).symlink_to(path)
config={'model_name':'AXERA-TECH/FastVLM-1.5B','system_prompt':'You are a helpful assistant, created by apple company.',
 'url_tokenizer_model':'FastVLM_tokenizer.txt','tokenizer_type':'FastVLM','post_config_path':'post_config.json',
 'template_filename_axmodel':'llava_qwen2_p128_l%d_together.axmodel','axmodel_num':28,
 'filename_post_axmodel':'llava_qwen2_post.axmodel','filename_tokens_embed':'model.embed_tokens.weight.bfloat16.bin',
 'tokens_embed_num':151647,'tokens_embed_size':1536,'use_mmap_load_embed':True,'use_mmap_load_layer':True,
 'vlm_type':'FastVLM','filename_image_encoder_axmodel':f'image_encoder_{a.image_size}x{a.image_size}.axmodel',
 'vision_width':a.image_size,'vision_height':a.image_size,'vision_patch_size':14,'vision_temporal_patch_size':1,
 'vision_spatial_merge_size':1,'vision_fps':1,'vision_tokens_per_second':1,'vision_cache_dir':'vision_cache','devices':[0]}
post=json.loads((model/'post_config.json').read_text())
post.update(enable_temperature=False,enable_repetition_penalty=False,enable_top_p_sampling=False,enable_top_k_sampling=True,top_k=1)
(out/'config.json').write_text(json.dumps(config,indent=2)+'\n')
(out/'post_config.json').write_text(json.dumps(post,indent=2)+'\n')
print('Created AXLLM runtime directory:',out)
