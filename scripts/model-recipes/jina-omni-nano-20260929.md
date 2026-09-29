## 准备多模态向量环境

本例在 RK3576 + AX8850 **16GB M.2** 上运行，输出 768 维归一化向量。文本支持 `retrieval`、`clustering`、`classification`、`text-matching` 四种任务；图片和短音频支持前两种。选择任务决定向量空间，不能混用不同任务的分数。

下载 [算力卡运行包](../../../static/examples/jina-omni-nano-native-20260929.tar.gz)，保存为 `~/edgeaccel/jina-omni-nano-native-20260929.tar.gz`。包内提供已实测的 ARM64 库、C++ 源码、Python 入口及任务 token 配套文件，通过 **AXCL Native API** 使用设备 0。

在已有 AXCL 驱动和 Python 3.12 的 ARM64 主机执行：

```bash
cd ~/edgeaccel
tar -xzf jina-omni-nano-native-20260929.tar.gz
python3 -m venv jina-env
source jina-env/bin/activate
python -m pip install 'numpy==1.26.4' 'ml_dtypes==0.5.3' \
  'Pillow==11.3.0' 'tokenizers==0.21.4' 'Jinja2==3.1.6' \
  'scipy==1.17.1' 'soundfile==0.13.1' 'torch==2.5.1' 'transformers==4.51.3'
axcl-smi
```

以上版本来自本次运行环境；驱动和固件均为 V3.16.0。模型权重约 1.36GB，另需为 Python 依赖、下载缓存和结果预留空间。首次安装依赖需要联网，推理只读取本地文件。

如需重新编译配套库，在安装了 AXCL 开发头文件的主机执行：

```bash
cd ~/edgeaccel/jina-omni-nano
g++ -std=c++17 -O2 -shared -fPIC -Wall -Wextra -Werror \
  jina_native_bridge.cpp -I/usr/include/axcl -L/usr/lib/axcl \
  -laxcl_rt -laxcl_npu -Wl,-rpath,/usr/lib/axcl \
  -o libjina_native_bridge.so
```

`special-tokens/` 配套文件来自原始模型的[固定版本](https://huggingface.co/jinaai/jina-embeddings-v5-omni-nano/tree/009e0d09a98a82227526e8c5aa7b0aa282e36163)，来源和校验值保存在包内清单中。部署时与本页固定的 AXERA 权重一起使用。

## 运行文本与图片检索

保持前面下载步骤中的 `MODEL_DIR`。下面用一句描述检索仓库中的猫、狗图片：

```bash
python - "$MODEL_DIR" <<'PY'
import json, sys
from pathlib import Path
model = Path(sys.argv[1]).resolve()
requests = [
    {"id": "query-cat", "task": "retrieval", "role": "query",
     "text": "A photo of a cat."},
    {"id": "cat", "task": "retrieval", "modality": "image",
     "file": str(model / "assets/cat_0.jpeg")},
    {"id": "dog", "task": "retrieval", "modality": "image",
     "file": str(model / "assets/dog_0.jpeg")}
]
Path.home().joinpath('edgeaccel/jina-inputs.json').write_text(
    json.dumps(requests, ensure_ascii=False, indent=2), encoding='utf-8')
PY

python ~/edgeaccel/jina-omni-nano/jina_card.py \
  --model-dir "$MODEL_DIR" --inputs ~/edgeaccel/jina-inputs.json \
  --output ~/edgeaccel/results/jina-image-01
```

输出目录须尚不存在。读取本次实际分数：

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path.home() / 'edgeaccel/results/jina-image-01/embeddings.json'
r = json.loads(p.read_text(encoding='utf-8'))
print('完成：', r['completed'])
for item, score in zip(r['results'][1:], r['similarityMatrix'][0][1:]):
    print(item['id'], round(score, 6))
PY
```

程序按顺序逐条编码，每个请求输出向量、token 数和耗时。`similarityMatrix` 按输入顺序排列；不同任务之间为 `null`，不进行跨任务比较。图片统一缩放到 256 × 256，使用 64 个图像特征 token。文本经模板和 EOS 处理后最多 128 个 token，超长输入会报错。

## 运行短音频检索

下载 [英文样例](../../../static/validation/effects/jina-embeddings-v5-omni-nano-20260929/english-short.wav)、[中文样例](../../../static/validation/effects/jina-embeddings-v5-omni-nano-20260929/chinese-short.wav) 或 [双语样例](../../../static/validation/effects/jina-embeddings-v5-omni-nano-20260929/combined.wav)，在 `~/edgeaccel/inputs/` 下分别保存为 `english-short.wav`、`chinese-short.wav`、`combined.wav`。这些音频来自本地 TTS 演示，双语样例由前两段按顺序拼接。

将 `jina-inputs.json` 改为下面的内容，其中音频路径相对于该 JSON 文件：

```json
[
  {"id": "query", "task": "retrieval", "role": "query", "text": "Hello, this is a demo. 你好，欢迎使用算力卡。"},
  {"id": "audio", "task": "retrieval", "modality": "audio", "file": "inputs/combined.wav"}
]
```

```bash
python ~/edgeaccel/jina-omni-nano/jina_card.py \
  --model-dir "$MODEL_DIR" --inputs ~/edgeaccel/jina-inputs.json \
  --output ~/edgeaccel/results/jina-audio-01
```

支持不超过 8 秒的单声道音频，程序重采样到 16kHz，提取 128 维 Mel 特征，按实际时长取有效音频 token。特征编码按每块 128 个 token、最多两块执行；这与原始模型对整个序列一次执行双向注意力并不完全等价。更长录音需要由业务明确切段，本例不静默截断。

## 使用其他任务

文本分类、文本匹配和聚类均输出向量，业务需要继续比较标签、候选文本或建立聚类。`classification` 不会直接返回类别名称。将输入记录的 `task` 改为所需任务，并为该任务重新编码全部候选。

音频与音频的聚类可使用 `clustering`。本次仅检查两句语音及其降音量、前置静音版本；**音频与文本的跨模态聚类排序在本次样例中未达到预期**。根据描述检索录音时使用已展示的 `retrieval` 结果，仍需在业务数据上评估。

## 理解结果与耗时

`embeddings.json` 中的分数为余弦相似度，不是概率。向量采用最后一个 EOS 位置的归一化输出，再做 L2 归一化。下面展示原始输入和实测分数，避免只凭“程序正常退出”判断效果。

运行脚本的 `totalSeconds` 包含当前请求的预处理、模型加载和推理；首个音频请求还包含音频依赖初始化。它不包含进程启动、公共分词器和共享权重初始化，也不包含最终结果写盘。当前程序逐请求加载模型，适合复现功能，不代表模型常驻内存后的吞吐性能。完整调用记录保存在输出目录的 `native-calls/` 中。
