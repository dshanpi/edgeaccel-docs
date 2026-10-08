## 下载固定版本模型

在连接算力卡的 RK3576 终端执行。模型包约 5.13 GiB，下载分区建议至少有 8 GiB 可用空间；板载空间不足时，将 `MODEL_DIR` 改为已挂载的 SSD 或存储卡目录。

```bash
MODEL_DIR=~/edgeaccel/models/deepseek-r1-7b-int4/9b903307e1ea
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4 \
  --revision 9b903307e1ea3b216330e88f8e6fe39b6627bb74 \
  --local-dir "$MODEL_DIR"
```

保留完整目录中的 28 个文本层、输出层、embedding、分词器、ARM64 程序和配置文件。代理设置见[下载方式与文件校验](../../usage/download-models.md)。标准 7B 版与本 Int4 版的分词服务接口不同，不能互换脚本。

下载[固定版本文件校验包](../../../static/examples/deepseek7b-int4-verify-20261003.tar.gz)，复制到 RK3576 的 `~/Downloads`，并将下载文件命名为 `deepseek7b-int4-verify-20261003.tar.gz`。使用 Python 3.9 或更高版本校验全部 43 个文件：

```bash
cd ~/Downloads
echo '45846cf74f7d20ed094f67f75e23111a847669223ee32aafc601f8dc2e0d00f1  deepseek7b-int4-verify-20261003.tar.gz' | sha256sum -c -
tar -xzf deepseek7b-int4-verify-20261003.tar.gz
python3 deepseek7b-int4-verify-20261003/verify_models.py "$MODEL_DIR"
```

校验包应显示 `OK`，脚本应输出 `Verified 43 model files`。文件缺失或 SHA256 不一致时，重新下载对应文件并再次校验，通过后再启动模型。

## 准备分词环境与运行程序

本页使用仓库中的 `main_axcl_aarch64`，适用于 Linux ARM64 主机上的 AXCL 算力卡。先确认 AXCL 驱动和设备可用，再安装分词依赖：

```bash
python3 -m venv ~/edgeaccel/deepseek7b-tokenizer-env
~/edgeaccel/deepseek7b-tokenizer-env/bin/python -m pip install \
  'transformers==4.51.3' 'tokenizers==0.21.4'
export PATH=/usr/bin/axcl:$PATH
axcl-smi
cd "$MODEL_DIR"
echo 'bb111fc00c54abb6142a8f44df087bf104c8150a1cefa6be55c6b174b932c4ec  main_axcl_aarch64' | sha256sum -c -
chmod +x main_axcl_aarch64
ldd main_axcl_aarch64
./main_axcl_aarch64 --help
```

程序校验应显示 `OK`，依赖中不能出现 `not found`。帮助信息应包含 `--filename_tokenizer_model`、`--tokenizer_type` 和 `--use_mmap_load_embed`。本程序通过 PATH 调用 `axcl-smi`，因此两个终端都要包含 `/usr/bin/axcl`。

## 启动官方分词服务

继续使用当前终端作为终端 1。进入模型根目录后执行，保持进程运行：

```bash
cd "$MODEL_DIR"
USE_TORCH=0 USE_TF=0 USE_FLAX=0 TOKENIZERS_PARALLELISM=false \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ~/edgeaccel/deepseek7b-tokenizer-env/bin/python deepseek-r1_tokenizer.py \
  --host 127.0.0.1 --port 8519
```

这里仅运行分词器，不需要安装 PyTorch。使用原始脚本和模板；本仓库模板会保留两个起始 token，不能自行删掉其中一个。

## 配置采样并运行问答

终端 2 重新设置模型目录，创建单独的运行目录。以下配置使用 `top_k=1`，关闭温度、重复惩罚和 top-p 采样，便于复现短输入；原始模型配置保持不变。

```bash
MODEL_DIR=~/edgeaccel/models/deepseek-r1-7b-int4/9b903307e1ea
RUN_DIR=~/edgeaccel/results/deepseek-r1-7b-int4
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
curl --fail http://127.0.0.1:8519/eos_id
cd "$RUN_DIR"
WEIGHTS="$MODEL_DIR/deepseek-r1-7b-gptq-int4-ax650"
set -o pipefail
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 AXLLM_DEVICES=0 \
  "$MODEL_DIR/main_axcl_aarch64" \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --tokenizer_type 2 \
  --filename_tokenizer_model http://127.0.0.1:8519 --bos 0 --eos 0 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHTS/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 152064 --tokens_embed_size 3584 \
  --use_mmap_load_embed 0 --live_print 1 --continue 0 \
  --prompt 'What is 2 + 3? Reply with only the number.' 2>&1 | tee answer.log
```

`/eos_id` 应返回包含 `"eos_id": 151643` 的 JSON。`--use_mmap_load_embed 0` 沿用官方示例的 embedding 读取方式，会将约 1.02 GiB 的 embedding 文件加载到主机内存，`--continue 0` 表示每次只运行一个独立问题。更换 `--prompt` 可复现下方其他输入。

完整进程计时包含模型加载和退出，不能等同于纯推理耗时。运行结束后执行 `axcl-smi`，确认模型资源已释放；不再使用分词服务时，在终端 1 按 `Ctrl+C` 退出。


