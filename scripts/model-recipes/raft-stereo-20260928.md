## 准备双目推理例程

在 RK3576 主机激活已安装 [PyAXEngine](../../usage/python.md) 的环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'matplotlib==3.10.8'
python -c "import axengine; print(axengine.get_available_providers())"
```

确认包含 `AXCLRTExecutionProvider`。下载 [RAFT-Stereo 算力卡例程](../../../static/examples/raft_stereo_card.py)，保存为 `~/edgeaccel/raft_stereo_card.py`。

本页使用官方 AX650 目录中的两份权重。文件名中的 `steoro` 沿用上游命名，不要自行改为 `stereo`。

| 选项 | 权重 | 输入宽×高 |
| --- | --- | --- |
| `r1` | `raft_steoro256x640_r1.axmodel` | 640×256 |
| `r4` | `raft_steoro384x1280_r4.axmodel` | 1280×384 |

## 生成两种规格的视差图

保持下载步骤中的 `MODEL_DIR`。先运行 `r1`，结束后再运行 `r4`：

```bash
python ~/edgeaccel/raft_stereo_card.py \
  --model-dir "$MODEL_DIR" --variant r1 \
  --output ~/edgeaccel/results/raft-r1

python ~/edgeaccel/raft_stereo_card.py \
  --model-dir "$MODEL_DIR" --variant r4 \
  --output ~/edgeaccel/results/raft-r4
```

输出目录需要尚不存在。每个规格处理 `examples/left` 和 `examples/right` 中同名的 10 对图片，每对重复两次。

例程沿用官方 RGB、uint8、NHWC 图像处理方式，并显式选择算力卡后端。输出视差缩放回原图尺寸，数值乘以“原图宽度 / 模型输入宽度”。输入左右图不可交换，尺寸必须一致。

## 查看视差结果

打开输出目录中的 `*-disparity.png`，对照同名 `*-left.png`、`*-right.png`。

| 文件 | 内容 |
| --- | --- |
| `*-left.png`、`*-right.png` | 实际左右目输入 |
| `*-disparity.png` | 本次视差图，统一采用 0–256 像素色阶 |
| `*-raw.npz` | 原始模型输出及恢复到原图尺寸的像素视差 |
| `deployment-result.json` | 输入校验、尺寸、两次一致性、耗时和视差统计 |

蓝色表示较小视差，红色表示较大视差；超出 256 的值只在显示时截断，原始数组仍完整保存。视差不是米制距离，实际测距需要已标定、已校正的双目相机和对应参数。

完成后，记录中的 `completed` 应为 `true`，具有 10 对输入结果，重复输出一致且数值有限。以下展示两种规格的全部实测结果；车辆边缘、遮挡和路面异常需结合参考视差进一步判断。
