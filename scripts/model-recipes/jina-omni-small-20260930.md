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
