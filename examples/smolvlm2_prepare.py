#!/usr/bin/env python3
"""Create AXCL AXLLM 8501c22b configuration for SmolVLM2-256M video weights."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
model=a.model_dir.resolve();out=a.output.resolve()
weight=model/'SmolVLM2-256M-Video-Instruct_Ax650-C128-P768-CTX1024'
names=[f'llama_p128_l{i}_together.axmodel' for i in range(30)]+['llama_post.axmodel','model.embed_tokens.weight.bfloat16.bin','vision_model_1x3x512x512_256M_NHwC_U8.axmodel']
files=[(weight/n,n) for n in names]+[(model/'smolvlm2_tokenizer.txt','smolvlm2_tokenizer.txt')]
if not all(f.is_file() and f.stat().st_size for f,_ in files):raise FileNotFoundError('Missing model or tokenizer files')
out.mkdir(parents=True,exist_ok=False)
for source,name in files:(out/name).symlink_to(source)
config={'model_name':'AXERA-TECH/SmolVLM2-256M-Video-Instruct_Ax650','system_prompt':'',
 'url_tokenizer_model':'smolvlm2_tokenizer.txt','tokenizer_type':'SmolVLM2','post_config_path':'post_config.json',
 'template_filename_axmodel':'llama_p128_l%d_together.axmodel','axmodel_num':30,
 'filename_post_axmodel':'llama_post.axmodel','filename_tokens_embed':'model.embed_tokens.weight.bfloat16.bin',
 'tokens_embed_num':49280,'tokens_embed_size':576,'use_mmap_load_embed':True,'use_mmap_load_layer':True,
 'vlm_type':'SmolVLM2','filename_image_encoder_axmodel':'vision_model_1x3x512x512_256M_NHwC_U8.axmodel',
 'vision_width':512,'vision_height':512,'vision_fps':1,'vision_cache_dir':'vision_cache','devices':[0]}
post={'enable_temperature':False,'temperature':0.7,'enable_repetition_penalty':False,'repetition_penalty':1,'penalty_window':30,
 'enable_top_p_sampling':False,'top_p':0.8,'enable_top_k_sampling':True,'top_k':1}
(out/'config.json').write_text(json.dumps(config,indent=2)+'\n')
(out/'post_config.json').write_text(json.dumps(post,indent=2)+'\n')
print('Created AXCL runtime directory:',out)
