## 准备双目推理环境

本例在 RK3576 + AX8850 16GB M.2 上运行 IGEV++，将官方 7 组左右目图片转换为视差图。使用 `models/AX650_RTIGEV.axmodel` 通过 AXCL 推理，并使用同仓库 `models/AX650.onnx` 在主机 CPU 上对照输出。

在已安装 PyAXEngine 的 Python 环境执行：

```bash
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'Pillow==11.3.0' \
  'onnxruntime==1.20.1' matplotlib tqdm
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认列表包含 `AXCLRTExecutionProvider`，设备 0 可用。CPU 对照使用两个线程；模型加载和 CPU 推理耗时与算力卡推理分开记录。

下载 [IGEV++ 算力卡示例](../../../static/examples/igev_card.py)，保存为 `~/edgeaccel/igev_card.py`。例程核对官方脚本版本，沿用其图片缩放与输入归一化方法。

## 运行七组双目图片

保持下载步骤中的 `MODEL_DIR`，指定一个尚不存在的输出目录：

```bash
python ~/edgeaccel/igev_card.py --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/igev-01
```

每组输入按官方方法缩放到 512 × 384。算力卡接收 RGB `uint8` NHWC 输入；CPU 参考接收归一化到 `[-1, 1]` 的 `float32` NCHW 输入。每组图片在算力卡上运行两次，在 CPU 上运行一次。

程序逐组打印推理耗时和与 CPU 输出的平均绝对误差。全部七组完成后，`deployment-result.json` 中的 `completed` 为 `true`；`repeatExact` 记录两次算力卡原始输出是否一致。

## 查看视差和数值对照

以 `Adirondack` 为例：

| 输出文件 | 内容 |
| --- | --- |
| `Adirondack-left.png`、`Adirondack-right.png` | 实际送入模型的左右目图片 |
| `Adirondack-card.png` | 算力卡输出视差图 |
| `Adirondack-cpu.png` | CPU ONNX 参考视差图 |
| `Adirondack-error.png` | 两份原始视差的绝对差值 |
| `Adirondack-raw.npz` | 未裁剪的原始视差、重复输出和输入张量 |
| `deployment-result.json` | 全部图片、版本校验、耗时和误差统计 |

视差图统一使用 0–128 像素色阶，蓝色较小、红色较大；误差图统一使用 0–16 像素色阶。超出范围的颜色会截断，原始数值仍完整保存在 NPZ 中。

视差单位是 **512 × 384 输入图上的像素**，不能直接解释为米。真实距离还需要双目相机标定参数。CPU ONNX 用于数值对照，并非视差标注真值；与 CPU 接近不能代替 EPE、D1 等数据集精度评估。

下方展示本次实际输入、输出及统计，算力卡耗时为 `session.run` 的主机侧计时，包含数据传输，不含模型加载、图片缩放、CPU 参考和文件保存。
