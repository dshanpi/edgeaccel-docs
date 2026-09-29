## 安装算力卡运行包

本例在 RK3576 + AX8850 **16GB M.2** 上运行文本、图片、音频和视频帧检索，输出 768 维归一化向量。固定仓库中的检索权重已经合并任务参数，输入通过 `query`、`document` 区分查询和候选内容。

下载 [算力卡运行包](../../../static/examples/jina-nano-retrieval-native-20260929.tar.gz)，保存为 `~/edgeaccel/jina-nano-retrieval-native-20260929.tar.gz`。包内包含已实测的 ARM64 库、C++ 源码、Python 入口及模型张量配置，通过 **AXCL Native API** 使用设备 0。

在安装了 AXCL V3.16.0 和 Python 3.12 的 ARM64 主机执行：

```bash
cd ~/edgeaccel
tar -xzf jina-nano-retrieval-native-20260929.tar.gz
python3 -m venv jina-retrieval-env
source jina-retrieval-env/bin/activate
python -m pip install 'numpy==1.26.4' 'ml_dtypes==0.5.3' \
  'Pillow==11.3.0' 'tokenizers==0.21.4' 'Jinja2==3.1.6' \
  'scipy==1.17.1' 'soundfile==0.13.1' 'torch==2.5.1' 'transformers==4.51.3'
axcl-smi
```

模型及样例约 2.23GB，另为 Python 依赖、下载缓存和输出预留空间。模型下载完成后，推理只读取本地文件。保留前面下载步骤中的 `MODEL_DIR` 变量。

需要重新编译配套库时，在安装 AXCL 开发头文件的主机执行：

```bash
cd ~/edgeaccel/jina-nano-retrieval
g++ -std=c++17 -O2 -shared -fPIC -Wall -Wextra -Werror \
  jina_native_bridge.cpp -I/usr/include/axcl -L/usr/lib/axcl \
  -laxcl_rt -laxcl_npu -Wl,-rpath,/usr/lib/axcl \
  -o libjina_native_bridge.so
```

## 运行图片与视频帧检索

用仓库中的龙虾图片、小熊猫视频帧，检索六条文字描述：

```bash
python - "$MODEL_DIR" <<'PY'
import json, sys
from pathlib import Path
model = Path(sys.argv[1]).resolve()
requests = [
    {"id": "image", "modality": "image", "role": "query",
     "file": str(model / "assets/sample.png")},
    {"id": "video", "modality": "video", "role": "query",
     "file": str(model / "assets/red-panda-openai.frames")}
]
descriptions = {
    "lobster": "A red cartoon lobster with large claws on a white background.",
    "pandas": "Red pandas climb on branches in an outdoor enclosure.",
    "ocean": "A sunset over the ocean.",
    "car": "An automobile driving on a highway.",
    "finance": "Financial markets and quarterly company earnings.",
    "snow": "A snowy mountain landscape."
}
requests += [{"id": k, "modality": "text", "role": "document", "text": v}
             for k, v in descriptions.items()]
Path.home().joinpath('edgeaccel/jina-retrieval-inputs.json').write_text(
    json.dumps(requests, ensure_ascii=False, indent=2), encoding='utf-8')
PY

python ~/edgeaccel/jina-nano-retrieval/jina_retrieval_card.py \
  --model-dir "$MODEL_DIR" --inputs ~/edgeaccel/jina-retrieval-inputs.json \
  --output ~/edgeaccel/results/jina-retrieval-01
```

输出目录须尚不存在。读取实际排名：

```bash
python - <<'PY'
import json
from pathlib import Path
r = json.loads(Path.home().joinpath(
    'edgeaccel/results/jina-retrieval-01/result.json').read_text(encoding='utf-8'))
print('完成：', r['completed'])
for i in [0, 1]:
    ranked = sorted(range(2, len(r['calls'])),
                    key=lambda j: r['similarityMatrix'][i][j], reverse=True)
    print(r['calls'][i]['id'])
    for j in ranked:
        print(r['calls'][j]['id'], round(r['similarityMatrix'][i][j], 6))
PY
```

图片缩放到 256 × 256，转换为 64 个特征 token。视频输入为按文件名排序的图片目录，本例使用仓库中的三张抽帧图片；每帧分别编码后合并为 192 个特征 token。本入口不直接解码 MP4，也不分析视频音轨。对自有视频先抽帧并检查顺序，再传入帧目录。

## 运行文本检索

把输入 JSON 改为查询与候选文本，运行命令沿用前一节，并更换输出目录：

```json
[
  {"id": "query", "role": "query", "text": "Which planet is known as the Red Planet?"},
  {"id": "mars", "role": "document", "text": "Mars is often called the Red Planet because of its reddish surface."},
  {"id": "finance", "role": "document", "text": "Quarterly revenue increased while operating costs declined."}
]
```

`similarityMatrix[0][1]` 为查询与火星描述的分数，`similarityMatrix[0][2]` 为查询与财务描述的分数。本次分别为 **0.769048**、**0.014609**。分数是余弦相似度，不是概率。

## 编码 8 秒与 30 秒音频

音频必须为 **16kHz、单声道**，时长不超过所选规格。使用仓库的两个 WAV 样例：

```bash
python - "$MODEL_DIR" <<'PY'
import json, sys
from pathlib import Path
model = Path(sys.argv[1]).resolve()
requests = [
    {"id": f"audio-{seconds}s", "modality": "audio", "role": "query",
     "file": str(model / f"assets/audio_test_chunk0_{seconds}s.wav"),
     "audioSeconds": seconds}
    for seconds in [8, 30]
]
Path.home().joinpath('edgeaccel/jina-audio-inputs.json').write_text(
    json.dumps(requests, indent=2), encoding='utf-8')
PY

python ~/edgeaccel/jina-nano-retrieval/jina_retrieval_card.py \
  --model-dir "$MODEL_DIR" --inputs ~/edgeaccel/jina-audio-inputs.json \
  --output ~/edgeaccel/results/jina-audio-01
```

8 秒、30 秒规格分别补齐到 800、3000 个 Mel 帧，输出 200、750 个音频特征 token，再进入文本编码部分。较短录音同样按所选规格补齐。本页验证了两个规格的向量输出和参考向量一致性；音频不会直接返回转录文本。建立音文检索时，需要另外编码候选描述，并用业务录音检查排名。

## 检查输出与输入范围

`result.json` 的 `completed` 应为 `true`。每个 `calls` 项包含 768 维 `embedding`、`tokenCount` 和 `requestSeconds`；`similarityMatrix` 的行列顺序与输入一致。相似度比较应使用本模型编码的查询和候选，不混入其他模型生成的向量。

运行包按每块 128 个 token 编码，保留前面块的缓存，模板与 EOS 计入长度。总长限制为 1024 token，超长输入直接报错。分块编码与整段一次执行双向注意力并不完全相同，应结合下方参考向量差异评估业务效果。

`requestSeconds` 包含当前请求的预处理、模型加载和推理；首次音频请求还包含音频依赖初始化。不含进程启动、共享分词器和词向量初始化、最终结果写盘。当前逐请求加载模型，耗时用于复现本页流程，不代表常驻服务吞吐率。
