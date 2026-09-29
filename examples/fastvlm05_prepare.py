#!/usr/bin/env python3
"""Create an AXLLM 8501c22b config for the official FastVLM-0.5B AX650 files.

Creates symlinks in a new directory; does not change downloaded weights.
"""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
model=a.model_dir.resolve();out=a.output.resolve()
weight=model/'fastvlm_C128_CTX1024_P640_ax650'
files=[(weight/f'llava_qwen2_p128_l{i}_together.axmodel',f'llava_qwen2_p128_l{i}_together.axmodel') for i in range(24)]
files += [(weight/'llava_qwen2_post.axmodel','llava_qwen2_post.axmodel'),
          (weight/'image_encoder_512x512_0.5b_ax650.axmodel','image_encoder_512x512_0.5b_ax650.axmodel'),
          (model/'embeds/model.embed_tokens.weight.bfloat16.bin','model.embed_tokens.weight.bfloat16.bin'),
          (model/'FastVLM_tokenizer.txt','FastVLM_tokenizer.txt')]
assert all(f.is_file() and f.stat().st_size>0 for f,_ in files),'Missing model/tokenizer files'
out.mkdir(parents=True,exist_ok=False)
for path,name in files:(out/name).symlink_to(path)
config={'model_name':'AXERA-TECH/FastVLM-0.5B','system_prompt':'You are a helpful assistant, created by apple company.',
 'url_tokenizer_model':'FastVLM_tokenizer.txt','tokenizer_type':'FastVLM','post_config_path':'post_config.json',
 'template_filename_axmodel':'llava_qwen2_p128_l%d_together.axmodel','axmodel_num':24,
 'filename_post_axmodel':'llava_qwen2_post.axmodel','filename_tokens_embed':'model.embed_tokens.weight.bfloat16.bin',
 'tokens_embed_num':151647,'tokens_embed_size':896,'use_mmap_load_embed':True,'use_mmap_load_layer':True,
 'vlm_type':'FastVLM','filename_image_encoder_axmodel':'image_encoder_512x512_0.5b_ax650.axmodel',
 'vision_width':512,'vision_height':512,'vision_patch_size':14,'vision_temporal_patch_size':1,
 'vision_spatial_merge_size':1,'vision_fps':1,'vision_tokens_per_second':1,'vision_cache_dir':'vision_cache','devices':[0]}
post=json.loads((model/'post_config.json').read_text())
post.update(enable_temperature=False,enable_repetition_penalty=False,enable_top_p_sampling=False,enable_top_k_sampling=True,top_k=1)
(out/'config.json').write_text(json.dumps(config,indent=2)+'\n')
(out/'post_config.json').write_text(json.dumps(post,indent=2)+'\n')
print('Created AXLLM runtime directory:',out)
