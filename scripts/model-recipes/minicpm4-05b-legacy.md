## 准备分词服务

本例使用官方 `main_axcl_aarch64` 通过 AXCL 在 M.2 算力卡上推理，Python 服务负责分词。以下版本已在 RK3576 主机上测试：

```bash
python3 -m venv ~/edgeaccel/legacy-text-env
source ~/edgeaccel/legacy-text-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

确认依赖检查没有 `not found`，再启动服务。

## 运行文本生成

在模型目录设置与本页效果一致的贪心采样，并保留原配置：

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
python minicpm4_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

保持服务终端运行。另开终端，进入同一模型目录：

```bash
MODEL_DIR=~/edgeaccel/models/minicpm4-0-5b/40672934396f
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
./main_axcl_aarch64 \
  --system_prompt 'You are MiniCPM4, created by ModelBest. You are a helpful assistant.' \
  --template_filename_axmodel 'minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l%d_together.axmodel' \
  --axmodel_num 24 \
  --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_post.axmodel \
  --filename_tokens_embed minicpm4-0.5b-int8-ctx-ax650/model.embed_tokens.weight.bfloat16.bin \
  --tokens_embed_num 73448 --tokens_embed_size 1024 \
  --use_mmap_load_embed 1 --live_print 0 --devices 0
```

在交互提示下输入 `What is 2 + 3? Reply with only the number.`，等待完整回复。`--live_print 0` 表示生成完成后显示回复。本次该问题返回 `5`。

输入 `q` 退出程序；测试下一条问题时重新启动，避免沿用对话历史。运行结束后，在分词服务终端按 `Ctrl+C` 关闭服务。下方展示三条独立输入的实际结果和进程耗时。
