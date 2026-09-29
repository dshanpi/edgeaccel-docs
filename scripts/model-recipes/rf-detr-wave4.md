## 安装例程依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程指定 `AXCLRTExecutionProvider`，使用本页固定版本的权重和样例，并保存本次输出。

## 检测图片中的车辆与信号灯

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task rf-detr --variant default \
  --output results/traffic
```

输入为 `asserts/test.jpg`，使用官方缩放、后处理和 COCO 类别映射，阈值为 0.3。同一图片连续推理 3 次，`results/traffic/output.png` 保存最后一次检测图，`deployment-result.json` 保留三次框坐标与分数。

先检查车辆框与图像位置是否对应，再检查远处小目标。候选框数量不是图片中目标数量的人工真值。
