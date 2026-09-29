## 准备视频处理环境

在 RK3576 主机激活已安装 [PyAXEngine](../../usage/python.md) 的环境，安装视频和相似度计算依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'torch==2.5.1' tqdm
python -c "import axengine; print(axengine.get_available_providers())"
```

确认输出包含 `AXCLRTExecutionProvider`。下载 [RIFE 算力卡例程](../../../static/examples/rife_card.py)，保存为 `~/edgeaccel/rife_card.py`。

## 生成插帧视频

保持下载步骤中的 `MODEL_DIR`，先运行 720p 规格：

```bash
python ~/edgeaccel/rife_card.py \
  --model-dir "$MODEL_DIR" \
  --resolution 720p \
  --output ~/edgeaccel/results/rife-720p
```

例程读取官方 `video/demo.mp4`，采用官方脚本的帧相似度判断、RGB 浮点输入、补边和结果裁剪流程。完整模型在算力卡执行，只将最终图像取回主机。视频帧队列限制为 2，写入线程结束后才关闭输出文件，避免主机积压大量图像。本例固定使用上述 PyAXEngine 0.1.3.rc3。

本页已验证范围为 `rife_x2_720p.axmodel`，输入为 1280×720。官方仓库另有 1080p 和 4K 权重，目前未在本页环境完成推理，不能直接沿用 720p 的验证结论。输出目录需要尚不存在。

## 打开本次输出

在桌面视频播放器中打开结果目录中的 `interpolated.mp4`，查看插帧后的运动。官方样例包含 128 帧、帧率为 25 fps；本次输出应能解码为 255 帧、50 fps。

| 文件 | 内容 |
| --- | --- |
| `interpolated.mp4` | 本次完整插帧视频，不包含音轨 |
| `left.png`、`right.png` | 第一次实际 NPU 调用的两张输入帧 |
| `middle.png` | 该次 NPU 调用生成的中间帧 |
| `deployment-result.json` | 文件校验、分辨率、帧数、调用次数与耗时 |

例程额外重复第一次 NPU 调用，核对输出一致性；这次重复不写入视频。50 fps 是输出视频的播放帧率，不能用来表示处理速度。实际推理调用和整段处理耗时见下方实测记录。

下方网页视频由本次输入与输出转码为 H.264，保留尺寸、帧率和帧数，不包含音轨；三张静态帧图以无损格式保存。
