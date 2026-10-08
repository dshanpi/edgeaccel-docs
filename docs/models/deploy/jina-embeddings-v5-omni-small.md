---
title: "jina-embeddings-v5-omni-small 部署指南"
sidebar_label: "jina-embeddings-v5-omni-small"
description: "jina-embeddings-v5-omni-small 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# jina-embeddings-v5-omni-small 部署指南

jina-embeddings-v5-omni-small 用于文本、图片与音频向量检索。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/jina-embeddings-v5-omni-small` 的固定版本。下面下载本页选用的 176 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/jina-embeddings-v5-omni-small/3369e03364b2
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/jina-embeddings-v5-omni-small \
  --include "*.axmodel" "lora/*" "assets/*" "model.embed_tokens.weight.bfloat16.bin" "config.json" "tokenizer.json" "tokenizer_config.json" "chat_template.jinja" \
  --revision 3369e03364b29a2af7d1fd766d0e59f31b92d5b8 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装算力卡运行包

本例在 RK3576 + AX8850 **16GB M.2 算力卡**上运行 Jina Omni Small，输出 1024 维归一化向量。支持 `retrieval`、`clustering`、`classification`、`text-matching` 四种任务。同一次相似度比较应使用同一任务编码的向量。

下载[算力卡运行包](../../../static/examples/jina-omni-small-native-20260930.tar.gz)，保存到 `~/edgeaccel`。在已安装 AXCL V3.16.0、Python 3.12 的 ARM64 主机执行：

```bash
cd ~/edgeaccel
tar -xzf jina-omni-small-native-20260930.tar.gz
python3 -m venv jina-small-env
source jina-small-env/bin/activate
python -m pip install 'numpy==1.26.4' 'ml_dtypes==0.5.3' \
  'Pillow==11.3.0' 'tokenizers==0.21.4' 'Jinja2==3.1.6' \
  'soundfile==0.13.1' 'torch==2.5.1' 'transformers==4.51.3'
axcl-smi
```

确认设备 0 可识别。运行包包含 ARM64 桥接库、C++ 源码、Python 入口和已核对的张量接口，通过 AXCL Native API 运行。模型完整仓库约 2.37GB，另为 Python 依赖、缓存及输出预留空间。保留上面下载步骤中的 `MODEL_DIR` 变量。

## 运行图片与音频检索

以模型仓库中的猫图片和运行包中的语音样例，比较三条候选文字。音频内容为“Hello, this is a demo.”，来源是本算力卡先前生成的语音，经 24kHz 转为 16kHz；不属于 Jina 官方样例。

```bash
python - "$MODEL_DIR" <<'PY'
import json, sys
from pathlib import Path
model = Path(sys.argv[1]).resolve()
requests = [
    {"id": "cat", "role": "document", "text": "A striped cat is sitting on a concrete pavement."},
    {"id": "speech", "role": "document", "text": "Hello, this is a demo."},
    {"id": "finance", "role": "document", "text": "Bond yields rose after the central bank announcement."},
    {"id": "image", "modality": "image", "file": str(model / 'assets/cat_0.jpeg')},
    {"id": "audio", "modality": "audio", "file": str(Path.home() / 'edgeaccel/jina-omni-small/english-short.wav')}
]
Path.home().joinpath('edgeaccel/jina-small-inputs.json').write_text(
    json.dumps(requests, indent=2), encoding='utf-8')
PY

python ~/edgeaccel/jina-omni-small/jina_small_card.py \
  --model-dir "$MODEL_DIR" --inputs ~/edgeaccel/jina-small-inputs.json \
  --output ~/edgeaccel/results/jina-small-01
```

输出目录须尚不存在。默认使用 `retrieval` 任务；省略 `modality` 时按文本处理，省略 `role` 时按查询处理。读取实际排名：

```bash
python - <<'PY'
import json
from pathlib import Path
r = json.loads(Path.home().joinpath(
    'edgeaccel/results/jina-small-01/result.json').read_text(encoding='utf-8'))
print('完成：', r['completed'])
for i in [3, 4]:
    print(r['calls'][i]['id'])
    for j in sorted(range(3), key=lambda j: r['similarityMatrix'][i][j], reverse=True):
        print(r['calls'][j]['id'], round(r['similarityMatrix'][i][j], 6))
PY
```

分数为余弦相似度，不是概率。实际样例结果和适用范围见本页效果展示。

## 切换文本任务

将输入 JSON 改为下面内容，更换输出目录后沿用运行命令：

```json
[
  {"id": "query", "task": "retrieval", "role": "query", "text": "How do I train a puppy to sit?"},
  {"id": "related", "task": "retrieval", "role": "document", "text": "Reward the puppy immediately after it sits on command."},
  {"id": "unrelated", "task": "retrieval", "role": "document", "text": "Bond yields rose after the central bank announcement."}
]
```

`task` 可改为 `clustering`、`classification` 或 `text-matching`，同时将这些任务所有输入的 `role` 设为 `document`。检索任务使用 `query` 编码查询、`document` 编码候选。这些任务仍然输出向量，不会直接返回类别名称或聚类编号；需要将待处理内容和候选内容按同一任务编码，再实现分类或聚类逻辑。

## 检查输入与输出

`result.json` 的 `completed` 应为 `true`，每个 `calls` 项包含 1024 维 `embedding`、`tokenCount` 和 `requestSeconds`。`similarityMatrix` 的行列顺序与输入 JSON 一致。

本入口限制总长度为 **256 token**，包含任务前缀、媒体占位符和模板，超长输入直接拒绝。图片缩放到 256 × 256，占 64 个特征 token；音频要求 **16kHz 单声道、最长 8 秒**，补齐到 800 个 Mel 帧和 200 个特征 token。音频输出是向量，不是语音转录。本入口尚未覆盖长文和视频。

`requestSeconds` 包含该请求的预处理、模型加载与推理；首次音频请求还包含音频依赖初始化。不含进程启动、共享分词器及词向量初始化。当前逐请求加载模型，耗时不代表常驻服务吞吐。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB 算力卡完成四任务文本、图片与音频的基本编码，并展示真实相似度和候选排序。

**四种文本任务：比较相关和无关内容**

四种任务各使用一条输入和两条候选文字，相关候选分数均更高。检索→聚类→检索切换后，同一查询的输出向量逐字节一致。此处是基本样例检查，不是分类或聚类准确率评测。

| 任务 | 相关文本余弦 | 无关文本余弦 |
| --- | --- | --- |
| retrieval | 0.581275 | 0.391158 |
| clustering | 0.863664 | 0.466169 |
| classification | 0.764440 | 0.597520 |
| text-matching | 0.609863 | 0.495788 |

**图片与语音：实际候选排序**

使用同一张猫图片和同一段语音，与猫、语音内容、财务三条描述比较。检索任务以 query 编码输入、document 编码候选；另外三种任务全部使用 document。图片预期对应 cat，语音预期对应 speech；下表完整保留各任务结果。检索任务的图片和语音重复编码逐字节一致。 本样例中未选中预期描述的分支：classification-audio、text-matching-audio。

<div className="model-effect-gallery">

<figure>

[![实际图片输入：坐在路面上的猫](../../../static/validation/effects/jina-embeddings-v5-omni-small-20260930/cat.jpeg)](../../../static/validation/effects/jina-embeddings-v5-omni-small-20260930/cat.jpeg)

<figcaption>实际图片输入：坐在路面上的猫</figcaption>
</figure>

</div>

| 任务 | 输入 | cat 分数 | speech 分数 | finance 分数 | 第一名 |
| --- | --- | --- | --- | --- | --- |
| retrieval | 图片 | 0.290294 | 0.075366 | 0.055119 | cat |
| retrieval | 语音 | -0.016194 | 0.097545 | 0.042247 | speech |
| clustering | 图片 | 0.311334 | 0.130428 | 0.132416 | cat |
| clustering | 语音 | 0.110219 | 0.152600 | 0.115758 | speech |
| classification | 图片 | 0.376093 | 0.330550 | 0.282192 | cat |
| classification | 语音 | 0.193698 | 0.145792 | 0.102124 | cat |
| text-matching | 图片 | 0.279454 | 0.164071 | 0.088473 | cat |
| text-matching | 语音 | 0.195910 | 0.158553 | 0.135301 | cat |

实际语音输入：Hello, this is a demo.

<audio controls preload="metadata" src="/validation/effects/jina-embeddings-v5-omni-small-20260930/english-short.wav" aria-label="实际语音输入：Hello, this is a demo."></audio>

[下载音频](../../../static/validation/effects/jina-embeddings-v5-omni-small-20260930/english-short.wav)

**部署入口的实际耗时**

本页运行入口复现三条文本、一张图片和一段音频，五个向量均与前面的独立测试逐字节一致。下表为包含预处理、模型加载和推理的请求耗时，首次音频还含依赖初始化。

| 输入 | 总 token | 请求耗时（秒） |
| --- | --- | --- |
| cat | 12 | 16.536 |
| speech | 9 | 15.978 |
| finance | 11 | 16.279 |
| cat-image | 74 | 24.670 |
| speech-audio | 210 | 39.930 |

**检查输入长度边界**

总长 256 token 的输入完成编码；257 token 在 NPU 调用前拒绝，没有静默截断。随后再次运行原始检索查询，向量与首次测试逐字节一致。长度检查不代表长文检索质量。

**使用时注意：**

- 本次使用 16GB 卡，8GB 容量、并发与长期稳定性仍需回归。
- 本入口限制总长 256 token，尚未验证长文和视频；仓库其他运行时的长度能力不代表本入口已覆盖。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`3369e03364b29a2af7d1fd766d0e59f31b92d5b8`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | Python 3.12.3 + 本页 C++ 桥接库 / AXCL Native API（设备 0）；NumPy 1.26.4；Torch 2.5.1；Transformers 4.51.3 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 向量输出 | 1024 维 / L2 归一化 | 四任务文本、图片与固定 8 秒音频规格。 |
| 编译权重 | 39 / 39 实际执行 | 28 个文本层、1 个后处理、2 个媒体主干和 8 个任务投影。 |
| 检索入口复现 | 5 / 5 向量逐字节一致 | 文本、图片与音频，与独立测试比较。 |

适用范围：

- 图片固定 256×256；音频为 16kHz 单声道、最长 8 秒，按固定规格补齐。向量输出不等同于语音转录。
- 图文、音文仅使用各一个样例和三条候选，不能视为检索准确率数据集。
- 当前逐请求加载模型，请求耗时包含加载与预处理，不代表常驻服务吞吐。
- 本次未选中预期描述的分支：classification-audio、text-matching-audio；用于对应业务前需要补充标注数据评估。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`demo/openai_task_switch_web.py`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/demo/openai_task_switch_web.py) | Python 程序 / 前后处理 |
| [`scripts/test_retrieval_clustering.py`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/scripts/test_retrieval_clustering.py) | Python 程序 / 前后处理 |
| [`config.json`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/config.json) | 运行配置 |
| [`jina_embeddings_v5_omni_post.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`jina_v5_omni_tokenizer.txt`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_v5_omni_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`jina_v5_omni_small_vision_tower_256x256.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_v5_omni_small_vision_tower_256x256.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`jina_embeddings_v5_omni_p256_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_p256_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`jina_embeddings_v5_omni_p256_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_p256_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`jina_embeddings_v5_omni_p256_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_p256_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`jina_embeddings_v5_omni_p256_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_p256_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`jina_embeddings_v5_omni_p256_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_p256_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`lora/classification/source_adapter_config.json`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/lora/classification/source_adapter_config.json) | 运行配置 |
| [`lora/clustering/source_adapter_config.json`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/lora/clustering/source_adapter_config.json) | 运行配置 |

仓库提交：`3369e03364b29a2af7d1fd766d0e59f31b92d5b8`。仓库中的 39 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/tree/3369e03364b29a2af7d1fd766d0e59f31b92d5b8)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/tree/3369e03364b29a2af7d1fd766d0e59f31b92d5b8)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/README.md)。
- [主要程序入口：demo/openai_task_switch_web.py](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/demo/openai_task_switch_web.py)。
- [配套项目：AXERA-TECH/jina_embeddings_v5_omni.axera](https://github.com/AXERA-TECH/jina_embeddings_v5_omni.axera)。

返回[完整模型目录](../catalog.mdx)。
