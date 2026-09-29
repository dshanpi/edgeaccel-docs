## 安装分类依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'pillow==11.3.0'
python -m pip check
```

## 指定算力卡后端

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
p = Path('python/inference.py')
s = p.read_text()
old = 'axengine.InferenceSession(model_path)'
new = 'axengine.InferenceSession(model_path, providers=["AXCLRTExecutionProvider"])'
if old in s:
    backup = p.with_suffix('.py.upstream')
    if not backup.exists():
        backup.write_text(s)
    p.write_text(s.replace(old, new))
else:
    assert new in s, '源码与固定版本不匹配'
PY
```

## 准备公交车图片

下载[实测输入图片](../../../static/validation/effects/mobilenetv3-small/input.jpg)，复制到主机的 `$MODEL_DIR/input.jpg`，然后校验：

```bash
cd "$MODEL_DIR"
printf '%s  %s\n' \
  '33b198a1d2839bb9ac4c65d61f9e852196793cae9a0781360859425f6022b69c' \
  input.jpg | sha256sum -c -
```

## 运行分类

本版本官方 Python 示例按 RGB 读取图片，模型元数据写的是 BGR。下面先复现 Python 示例的 RGB 输入，再单独运行 BGR 对照；两种输入的实测结果均未正确识别公交车，当前仅确认模型能够执行。

```bash
cd "$MODEL_DIR"
CHANNEL_ORDER=RGB PYTHONPATH="$MODEL_DIR/python" python - <<'PY'
import json, os
import numpy as np
from PIL import Image
from inference import MobileNetV3Classifier
data = np.array(Image.open('input.jpg').resize((224, 224)), dtype=np.float32)
data = data.transpose(2, 0, 1)[None] / 255.0
order = os.environ['CHANNEL_ORDER']
assert order in ['RGB', 'BGR']
if order == 'BGR':
    data = np.ascontiguousarray(data[:, ::-1, :, :])
model = MobileNetV3Classifier('models/model.axmodel')
for i in range(3):
    logits = model.classify(data)[0]
    assert np.isfinite(logits).all()
    probs = np.exp(logits - logits.max())
    probs /= probs.sum()
    top5 = [{'class_id': int(j), 'confidence': float(probs[j])}
            for j in np.argsort(-logits)[:5]]
    print(json.dumps({'round': i + 1, 'order': order, 'top5': top5}))
PY
```

日志应显示 `AXCLRTExecutionProvider`，输出张量含 1000 个分类分值。将上面命令中的 `CHANNEL_ORDER=RGB` 改为 `CHANNEL_ORDER=BGR` 后重新执行，即可复现下方 BGR 对照。没有证据表明仅交换通道即可恢复本版本的分类效果。
