## 准备分词服务

使用模型仓库内的 `main_axcl_aarch64` 通过 AXCL 在 M.2 算力卡上推理。Python 服务只负责分词：

```bash
python3 -m venv ~/edgeaccel/legacy-text-env
source ~/edgeaccel/legacy-text-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

确认没有缺失的动态库，再设置与本页效果一致的采样参数：

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path('post_config.json')
backup = p.with_suffix('.json.upstream')
if not backup.exists():
    backup.write_bytes(p.read_bytes())
config = json.loads(p.read_text())
config.update(enable_temperature=False, enable_repetition_penalty=False,
              enable_top_p_sampling=False, enable_top_k_sampling=True, top_k=1)
p.write_text(json.dumps(config, indent=2) + '\n')
PY
python qwen2.5_tokenizer.py --host 127.0.0.1 --port 12345
```

保持分词服务运行。该版本使用非 UID 的 HTTP 分词接口，须配套使用本仓库的程序和 tokenizer。

## 运行单轮问答

另开终端，进入模型目录。下面关闭连续对话，每次命令完成一条问题：

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-1-5b-instruct-gptq-int4/01d5a6eb90d9
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
./main_axcl_aarch64 \
  --template_filename_axmodel 'qwen2.5-1.5b-gptq-int4-ax650/qwen2_p128_l%d_together.axmodel' \
  --axmodel_num 28 --tokenizer_type 2 \
  --filename_tokenizer_model http://127.0.0.1:12345 \
  --bos 0 --eos 0 \
  --filename_post_axmodel qwen2.5-1.5b-gptq-int4-ax650/qwen2_post.axmodel \
  --filename_tokens_embed qwen2.5-1.5b-gptq-int4-ax650/model.embed_tokens.weight.bfloat16.bin \
  --tokens_embed_num 151936 --tokens_embed_size 1536 \
  --use_mmap_load_embed 0 --live_print 0 --continue 0 \
  --prompt 'What is 2 + 3? Reply with only the number.'
```

等待程序显示完整回复并退出。更换 `--prompt` 的内容可测试中文或 JSON 输入；每次重新启动，不沿用上一条对话。本页记录包含模型加载和退出的进程耗时，不作为纯推理速度。完成后在分词服务终端按 `Ctrl+C` 退出。
