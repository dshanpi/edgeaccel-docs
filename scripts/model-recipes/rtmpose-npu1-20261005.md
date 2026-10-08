## 运行 rtmpose-npu1 变体

### 准备运行包

在 RK3576 主机激活前文安装的 PyAXEngine 环境，下载[视觉变体运行包](../../../static/examples/vision-variant-deployment-20261005.zip)，保存到`~/edgeaccel`并解压到 `~/edgeaccel`。

```bash
source ~/edgeaccel/python-env/bin/activate
python -m zipfile -e ~/edgeaccel/vision-variant-deployment-20261005.zip ~/edgeaccel
```

### 下载权重和样例

```bash
VARIANT_MODELS=~/edgeaccel/models-variants
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/RTMPose \
  --revision 726c3acf17cff3a13958bc30da0aa6bf125312b1 \
  --include "README.md" "ax_infer.py" "config.json" "export_onnx.py" "onnx_infer.py" "replace_hardsigmoid.py" "test.jpg" "AX650/rtmpose_m_npu1.axmodel" \
  --local-dir "$VARIANT_MODELS/RTMPose"
```

### 运行模型

```bash
python ~/edgeaccel/vision-variant/vision_variant.py \
  --models-root "$VARIANT_MODELS" --case rtmpose-npu1 \
  --output ~/edgeaccel/results/rtmpose-npu1
```

使用尚不存在的结果目录。终端应显示 `AXCLRTExecutionProvider`，结果目录中应生成输出图。
