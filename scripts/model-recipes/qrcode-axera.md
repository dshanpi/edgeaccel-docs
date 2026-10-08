## 安装检测与解码依赖

本页使用仓库内全部 9 个 AX650 模型及 48 张样例图片。神经网络检测在 M.2 卡上执行，图像前后处理和 ZBar 二维码解码在 RK3576 主机执行。

在 Ubuntu 24.04 主机安装解码库，并激活已安装 PyAXEngine 的独立环境：

```bash
sudo apt-get install -y libzbar0t64
source ~/edgeaccel/python-env/bin/activate
python -m pip install \
  'numpy==1.26.4' 'pillow==11.3.0' \
  'torch==2.5.1' 'torchvision==0.20.1' \
  'matplotlib==3.10.8' 'pyyaml==6.0.3' 'pyzbar==0.1.9'
python -m pip check
```

下载配套运行脚本 [qrcode_card.py](../../../static/examples/qrcode_card.py)，复制到主机的 `$MODEL_DIR/qrcode_card.py`。脚本调用同版本官方前后处理，将推理后端显式设为 `AXCLRTExecutionProvider`，并保留修改前的源码副本。

## 运行一个检测模型

先运行 YOLO11n。下载本页的[测试二维码](../../../static/validation/effects/qrcode-axera/inputs/edgeaccel-qr.png)，保存为 `$MODEL_DIR/images/edgeaccel-qr.png`。输出目录必须尚不存在，防止混入上一次的结果。

```bash
cd "$MODEL_DIR"
python qrcode_card.py --model-dir . \
  --weight yolo11n_650_npu1.axmodel \
  --images edgeaccel-qr.png \
  --output results/yolo11n
```

日志应显示 `AXCLRTExecutionProvider`，随后逐张输出 `boxes` 和 `decoded` 数量。`boxes` 表示检测到的区域数量；`decoded` 表示在裁剪区域中成功解码的结果数量。存在检测框不代表一定能够读出二维码文字。

脚本会生成标注图片和 `qrcode-result.json`，其中保留框坐标、解码文字、输入文件校验值及单图耗时。解码文字应与配套 `qrcode-result.json` 中该输入的原始记录一致。省略 `--images` 时处理仓库内的 48 张 JPG 样例。

## 运行其余模型

以下命令在主机上依次运行全部 9 个 AX650 权重，每个权重处理同一张测试二维码。`results/all` 应是新的输出目录：

```bash
cd "$MODEL_DIR"
for weight in model/AX650/*.axmodel; do
  name=$(basename "$weight" .axmodel)
  python qrcode_card.py --model-dir . \
    --weight "$(basename "$weight")" \
    --images edgeaccel-qr.png \
    --output "results/all/$name" || break
done
```

YOLOv5、YOLOv8 系列、YOLO26、NanoDet 和 DEIMv2 分别采用仓库中的对应前后处理。AX620E、AX637 目录面向其他芯片，本页没有下载或验证这些权重。

本次 NanoDet 未检测到这张测试图中的二维码；其余 8 个变体解码文字与原文一致。默认阈值和前后处理保持官方实现，不能仅根据推理进程正常退出判断识别正确。
