## 准备 AXCL 程序

本仓库固定版本提供 AX650 板端入口。M.2 算力卡使用下面已固定版本的官方 AXCL ARM64 程序，权重与 tokenizer 仍来自本页的 CTX Int8 仓库。

在前文设置的 `MODEL_DIR` 中下载程序并校验：

```bash
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4 \
  --revision 10db075dd5e99796adcec79452fcae0ec03ddded \
  --include main_axcl_aarch64 --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
printf '%s  %s\n' \
  1f9f1a1ca329b47f70840e8b6d104ce8248a82326aa2402bccb31144590a8fb2 \
  main_axcl_aarch64 | sha256sum -c -
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

校验须显示 `OK`，动态库检查不得出现 `not found`。

## 启动分词服务

```bash
python3 -m venv ~/edgeaccel/legacy-text-env
source ~/edgeaccel/legacy-text-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
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
python qwen2.5_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

保持分词服务运行。

## 运行文本生成

另开终端，按本页 CTX Int8 权重名称启动程序：

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-0-5b-instruct-ctx-int8/2aca5290377e
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
./main_axcl_aarch64 \
  --system_prompt 'You are Qwen, created by Alibaba Cloud. You are a helpful assistant.' \
  --template_filename_axmodel 'qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l%d_together.axmodel' \
  --axmodel_num 24 --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_post.axmodel \
  --filename_tokens_embed qwen2.5-0.5b-gptq-int8-ctx-ax650/model.embed_tokens.weight.bfloat16.bin \
  --tokens_embed_num 151936 --tokens_embed_size 896 \
  --use_mmap_load_embed 0 --live_print 0 --devices 0
```

在交互提示下输入问题，等待完整回复。输入 `q` 退出；每次核对新样例时重新启动程序。最后在分词服务终端按 `Ctrl+C` 关闭服务。下方只展示这套固定权重与 AXCL 程序组合的实际结果。
