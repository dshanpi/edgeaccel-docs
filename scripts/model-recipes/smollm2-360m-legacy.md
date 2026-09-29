## 准备分词服务

模型使用官方 `main_axcl_aarch64` 通过 AXCL 在设备 0 推理。Python 分词服务在 RK3576 主机运行，安装已测试版本：

```bash
python3 -m venv ~/edgeaccel/legacy-text-env
source ~/edgeaccel/legacy-text-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

依赖检查不能出现 `not found`。本页使用 `smollm2-360m-ax650` 权重；仓库中的空 `config.json` 不作为新版 AX-LLM 服务配置。

## 运行文本生成

设置与下方效果一致的采样参数，然后启动 UID 分词服务：

```bash
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
python smollm2_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

保持该终端运行。在另一终端执行以下命令。显式指定配套 tokenizer 的系统提示词；`--live_print 0` 在完整解码后输出，避免中文字符被流式 token 分块截开。

```bash
MODEL_DIR=~/edgeaccel/models/smollm2-360m-instruct/17a64761eff9
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
./main_axcl_aarch64 \
  --template_filename_axmodel 'smollm2-360m-ax650/llama_p128_l%d_together.axmodel' \
  --axmodel_num 32 \
  --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel smollm2-360m-ax650/llama_post.axmodel \
  --filename_tokens_embed smollm2-360m-ax650/model.embed_tokens.weight.bfloat16.bin \
  --tokens_embed_num 49152 --tokens_embed_size 960 \
  --use_mmap_load_embed 0 --live_print 0 --devices 0 \
  --system_prompt 'You are a AI assistant, created by HuggingfaceTB'
```

输入问题并等待回复，输入 `q` 退出。本页三个样例分别重新启动推理程序，使用独立对话。结束使用后，在分词服务终端按 `Ctrl+C`。

先输入 `Return only a JSON object with apple equal to 3 and pear equal to 2.`，检查回复是否能直接解析为 JSON，再核对字段与数值。其他输入仍需按业务要求评估。
