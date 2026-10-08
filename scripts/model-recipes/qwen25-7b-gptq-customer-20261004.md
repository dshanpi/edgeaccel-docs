

## 下载固定版本模型

在连接算力卡的 RK3576 终端执行。本页使用仓库原版 ARM64 AXCL 程序，配套 28 个文本层、一个输出层和非 UID 分词服务。37 个文件约 5.12 GiB，下载分区建议至少预留 8 GiB。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b-instruct-gptq-int4/5b09894da95a
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4 \
  --include 'README.md' 'main_axcl_aarch64' 'post_config.json' \
  'qwen2.5_tokenizer.py' 'qwen2.5_tokenizer/*' \
  'model.embed_tokens.weight.bfloat16.bin' \
  'qwen2_p128_l*_together.axmodel' 'qwen2_post.axmodel' \
  'run_qwen2.5_7b_gptq_int4_axcl_aarch64.sh' \
  --revision 5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c \
  --local-dir "$MODEL_DIR"
```

板载空间不足时，将 `MODEL_DIR` 指向已挂载的存储卡、SSD 或只读模型目录。代理及离线复制方法见[下载方式与文件校验](../../usage/download-models.md)。本次实测从主机的只读网络目录加载权重，完整进程耗时包含网络读取。

下载[37 个模型文件的 SHA256 校验清单](/examples/qwen25-7b-gptq-model-files-20261004.sha256)，将文件重命名为 `qwen25-7b-gptq-model-files-20261004.sha256` 并复制到 `MODEL_DIR`，再执行：

```bash
cd "$MODEL_DIR"
sha256sum -c qwen25-7b-gptq-model-files-20261004.sha256
```

全部文件应显示 `OK`。出现缺失或不匹配时，重新下载对应文件后再运行。

## 准备分词环境与程序

在 RK3576 上执行。Python 负责分词，模型推理由 AXCL 程序完成。

```bash
python3 -m venv ~/edgeaccel/qwen25-7b-gptq-env
~/edgeaccel/qwen25-7b-gptq-env/bin/python -m pip install \
  'transformers==4.51.3' 'tokenizers==0.21.4'
export PATH=/usr/bin/axcl:$PATH
axcl-smi
cd "$MODEL_DIR"
echo 'bb111fc00c54abb6142a8f44df087bf104c8150a1cefa6be55c6b174b932c4ec  main_axcl_aarch64' | sha256sum -c -
chmod +x main_axcl_aarch64
ldd main_axcl_aarch64
./main_axcl_aarch64 --help
```

程序校验应显示 `OK`，依赖中不能出现 `not found`。帮助信息应包含 `--tokenizer_type`、`--filename_tokenizer_model`、`--prompt` 和 `--continue`。以下步骤用于设备列表中只有一张卡、编号为 0 的环境。

## 启动官方分词服务

终端 1 执行，保持服务运行：

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b-instruct-gptq-int4/5b09894da95a
cd "$MODEL_DIR"
USE_TORCH=0 USE_TF=0 USE_FLAX=0 TOKENIZERS_PARALLELISM=false \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ~/edgeaccel/qwen25-7b-gptq-env/bin/python qwen2.5_tokenizer.py \
  --host 127.0.0.1 --port 8521
```

保留 `qwen2.5_tokenizer.py` 及同目录的 `qwen2.5_tokenizer` 文件夹。服务内置 Qwen 原版系统提示词；启动输出应包含 `eos_id` 对应的 `151645`。分词服务无需安装 PyTorch。

## 运行单次问答

另开终端 2，设置同一模型目录并创建独立运行目录。以下配置使用 `top_k=1`，每次提问启动一个新进程。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b-instruct-gptq-int4/5b09894da95a
RUN_DIR=~/edgeaccel/results/qwen25-7b-gptq
export PATH=/usr/bin/axcl:$PATH
mkdir -p "$RUN_DIR"
python3 - "$MODEL_DIR/post_config.json" "$RUN_DIR/post_config.json" <<'PY'
import json, sys
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
config.update(enable_temperature=False, enable_repetition_penalty=False,
              enable_top_p_sampling=False, enable_top_k_sampling=True, top_k=1)
Path(sys.argv[2]).write_text(json.dumps(config, indent=2) + '\n')
PY
cd "$RUN_DIR"
set -o pipefail
PROMPT='What is 2 + 3? Reply with only the number.'
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 AXLLM_DEVICES=0 \
  "$MODEL_DIR/main_axcl_aarch64" \
  --template_filename_axmodel "$MODEL_DIR/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --tokenizer_type 2 \
  --filename_tokenizer_model http://127.0.0.1:8521 \
  --bos 0 --eos 0 \
  --filename_post_axmodel "$MODEL_DIR/qwen2_post.axmodel" \
  --filename_tokens_embed "$MODEL_DIR/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 152064 --tokens_embed_size 3584 \
  --use_mmap_load_embed 0 --live_print 0 --continue 0 \
  --prompt "$PROMPT" 2>&1 | tee answer.log
```

`--use_mmap_load_embed 0` 会将约 1.02 GiB 的 embedding 加载到主机内存，须为操作系统和运行程序保留空间。`--live_print 0` 在生成结束后输出完整回答；等待期间可看到进度。上述算术问题应返回 `5`，日志应出现 `hit eos`，程序随后退出。

复现下方中文和 JSON 样例时，分别替换 `PROMPT` 并重新执行问答命令。测试结束后运行 `axcl-smi` 确认模型资源已释放，在终端 1 按 `Ctrl+C` 结束分词服务。
