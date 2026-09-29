## 准备分割例程

在 RK3576 主机激活已安装 [PyAXEngine](../../usage/python.md) 的环境，安装图像处理依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86'
python -c "import axengine; print(axengine.get_available_providers())"
```

确认输出包含 `AXCLRTExecutionProvider`。下载 [MobileSAM 算力卡例程](../../../static/examples/mobilesam_card.py)，保存为 `~/edgeaccel/mobilesam_card.py`。

## 运行点提示和框提示

保持上文下载步骤中的 `MODEL_DIR`，指定一个尚不存在的结果目录：

```bash
python ~/edgeaccel/mobilesam_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/mobilesam
```

例程使用 `mobile_sam_encoder_650.axmodel` 和 `mobile_sam_decoder_650.axmodel`，显式选择 AXCL。编码器将图片按比例缩放、右侧与底部补边到 1024×1024；解码器接收提示坐标，输出四个候选掩码，并按模型预测分数选择一个。

本例沿用官方提示坐标：足球图片运行 3 个点提示、4 个框提示，车辆图片运行 1 个点提示、4 个框提示。坐标单位为原图像素；点格式为 `(x,y)`，框格式为 `(左上角 x,左上角 y,宽,高)`。

| 输出文件 | 内容 |
| --- | --- |
| `test-input.png`、`truck-input.png` | 实际输入图片 |
| `*-overlay.png` | 提示位置和绿色分割区域叠加图 |
| `*-mask.png` | 选中掩码，按官方步骤缩放回原图 |
| `*-raw.npz` | 解码器原始掩码和预测分数 |
| `deployment-result.json` | 提示坐标、选中掩码、重复运行核对和耗时 |

打开 `*-overlay.png` 查看效果。点选可能得到衣服、车窗等局部区域；需要完整目标时，对照框提示结果。模型给出的预测分数用于选择掩码，不等于用人工标注测得的 IoU。

本例每张图片编码两次，每组提示解码两次，并检查输出是否一致。掩码按官方顺序先以 `>0` 阈值处理，再用双线性插值放大、裁剪；边缘可能出现中间灰度，不能把灰度值当作模型置信度。
