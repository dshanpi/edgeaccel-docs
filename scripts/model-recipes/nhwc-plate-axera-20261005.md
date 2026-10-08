## 运行 NHWC 变体（可选）

默认步骤使用NCHW权重。下列NHWC变体需要配套的输入布局处理，不能只替换模型文件名。

### 准备例程

在RK3576主机激活前文安装的PyAXEngine环境。下载[NHWC视觉运行包](../../../static/examples/vision-nhwc-deployment-20261005.zip)，保存到 `~/edgeaccel`，然后解压：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m zipfile -e ~/edgeaccel/vision-nhwc-deployment-20261005.zip ~/edgeaccel
```

### 下载对应权重和样例

```bash
NHWC_MODELS=~/edgeaccel/models-nhwc
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Plate-axera \
  --revision e528f3e145f0ec35e3c2c05a019d8369d6fdef3c \
  --include "axmodel_infer_pld.py" "test.jpg" "AX650/pld_650_nhwc_npu3.axmodel" "axmodel_infer_plr.py" "苏A8A68Y.jpg" "AX650/plr_650_nhwc_npu3.axmodel" \
  --local-dir "$NHWC_MODELS/Plate-axera"
```

### 运行并查看输出

```bash
python ~/edgeaccel/vision-nhwc/vision_nhwc.py \
  --models-root "$NHWC_MODELS" --case plate-detection \
  --output ~/edgeaccel/results/plate-detection-nhwc
python ~/edgeaccel/vision-nhwc/vision_nhwc.py \
  --models-root "$NHWC_MODELS" --case plate-recognition \
  --output ~/edgeaccel/results/plate-recognition-nhwc
```

每次使用尚不存在的结果目录。程序应显示 `AXCLRTExecutionProvider`；输出图或终端识别文字应与下方NHWC效果一致。运行包保留固定版本原始前后处理，实际使用的输入布局为NHWC。

`plate-detection` 使用整车图生成 `det_res.jpg`；`plate-recognition` 使用仓库裁剪车牌图，在终端输出识别文字与颜色。本节验证两个独立入口，未将NHWC检测框裁剪结果串接到识别模型。
