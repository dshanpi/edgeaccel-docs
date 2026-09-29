## 安装图像处理依赖

在 RK3576 主机激活已安装 PyAXEngine 的环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0' 'torch==2.5.1' 'torchvision==0.20.1'
python -m pip check
```

下载 [enhancement_card.py](../../../static/examples/enhancement_card.py) 和 [image-enhancement-cases.json](../../../static/examples/image-enhancement-cases.json)，保存到 `$MODEL_DIR`。运行脚本复用固定版本官方前后处理，指定 `AXCLRTExecutionProvider`，并把输入、模型和输出目录替换为本页路径。

## 运行配套样例

以下命令按顺序运行本仓库全部已选变体。使用新的结果目录；同名目录已存在时脚本停止，避免混入旧图。

```bash
cd "$MODEL_DIR"
for name in codeformer-pipeline; do
  python enhancement_card.py --model-dir . \
    --cases image-enhancement-cases.json --case "$name" \
    --output "results/$name" || break
done
```

确认日志使用 `AXCLRTExecutionProvider`，退出码为 0，并在 `results/变体名称/outputs/` 中生成图片。`enhancement-result.json` 记录实际执行的权重、输入校验值、输出尺寸和耗时。只运行一种算法时，将循环中的名称改为对应名称。

本例必须同时执行 `yolov5l-face.axmodel`、`codeformer.axmodel` 与 `realesrgan-x2.axmodel`。最终整图位于 `results/codeformer-pipeline/outputs/outputs/final_results/`；只生成人脸裁剪图不代表整条流程完成。
