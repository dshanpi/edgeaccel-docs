## 准备 Python 环境

先完成 [AXCL Python 环境](../../usage/python.md)，确认可用执行后端包含 `AXCLRTExecutionProvider`。本例使用 PyAXEngine 0.1.3.rc3、NumPy 1.26.4 和 Pillow。

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'pillow==11.3.0'
python -c "import axengine; print(axengine.get_available_providers())"
```

## 运行官方公交车样例

下载 [Deformable-DETR 算力卡示例](../../../static/examples/deformable_detr_card.py)，保存为 `~/edgeaccel/deformable_detr_card.py`。保持上文下载步骤中的 `MODEL_DIR`，指定一个尚不存在的输出目录：

```bash
python ~/edgeaccel/deformable_detr_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/deformable-detr-bus \
  --threshold 0.6
```

程序从固定仓库读取 `output/detr.axmodel` 和 `assets/bus.jpg`，显式使用 AXCL。图像缩放、左上角对齐、黑色填充及坐标还原沿用官方 `src/inference.py`；按该脚本关闭均值和标准差归一化。

同一图片运行三次，输出目录包含：

| 文件 | 内容 |
| --- | --- |
| `input.png` | 本次实际输入图片 |
| `output-1.png` 至 `output-3.png` | 三次推理各自的检测框和类别 |
| `deployment-result.json` | 框坐标、类别、置信度和每次推理耗时 |
| `raw-1.npz` 至 `raw-3.npz` | 原始输出张量，供进一步核对 |

在桌面图片查看器中打开 `output-1.png`，即可查看本次生成的结果。`--threshold` 控制保留候选框的最低置信度；下方实测使用 `0.6`。框的数量不能直接当作真实目标数量，仍需对照原图检查误检和漏检。
