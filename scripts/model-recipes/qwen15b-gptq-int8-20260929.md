## 准备程序与分词服务

以下命令在连接算力卡的 RK3576 主机执行，沿用前文的 `MODEL_DIR`。文件约 2.43GB，另外预留运行和日志空间。本页使用主机内部存储、仓库自带的 `main_axcl_aarch64` 和 `qwen2.5_tokenizer.py` 分词服务。

```bash
python3 -m venv ~/edgeaccel/qwen25-gptq-env
source ~/edgeaccel/qwen25-gptq-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4' 'jinja2==3.1.6'
cd "$MODEL_DIR"
printf '%s  %s\n' \
  bb111fc00c54abb6142a8f44df087bf104c8150a1cefa6be55c6b174b932c4ec \
  main_axcl_aarch64 | sha256sum -c -
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

程序校验须显示 `OK`，动态库检查不得出现 `not found`。设置固定采样参数，并保留上游配置副本：

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
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
python qwen2.5_tokenizer.py --host 127.0.0.1 --port 12345
```

保持这个终端运行。Python 服务负责分词，文本生成由 AXCL 程序在算力卡上完成。

## 运行单轮问答

另开主机终端，设置同一内部存储中的模型目录。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-1-5b-instruct-gptq-int8/a882598b8893
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"

PROMPT='What is 2 + 3? Reply with only the number.'
WEIGHTS=qwen2.5-1.5b-gptq-int8-ax650
./main_axcl_aarch64 \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --tokenizer_type 2 \
  --filename_tokenizer_model http://127.0.0.1:12345 \
  --bos 0 --eos 0 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHTS/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 151936 --tokens_embed_size 1536 \
  --use_mmap_load_embed 0 --live_print 0 --continue 0 --prompt "$PROMPT"
```

当前设置采用非 mmap 方式加载 embedding，在生成结束后显示完整回答并退出。复现其他单轮输入时，修改 `PROMPT` 后重新运行同一命令：

```text
请用一句中文说明 PCIe 的用途。
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

运行日志应完成 28 层和 post 模型初始化，随后输出回答并出现 `hit eos`。程序结束后运行 `axcl-smi`，确认推理进程已释放资源。该版本未输出首 token 耗时；效果展示保留完整进程耗时，包含模型加载、一次问答和退出。
