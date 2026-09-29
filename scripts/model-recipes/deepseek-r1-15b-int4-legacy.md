## 准备分词服务

本例使用仓库的 ARM64 AXCL 程序和 `deepseek-r1_tokenizer.py`。在 RK3576 主机安装已测试的分词依赖：

```bash
python3 -m venv ~/edgeaccel/legacy-text-env
source ~/edgeaccel/legacy-text-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

依赖检查不能出现 `not found`。仓库中的空 `config.json` 不作为新版 AX-LLM 服务配置；使用下方已测试的旧版命令行参数。

## 运行单轮问答

先设置本页使用的贪心采样，再启动分词服务。该服务使用非 UID 接口，不能替换为 Qwen 的 UID 服务。

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
python deepseek-r1_tokenizer.py --host 127.0.0.1 --port 12345
```

保持分词服务运行。在另一终端执行下方命令，替换 `PROMPT` 的内容即可测试其他问题。`--continue 0` 表示完成一题后退出，`--live_print 0` 表示生成结束后输出完整回复。

```bash
MODEL_DIR=~/edgeaccel/models/deepseek-r1-distill-qwen-1-5b-gptq-int4/496f830bba4e
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
PROMPT='What is 2 + 3? Reply with only the number.'
./main_axcl_aarch64 \
  --template_filename_axmodel 'deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l%d_together.axmodel' \
  --axmodel_num 28 --tokenizer_type 2 \
  --filename_tokenizer_model http://127.0.0.1:12345 \
  --bos 0 --eos 0 \
  --filename_post_axmodel deepseek-r1-1.5b-gptq-int4-ax650/qwen2_post.axmodel \
  --filename_tokens_embed deepseek-r1-1.5b-gptq-int4-ax650/model.embed_tokens.weight.bfloat16.bin \
  --tokens_embed_num 151936 --tokens_embed_size 1536 \
  --use_mmap_load_embed 0 --live_print 0 --continue 0 --prompt "$PROMPT"
```

等待模型加载和生成结束。原始回复可能包含 `<think>` 思考文本、最终回答以及 Markdown 格式，不能直接当作 JSON 或单个数字传给其他程序。结束使用后，在分词服务终端按 `Ctrl+C`。
