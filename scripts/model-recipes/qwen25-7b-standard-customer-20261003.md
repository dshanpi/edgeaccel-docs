## 下载固定版本模型

在连接算力卡的 RK3576 终端执行。此固定版本包含一套 `qwen2.5-7b-ctx-int4-ax650` 权重，共 28 个文本层和一个输出层。完整文件约 5.62 GiB，下载分区建议至少预留 8 GiB。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b/97ccbbde2f22
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-7B-Instruct \
  --revision 97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb \
  --local-dir "$MODEL_DIR"
```

板载空间不足时，将 `MODEL_DIR` 指向已挂载的存储卡或 SSD。代理设置见[下载方式与文件校验](../../usage/download-models.md)。

下载[固定版本文件校验包](../../../static/examples/qwen25-7b-standard-20261003.tar.gz)，复制到 RK3576 的 `~/Downloads`，并命名为 `qwen25-7b-standard-20261003.tar.gz`。校验包不包含模型权重，使用 Python 3.9 或更高版本运行：

```bash
cd ~/Downloads
echo '93e334372ebac1fd15465faf702f4e237db5b2cc89464c6b347546a1ab42033d  qwen25-7b-standard-20261003.tar.gz' | sha256sum -c -
tar -xzf qwen25-7b-standard-20261003.tar.gz
python3 qwen25-7b-standard-20261003/verify_models.py "$MODEL_DIR"
```

校验包应显示 `OK`，脚本应输出 `Verified 49 model files`。文件缺失或校验不一致时，重新下载对应文件，通过后再运行。

## 准备分词环境与程序

继续在当前终端执行。分词服务使用 Python，模型推理由仓库中的 ARM64 AXCL 程序完成。

```bash
python3 -m venv ~/edgeaccel/qwen25-7b-uid-env
~/edgeaccel/qwen25-7b-uid-env/bin/python -m pip install \
  'transformers==4.51.3' 'tokenizers==0.21.4'
export PATH=/usr/bin/axcl:$PATH
axcl-smi
cd "$MODEL_DIR"
echo '1f9f1a1ca329b47f70840e8b6d104ce8248a82326aa2402bccb31144590a8fb2  main_axcl_aarch64' | sha256sum -c -
chmod +x main_axcl_aarch64
ldd main_axcl_aarch64
./main_axcl_aarch64 --help
```

程序校验应显示 `OK`，依赖中不能出现 `not found`。帮助信息应包含 `--devices`、`--system_prompt` 和 `--url_tokenizer_model`。

## 启动官方分词服务

将当前终端作为终端 1，执行后保持服务运行：

```bash
cd "$MODEL_DIR"
USE_TORCH=0 USE_TF=0 USE_FLAX=0 TOKENIZERS_PARALLELISM=false \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ~/edgeaccel/qwen25-7b-uid-env/bin/python qwen2.5_tokenizer_uid.py \
  --host 127.0.0.1 --port 8519
```

这里只使用分词器，不需要安装 PyTorch。程序通过 UID 创建独立会话，须保留仓库配套的分词脚本及模板。

## 配置单卡并运行问答

另开终端 2，重新设置同一模型目录，创建独立运行目录。以下配置使用设备 0、`top_k=1` 和原版 Qwen 系统提示词。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b/97ccbbde2f22
WEIGHTS="$MODEL_DIR/qwen2.5-7b-ctx-int4-ax650"
RUN_DIR=~/edgeaccel/results/qwen2-5-7b
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
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 AXLLM_DEVICES=0 \
  "$MODEL_DIR/main_axcl_aarch64" \
  --devices 0 \
  --system_prompt 'You are Qwen, created by Alibaba Cloud. You are a helpful assistant.' \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --url_tokenizer_model http://127.0.0.1:8519 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHTS/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 152064 --tokens_embed_size 3584 \
  --use_mmap_load_embed 0 --live_print 1 2>&1 | tee answer.log
```

`--use_mmap_load_embed 0` 会将约 1.02 GiB 的 embedding 加载到主机内存，还需为操作系统和运行程序保留空间。等待出现输入提示后输入问题：

```text
What is 2 + 3? Reply with only the number.
```

回答结束后输入 `q` 退出。复现各条独立样例时，每次重新启动程序；同一进程中的连续对话需要另行验证。完成后执行 `axcl-smi` 确认模型资源已释放，并在终端 1 按 `Ctrl+C` 结束分词服务。


