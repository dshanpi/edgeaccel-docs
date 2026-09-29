## 安装例程依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程指定 `AXCLRTExecutionProvider`，使用本页固定版本的权重和样例，并保存本次输出。

## 跟踪视频中的指定目标

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task mixformer --variant car60 \
  --output results/tracking
```

输入为 `car.avi`。沿用官方首帧目标框 `[1079, 482, 99, 106]`，四个数依次为 x、y、宽、高；随后连续处理 60 帧。此坐标只适用于该样例，换视频时需要重新指定初始目标。

打开 `results/tracking/tracking.gif` 查看连续跟踪，`frame-001.png`、`frame-030.png`、`frame-060.png` 保留原尺寸关键帧。动画每两帧取一帧，按源视频时间间隔播放，不代表实际推理帧率。每帧坐标和置信度见 `deployment-result.json`。
