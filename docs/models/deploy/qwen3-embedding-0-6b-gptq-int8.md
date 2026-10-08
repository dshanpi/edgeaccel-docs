---
title: "Qwen3-Embedding-0.6B-GPTQ-Int8 部署指南"
sidebar_label: "Qwen3-Embedding-0.6B-GPTQ-Int8"
description: "Qwen3-Embedding-0.6B-GPTQ-Int8 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-Embedding-0.6B-GPTQ-Int8 部署指南

Qwen3-Embedding-0.6B-GPTQ-Int8 用于文本向量与语义检索。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

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


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

在16GB M.2算力卡上完成完整模型的中英文向量与检索。下方展示简单部署样例、构造语料，以及采用外部相关性标注的检索子集；实际向量均已与原始完整模型的CPU结果核对，未命中项也保留在结果中。

以下结果由完整 28 层模型与最终归一化层在算力卡上生成。输入均为文字，输出为 1024 维单位向量；相似度是向量的余弦分数，不是准确率或概率。

### 运行英文检索

| 候选文档 | 内容 |
| --- | --- |
| 文档 1 | The capital of China is Beijing. |
| 文档 2 | Gravity is a force that attracts two bodies towards each other. It gives weight to physical objects and is responsible for the movement of planets around the sun. |

| 查询 | 文档 1 分数 | 文档 2 分数 | 首选结果 |
| --- | --- | --- | --- |
| What is the capital of China? | 0.753962 | 0.142526 | 文档 1 |
| Explain gravity | 0.129248 | 0.591753 | 文档 2 |

本次模型加载 10.037 秒；加载后的单条编码耗时 0.443–0.482 秒。编码耗时包含主机向量查表、数据传输、算力卡推理与归一化，不包含模型加载和分词。

### 运行中文检索

| 候选文档 | 内容 |
| --- | --- |
| 文档 1 | 温室湿度低于设定值时，启动加湿设备并适量补水。 |
| 文档 2 | 画面中的双层公共汽车是红色的。 |

| 查询 | 文档 1 分数 | 文档 2 分数 | 首选结果 |
| --- | --- | --- | --- |
| 温室湿度过低应该怎么处理？ | 0.715815 | 0.056536 | 文档 1 |
| 画面中的公共汽车是什么颜色？ | 0.118098 | 0.787964 | 文档 2 |

本次模型加载 9.967 秒；加载后的单条编码耗时 0.431–0.473 秒。编码耗时包含主机向量查表、数据传输、算力卡推理与归一化，不包含模型加载和分词。

两组查询均将对应文档排在首位。中文“公共汽车”示例是在已有文字描述中检索答案，没有输入或识别图片。

[下载本次实际向量、检索分数与 CPU 对照](../../../static/validation/effects/qwen3-embedding-int8-20261004/embedding-result.json)。这里的固定样例不能代替业务语料上的召回率评估。

### 核对中英文与跨语言检索

使用 20 篇候选文档测试 40 个不同查询，内容包含容易混淆的操作条件和中英文改写。语料与相关性标注由助手在推理前编写，不属于公开基准或独立人工标注。额外重复首条查询一次，输出向量逐值一致，重复项不计入命中率。

| 检查项 | 实际结果 |
| --- | --- |
| 正确文档排在首位 | 39 / 40 |
| 正确文档进入前三 | 40 / 40 |
| 平均倒数排名（MRR） | 0.9875 |
| 61 个向量与完整 CPU 模型的最低余弦相似度 | 0.998632 |
| 全部检索分数与 CPU 结果的最大差异 | 0.010785 |

以下查询的首选结果未命中预先指定的文档，完整结果中保留了该项：

| 查询 | 实际首选文档 | 预期文档 | 预期文档排名 |
| --- | --- | --- | --- |
| 盆里的土干了，温室A应启动哪个设备给根系补水？ | 温室A的空气湿度偏低、但土壤含水量正常时，启动空气加湿器；无需启动滴灌。 | 温室A的土壤湿度低于设定值时，控制器启动滴灌，为根部补水。空气加湿器不负责给土壤浇水。 | 2 |

[下载全量输入样例](../../../static/validation/effects/qwen3-embedding-int8-20261004/bilingual-input.json)，保存到板端 `$APP_DIR/recipe/bilingual-input.json` 后，使用前文同一程序复现：

```bash
cd "$APP_DIR/recipe"
python qwen3_embedding_axcl.py --model-dir "$MODEL_DIR" \
  --input-json bilingual-input.json --output-dir "$APP_DIR/result-bilingual"
```

[查看全部排名、实际向量和 CPU 对照](../../../static/validation/effects/qwen3-embedding-int8-20261004/retrieval-quality.json)。本次小型构造语料结果不能替代业务文档和真实查询上的检索评估。

### 核对外部标注检索样本

采用英文 SciFact 与中文 DuRetrieval 的固定版本，每种语言按查询 ID 顺序选取 16 条。保留全部已标注相关文档，并加入词面相近及按固定哈希顺序选取的候选；以下是缩小候选集后的子集测试，不是完整 BEIR 或 C-MTEB 基准成绩。

长文档按 512 token 分段，相邻段重叠 64 token，保留全部内容；文档得分取最相似分段的余弦分数。标注与查询选择在模型推理前固定，未根据结果剔除样本。

| 数据集 | 查询 / 候选文档 | 首选命中 | Recall@3 | Recall@10 | NDCG@10 |
| --- | --- | --- | --- | --- | --- |
| [SciFact](https://huggingface.co/datasets/BeIR/scifact/tree/b3b5335604bf5ee3c4447671af975ea25143d4f5) | 16 / 64 | 9 / 16 | 0.9063 | 1.0000 | 0.8031 |
| [DuRetrieval](https://huggingface.co/datasets/C-MTEB/DuRetrieval/tree/a1a333e290fe30b10f3f56498e3a0d911a693ced) | 16 / 116 | 12 / 16 | 0.6472 | 1.0000 | 0.9100 |

首选命中表示第一篇文档属于该查询的相关文档。Recall@k 先计算每个查询在前 k 篇中找回的相关文档比例，再取平均；同一查询可能有多篇相关文档。NDCG@10 使用原始相关性等级，增益为 2 的等级次方减 1。未标注候选仅在评分时按 0 处理，不表示经过人工确认的不相关文档。

本次 238 条分段与查询输入的实际向量，均与原始完整 28 层 CPU 模型核对：最低余弦相似度 0.995763，文档检索分数最大差异 0.013830。执行前后模型文件一致，首条输入在执行开始及结束时复测，输出逐值一致。

[下载全部排名、向量与对照结果](../../../static/validation/effects/qwen3-embedding-int8-20261004/external-retrieval.json)。数据来源和固定版本包含在结果中；原始语料请从对应数据集获取。

**使用时注意：**

- 本次为RK3576 + AX8850 16GB实测；实际8GB卡、并发与长期运行需单独验证。
- 构造语料由助手预先编写；外部标注测试各选16条查询并缩小候选集，均不能等同完整公开基准或业务检索精度。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`4c972fca3731832e33899e14da1555dd78c3f8d6`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 15232MiB |
| Python / PyAXEngine | Python 3.12；官方 0.1.3.rc3 wheel（包版本 0.1.3）；AXCLRTExecutionProvider |
| NumPy / Pillow | 1.26.4 / 11.3.0 |
| ml-dtypes / OpenCV | 0.5.3 / opencv-python-headless 4.11.0.86 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 向量维度 | 1024 | 原始最终归一化层输出，经最后有效token选取与L2归一化。 |
| 单条输入上限 | 512 token | 本页固定编译配置，batch=1；包含查询指令前缀。 |
| 构造语料首选命中 | 39 / 40 | 20篇候选文档，40个不同查询；额外1次重复查询不计入分母。 |
| 构造语料前三命中 | 40 / 40 | 每个查询只有1篇预先指定的相关文档，全部查询均保留。 |
| 英文外部标注子集首选命中 | 9 / 16 | SciFact固定查询，64篇候选文档；不是完整BEIR基准。 |
| 中文外部标注子集首选命中 | 12 / 16 | DuRetrieval固定查询，116篇候选文档；不是完整C-MTEB基准。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B-GPTQ-Int8/blob/4c972fca3731832e33899e14da1555dd78c3f8d6/config.json) | 运行配置 |
| [`generation_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B-GPTQ-Int8/blob/4c972fca3731832e33899e14da1555dd78c3f8d6/generation_config.json) | 运行配置 |
| [`quantize_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B-GPTQ-Int8/blob/4c972fca3731832e33899e14da1555dd78c3f8d6/quantize_config.json) | 运行配置 |
| [`tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B-GPTQ-Int8/blob/4c972fca3731832e33899e14da1555dd78c3f8d6/tokenizer_config.json) | 运行配置 |

仓库提交：`4c972fca3731832e33899e14da1555dd78c3f8d6`。该提交没有预编译 `.axmodel` 文件。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B-GPTQ-Int8/tree/4c972fca3731832e33899e14da1555dd78c3f8d6)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 该仓库提供 GPTQ 源权重，按本页固定编译器与脚本生成 AXCL 模型包。
- 本配置使用完整28层与最终归一化层，输出1024维文本向量，单条输入最多512 token。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B-GPTQ-Int8/tree/4c972fca3731832e33899e14da1555dd78c3f8d6)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B-GPTQ-Int8/blob/4c972fca3731832e33899e14da1555dd78c3f8d6/README.md)。

返回[完整模型目录](../catalog.mdx)。
