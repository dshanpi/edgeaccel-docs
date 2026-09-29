## 安装例程依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程指定 `AXCLRTExecutionProvider`，使用本页固定版本的权重和样例，并保存本次输出。

本例还需要以下前处理依赖：

```bash
python -m pip install 'torch==2.5.1' 'torchvision==0.20.1'
```

## 运行 EDSR 与 ESPCN

```bash
cd "$MODEL_DIR"
for name in edsr edsr-2k espcn espcn-2k; do
  python vision_card.py --model-dir . --task super-resolution --variant "$name" \
    --output "results/$name" || break
done
```

例程读取官方 `video/test_1920x1080.mp4` 的第一帧，按权重的固定输入尺寸缩放，同一帧运行 3 次。EDSR 保持官方示例的 BGR、0–255 输入；ESPCN 运行亮度通道网络，再与插值后的色度通道合成。

| 参数 | 输入宽×高 | 输出宽×高 |
| --- | --- | --- |
| `edsr`、`espcn` | 1920×1080 | 3840×2160 |
| `edsr-2k`、`espcn-2k` | 1280×720 | 2560×1440 |

每个目录包含 `input.png`、`output.png` 和 `deployment-result.json`。放大查看文字、地砖边缘与颜色。本页展示固定帧推理，尚未验证整段视频的连续处理和帧率。
