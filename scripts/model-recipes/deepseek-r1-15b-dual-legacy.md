## 准备分词服务

本页使用该仓库的 AXCL 程序 `main_axcl_aarch64` 和 **UID 分词接口**。W8A16、W4A16 两组权重共用程序与词表；不要混用独立 `DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4` 仓库中的模型或分词脚本。

在 RK3576 主机执行：

```bash
python3 -m venv ~/edgeaccel/deepseek15-env
source ~/edgeaccel/deepseek15-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

依赖检查应全部解析成功，不能出现 `not found`。本页固定版本的 `config.json` 不是运行配置，不要作为新版 AX-LLM 的 JSON 配置传入程序。

## 配置采样并启动服务

下方效果使用贪心采样：`top_k=1`，关闭 temperature、repetition penalty 和 top-p。这与仓库的默认随机采样不同。先备份配置，再设置相同参数：

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
python deepseek-r1_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

保持服务运行。它为每次运行分配独立会话，监听本机回环地址，不需要对外开放端口。

## 运行两组权重

在另一终端恢复模型目录，先选择 W8A16：

```bash
MODEL_DIR=~/edgeaccel/models/deepseek-r1-distill-qwen-1-5b/88000a3b3447
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
WEIGHT_DIR=deepseek-r1-1.5b-ax650
MMAP=0
PROMPT='What is 2 + 3? Reply with only the number.'
printf '%s\nq\n' "$PROMPT" | ./main_axcl_aarch64 \
  --template_filename_axmodel "$WEIGHT_DIR/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel "$WEIGHT_DIR/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHT_DIR/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 151936 --tokens_embed_size 1536 \
  --use_mmap_load_embed "$MMAP" --live_print 0 --devices 0 \
  --system_prompt 'You are deepseek, You are a helpful assistant.'
```

程序完成一题后读取 `q` 并退出。`--live_print 0` 在生成结束后显示完整回复；总耗时包含模型加载、分词通信、生成和释放。

运行 W4A16 时，将变量改为以下值，再执行同一条 `printf … | ./main_axcl_aarch64 …` 命令：

```bash
WEIGHT_DIR=deepseek-r1-1.5b-int4-ax650
MMAP=1
```

两组均使用各自目录中的 28 层模型、post 模型与 embedding。测试其他内容时修改 `PROMPT`；本页另外使用了“一句中文说明 PCIe 用途”和“只返回指定 JSON”两道固定问题。

## 检查实际回复

程序应正常生成文本并退出，运行结束后用 `axcl-smi` 确认模型进程已释放。下方分别保留两组权重的原始回复和逐题观察。

内容与格式需分别判断：算术结果是否为 5、PCIe 说明是否准确、JSON 是否可直接解析。输出可能含有思考过程、Markdown 或额外说明，不能直接当作数字或 JSON 交给业务程序。短题运行通过不代表长上下文、多轮或完整能力评测通过。

结束使用后，在分词服务终端按 `Ctrl+C`。需要恢复默认采样时，将 `post_config.json.upstream` 复制回 `post_config.json`。
