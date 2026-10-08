## 准备转换与运行环境

本页将文字转换为 1024 维向量，再按相似度检索候选文档。28 个文本层与最终归一化层在算力卡上执行，分词、向量查表和 L2 归一化在 RK3576 主机执行。

| 设备 | 准备内容 |
| --- | --- |
| 转换主机 | x86_64 Linux 或 WSL2、Docker、Pulsar2 7.0-patch1（提交 `29f4c81a`）；建议 16GB 以上内存，工作分区预留 10GB |
| RK3576 + M.2 卡 | 完成[驱动与设备检查](../../usage/device-check.md)；本次实测为 AX8850 16GB、AXCL V3.16.0 |
| 板端存储 | 模型包约 837MiB；模型和 Python 环境建议预留 3GB，可放在已挂载的存储卡或 SSD |

本配置逐条编码，每条输入为 1–512 token，查询指令也计入长度。较长文档需要先分段。8GB 卡尚未执行本配置的回归测试。

转换主机按 [Pulsar2 环境说明](https://pulsar2-docs.readthedocs.io/zh-cn/latest/user_guides_quick/quick_start_prepare.html)准备 Docker，并取得上述版本镜像。以下使用实测镜像 ID，不能直接替换成其他版本：

```bash
PULSAR_IMAGE=sha256:f9d2e54003775abaa782acb2bf92cbd5e3f19c88b7e5615bb3e6673da80b456e
docker image inspect "$PULSAR_IMAGE" --format '{{.Id}}'
```

输出应与 `PULSAR_IMAGE` 一致。没有该镜像时先向供应商取得配套镜像并导入，再继续转换。

## 下载源权重与部署程序

在转换主机完成[Hugging Face 下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)，执行：

```bash
WORK=~/edgeaccel/qwen3-embedding
mkdir -p "$WORK/source" "$WORK/builds"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-Embedding-0.6B-GPTQ-Int8 \
  --revision 4c972fca3731832e33899e14da1555dd78c3f8d6 \
  --local-dir "$WORK/source"
```

仓库提供 GPTQ 源权重，没有预编译 `.axmodel`。下载受阻时，按[代理与离线复制说明](../../usage/download-models.md)设置网络。

下载[转换脚本、AXCL 运行程序及检索样例](/examples/qwen3-embedding-deployment-20261004.zip)，保存为 `qwen3-embedding-deployment-20261004.zip` 并放入 `WORK` 目录：

```bash
cd "$WORK"
echo 'e8f9fed1b60d215af19d09285dbe14deefb1660fa9353e00305d9a9c054d7abe  qwen3-embedding-deployment-20261004.zip' | sha256sum -c -
python3 -m zipfile -e qwen3-embedding-deployment-20261004.zip .
```

校验应显示 `OK`，解压后应出现 `recipe/convert.py`、`recipe/qwen3_embedding_axcl.py` 和两份输入 JSON。

## 转换完整模型

仍在转换主机执行。`builds/run` 必须是尚未使用的输出目录；重新转换时改用新的目录名。

```bash
docker run --rm --network none --cpus 2 --memory 6g --memory-swap 10g \
  --pids-limit 512 \
  -e FLOAT_MATMUL_USE_CONV_EU=1 -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 \
  --mount "type=bind,src=$WORK/source,dst=/inputs,readonly" \
  --mount "type=bind,src=$WORK/recipe,dst=/recipe,readonly" \
  --mount "type=bind,src=$WORK/builds,dst=/outputs" \
  --entrypoint python3 "$PULSAR_IMAGE" \
  /recipe/convert.py --source /inputs --output /outputs/run
```

首次转换需要逐层编译；本次 28 层编译约 59 分钟。可在另一终端查看 `builds/run/decoder-build.log`。

转换程序保留原始词表、全部 28 层及原始最终 RMSNorm 权重，选择用于文本向量的输出。它检查源文件并生成本次转换的 `SHA256SUMS`。完成时输出 `READY: /outputs/run/package`；未出现该标记时先查看日志，不复制未完成的模型包。

```bash
cd "$WORK/builds/run/package"
sha256sum -c SHA256SUMS
find . -maxdepth 1 -name '*.axmodel' | wc -l
```

应有 29 个 `.axmodel`，另含 `model.embed_tokens.weight.bfloat16.bin` 和 `tokenizer.json`。重新编译的二进制校验值可能不同，文件传输后使用本次生成的清单校验，并继续执行下面的结果检查。

## 将模型复制到 RK3576

在转换主机执行，将 `CARD_HOST` 替换为 RK3576 的 SSH 用户与地址，将 `CARD_DIR` 替换为板端已有足够空间的绝对目录：

```bash
CARD_HOST=baiwen@192.168.1.44
CARD_DIR=/home/baiwen/edgeaccel/qwen3-embedding
ssh "$CARD_HOST" "mkdir -p '$CARD_DIR'"
scp -r "$WORK/builds/run/package" "$WORK/recipe" "$CARD_HOST:$CARD_DIR/"
```

后续命令均在 RK3576 上执行。使用与复制目标相同的目录：

```bash
APP_DIR=/home/baiwen/edgeaccel/qwen3-embedding
MODEL_DIR="$APP_DIR/package"
cd "$MODEL_DIR"
sha256sum -c SHA256SUMS
```

所有文件应为 `OK`。先按[安装已核对的 PyAXEngine 版本](../../usage/python.md#安装已核对的-pyaxengine-版本)创建 `~/edgeaccel/python-env`，再补充分词依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'tokenizers==0.21.4' 'numpy==1.26.4' 'ml-dtypes==0.5.3'
python -m pip check
export PATH=/usr/bin/axcl:$PATH
axcl-smi
python -c 'import axengine; print(axengine.get_available_providers())'
```

依赖检查应通过，设备 0 应可用，可用后端应包含 `AXCLRTExecutionProvider`。运行程序会再次核对实际后端和 29 个模型的输入输出。

## 运行中英文检索

保持上述板端终端与虚拟环境。两次运行分别处理两条查询与两篇候选文档，输出目录必须尚不存在：

```bash
cd "$APP_DIR/recipe"
python qwen3_embedding_axcl.py --model-dir "$MODEL_DIR" \
  --input-json official-readme-example.json --output-dir "$APP_DIR/result-en"
python check_results.py --case official-readme --result-dir "$APP_DIR/result-en"

python qwen3_embedding_axcl.py --model-dir "$MODEL_DIR" \
  --input-json chinese-retrieval-example.json --output-dir "$APP_DIR/result-zh"
python check_results.py --case chinese-retrieval --result-dir "$APP_DIR/result-zh"
```

每个结果目录包含 `result.json` 和 `embeddings.npy`。检查程序应输出 `PASS`：4 条向量均为 1024 维，分别与原始完整模型 CPU 参考比较，两条查询各自命中对应文档。

向量与 CPU 参考的余弦相似度须不低于 0.99，检索分数差须不大于 0.02。检查未通过时保留结果文件，核对源权重、编译器与输入，不用其他模型的向量替换结果。

## 替换为业务文档

复制一份样例 JSON，修改 `queries`、`documents` 和检索任务说明 `instruction`。程序会为查询添加指令前缀，候选文档按原文编码；无需手动添加前缀。

也可使用 `{"texts": ["第一段文字", "第二段文字"]}` 只生成向量。再次执行 `qwen3_embedding_axcl.py` 时指定新的结果目录。

超出 512 token 的输入会报错，不会静默截断。建立索引时保存模型版本与前处理方式；更换模型或指令后重新编码。检索分数用于排序，业务阈值需要用自己的相关与不相关文档标定。
