## 安装例程依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程指定 `AXCLRTExecutionProvider`，使用本页固定版本的权重和样例，并保存本次输出。

## 运行 2 倍与 4 倍超分辨率

在模型目录执行，两种倍率分别生成结果目录：

```bash
cd "$MODEL_DIR"
for scale in x2 x4; do
  python vision_card.py --model-dir . --task realesrgan --variant "$scale" \
    --output "results/$scale" || break
done
```

输入为 `pics/0014.jpg`。例程按 108 像素分块，两侧各补 10 像素，使用 128×128 模型输入；推理后裁除边缘并拼接。不要把 x2 权重与 x4 的输出倍率混用。

检查 `results/x2/output.png`、`results/x4/output.png`，输出宽高应分别为输入的 2 倍和 4 倍。结果目录已存在时换用新目录，避免混入旧图片。
