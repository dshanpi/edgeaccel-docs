## 准备分词服务

本例使用仓库中的 `main_axcl_aarch64` 通过 AXCL 在算力卡上推理，Python 只负责分词。使用 Python 3.12 虚拟环境安装已测试版本：

```bash
python3 -m venv ~/edgeaccel/legacy-text-env
source ~/edgeaccel/legacy-text-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

依赖检查不能出现 `not found`。本仓库的 `config.json` 是模型配置，不是新版 AX-LLM 服务配置；使用下面的专用入口。

## 运行文本生成

先设置与本页效果一致的贪心采样，原配置备份为 `post_config.json.upstream`：

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
python qwen2.5_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

保持该终端运行。另开终端，进入相同模型目录并启动官方 ARM64 算力卡脚本：

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-0-5b-instruct-gptq-int4/10db075dd5e9
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
bash run_qwen2.5_0.5b_gptq_int4_axcl_aarch64.sh
```

在交互提示下输入问题，等待完整回复。输入 `q` 退出；本页每条样例均重新启动一次推理程序，未沿用上一题的对话历史。运行结束后，在分词服务终端按 `Ctrl+C` 关闭服务。

先输入 `What is 2 + 3? Reply with only the number.` 核对基础输出，再对照下方中文和 JSON 样例。模型能够生成文字，不代表它能可靠完成事实问答或遵守结构化输出约束。
