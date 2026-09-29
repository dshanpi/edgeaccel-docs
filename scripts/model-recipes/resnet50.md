## 安装分类依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'pillow==11.3.0'
python -m pip check
```

## 指定算力卡后端

在前一节下载的模型目录执行。只修改推理后端，图片缩放、归一化和分类后处理继续使用同版本官方 SDK。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
p = Path('python/resnet50_sdk/inference.py')
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

下载下方效果展示使用的[输入图片](../../../static/validation/effects/resnet50/input.jpg)，复制到主机的 `$MODEL_DIR/input.jpg`。在主机检查文件：

```bash
cd "$MODEL_DIR"
printf '%s  %s\n' \
  '33b198a1d2839bb9ac4c65d61f9e852196793cae9a0781360859425f6022b69c' \
  input.jpg | sha256sum -c -
```

## 输出 Top-5 分类

```bash
cd "$MODEL_DIR"
PYTHONPATH="$MODEL_DIR/python" python - <<'PY'
import json
from resnet50_sdk import ResNet50Classifier
model = ResNet50Classifier('models/model.axmodel')
for i in range(3):
    result = model.classify('input.jpg', top_k=5)
    print(json.dumps({'round': i + 1, 'top5': result}, ensure_ascii=False))
PY
```

日志应显示 `AXCLRTExecutionProvider`，每次输出 5 个类别编号及分数。本版本 SDK 只内置部分标签，因此部分结果显示为 `class_654` 等名称；下方展示按完整 ImageNet 类别表映射的英文标签。

本例使用 RGB、224×224 缩放及 SDK 自带的 ImageNet 均值和标准差，输入为 NCHW / float32。替换图片时保留这套前处理；三次同图重复只检查输出一致性。
