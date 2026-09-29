## 安装推理依赖

LivePortrait 用一张人像作为外观来源，再用图片或视频驱动其表情。下面在 RK3576 主机上运行 Python 示例，四个生成网络使用 M.2 算力卡的 `AXCLRTExecutionProvider`，人脸检测、关键点和 `warp.onnx` 使用 CPU。

沿用上方下载得到的 `$MODEL_DIR`，在已安装 PyAXEngine 的环境中执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'onnx==1.18.0' \
  'onnxruntime==1.20.1' 'opencv-python-headless==4.11.0.86' \
  'torch==2.5.1' 'scikit-image==0.25.2' \
  'loguru==0.7.3' 'imageio==2.37.4' 'imageio-ffmpeg==0.6.0' \
  requests tqdm
sudo apt-get install -y ffmpeg
ffmpeg -version
```

本页测试环境为约4GB内存的 RK3576 和16GB算力卡。下载文件约444MB，运行时还需保存中间结果和视频，请额外预留存储空间。

| 文件 | 执行位置 | 用途 |
| --- | --- | --- |
| `feature_extractor.axmodel` | 算力卡 | 提取源人像特征 |
| `motion_extractor.axmodel` | 算力卡 | 提取姿态和表情 |
| `stitching_retargeting.axmodel` | 算力卡 | 修正驱动关键点 |
| `spade_generator.axmodel` | 算力卡 | 生成512×512人像 |
| `warp.onnx` | CPU | 按驱动关键点变形特征 |
| `det_10g.onnx`、`2d106det.onnx`、`landmark.onnx` | CPU | 人脸检测、裁剪和关键点跟踪 |

保持上方下载清单的目录结构。示例只加载人像裁剪需要的模型；`buffalo_l` 目录中应仅有 `det_10g.onnx` 和 `2d106det.onnx`。身份特征、年龄性别、3D人脸和动物关键点模型不属于本页运行流程。

## 运行图片驱动

下载 [LivePortrait 算力卡示例](../../../static/examples/liveportrait_card.py)，保存为 `~/edgeaccel/liveportrait_card.py`：

```bash
python ~/edgeaccel/liveportrait_card.py \
  --model-dir "$MODEL_DIR" \
  --mode image \
  --output ~/edgeaccel/results/liveportrait-image-01
```

输出目录须尚不存在。程序依次运行 `s0.jpg + d8.jpg`、`s5.jpg + d8.jpg`，再重复第一组输入。它使用官方图像处理和动画计算流程，显式选择 AXCL 后端，将 CPU 推理限制为2线程，并保存真实输入输出。

| 输出 | 内容 |
| --- | --- |
| `s0-d8/s0--d8_concat.jpg` | 左：驱动图片；中：源人像裁剪；右：生成结果 |
| `s0-d8-000-crop.png` | 512×512生成图，无JPEG压缩 |
| `s0-d8-000-pasteback.png` | 将生成的人脸贴回原图后的结果 |
| `deployment-result.json` | 后端、输入输出校验值、调用耗时和完成状态 |
| `raw-*.npz` | 生成网络的原始张量及裁剪几何，可保留用于复核 |

`deployment-result.json` 中 `"completed": true` 表示本次流程执行完成。先查看本页下面的实际效果，再打开本机生成的拼接图核对。

## 运行短视频驱动

使用官方 `d0.mp4`，每5帧取1帧，共处理8帧：

```bash
python ~/edgeaccel/liveportrait_card.py \
  --model-dir "$MODEL_DIR" \
  --mode video --frames 8 --stride 5 \
  --output ~/edgeaccel/results/liveportrait-video-01
```

在输出目录的 `s0-d0-short` 子目录中打开 `s0--d0_concat.mp4` 查看“驱动帧—源人像—生成帧”对照，打开 `s0--d0.mp4` 查看贴回原图的动画。示例生成无声视频；播放帧率按原视频帧率除以采样间隔计算，与推理速度无关。

每帧的原始 PNG 也会保存。`--frames` 可设置为1～32，`--stride` 可设置为1～30；先用少量帧检查输入，再增加帧数。CPU变形网络耗时较长，当前示例用于离线生成。

## 使用自己的输入

源图片应包含清晰、无遮挡的人脸。驱动图片或视频应预先裁剪为以人脸为中心的画面；官方流程会直接缩放驱动画面，不能用宽幅全景视频替代人脸裁剪。

```bash
python ~/edgeaccel/liveportrait_card.py \
  --model-dir "$MODEL_DIR" \
  --source ~/Pictures/portrait.jpg \
  --driving ~/Pictures/expression.jpg \
  --output ~/edgeaccel/results/liveportrait-custom-01
```

视频输入使用 `--mode video --driving ~/Videos/face.mp4`，同时指定 `--source`。无脸图片会停止处理；检测到多人时按人脸大小选择一张，不会同时驱动全部人物。

本页验证了图片驱动、重复结果、短视频生成和贴回几何。表情生成会改变局部纹理和面部细节，尚未完成浮点参考、完整画质评估、长视频稳定性及实际8GB卡回归。
