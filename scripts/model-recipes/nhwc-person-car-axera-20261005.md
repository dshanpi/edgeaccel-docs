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
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Person_car-axera \
  --revision 20e3e18e65c7874da8e6dbe65e248dfb5a48ddde \
  --include "ax_pcd_infer.py" "car_away_1920x1080.jpg" "AX650/ax_ax650_pcd_max_800_480_rgb_nhwc_V2.0.0.axmodel" "AX650/ax_ax650_pcd_tiny_algo_rgb_nhwc_V2.0.0.axmodel" \
  --local-dir "$NHWC_MODELS/Person_car-axera"
```

### 运行并查看输出

```bash
python ~/edgeaccel/vision-nhwc/vision_nhwc.py \
  --models-root "$NHWC_MODELS" --case person-car-max \
  --output ~/edgeaccel/results/person-car-max-nhwc
python ~/edgeaccel/vision-nhwc/vision_nhwc.py \
  --models-root "$NHWC_MODELS" --case person-car-tiny \
  --output ~/edgeaccel/results/person-car-tiny-nhwc
```

每次使用尚不存在的结果目录。程序应显示 `AXCLRTExecutionProvider`；输出图或终端识别文字应与下方NHWC效果一致。运行包保留固定版本原始前后处理，实际使用的输入布局为NHWC。

max变体沿用原脚本BGR输入，tiny变体沿用RGB输入；运行包分别处理，不需要手动交换颜色通道。
