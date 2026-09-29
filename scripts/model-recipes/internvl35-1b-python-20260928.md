## 准备图文推理环境

本例在 **RK3576 + AX8850 16GB M.2** 上运行 InternVL3.5-1B。视觉编码、28 层语言模型和输出层均通过 AXCL 执行；分词、图像处理和 KV 缓存由主机管理。

在已安装 PyAXEngine 的 AXCL Python 环境中准备依赖：

```bash
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchvision==0.20.1' \
  'transformers==4.51.3' 'ml-dtypes==0.5.3' 'Pillow==11.3.0' \
  'onnxruntime==1.20.1' tqdm
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认提供者列表包含 `AXCLRTExecutionProvider`，设备 0 可用。本次使用 PyAXEngine `0.1.3.rc3`。此处版本对应本页的固定权重与运行示例，安装后保持同一 Python 环境运行。

下载 [InternVL3.5 算力卡运行示例](../../../static/examples/internvl35_card.py)，保存为 `~/edgeaccel/internvl35_card.py`。前面的固定版本下载约 1.78 GB，包含 Python 推理入口、分词器、图片、视觉模型、语言模型和 NumPy 格式的 Embedding。保留各目录结构，无需重复下载另外两份 `.bin` Embedding。

例程校验官方脚本版本，指定 AXCL 后端，保留官方图像处理、提示词模板、预填充与解码流程。Embedding 使用只读内存映射；每次问答清空 KV 缓存，默认最多生成 96 个 token。

## 运行图像描述与文本问答

沿用下载步骤中的 `MODEL_DIR`，指定一个尚不存在的结果目录：

```bash
python ~/edgeaccel/internvl35_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/internvl35-1b-01
```

程序依次运行小熊猫识别、大熊猫图片描述和 `2加3` 纯文本问答。每张图片按官方单块方式处理为 448 × 448 输入，使用 256 个视觉 token。语言模型加载一次，三个问题彼此独立。

使用自己的图片与问题：

```bash
python ~/edgeaccel/internvl35_card.py \
  --model-dir "$MODEL_DIR" \
  --image ~/edgeaccel/inputs/photo.jpg \
  --question '请用一句中文描述图片中看见的内容。' \
  --output ~/edgeaccel/results/internvl35-1b-custom-01
```

将 `photo.jpg` 替换为实际图片。纯文本问答省略 `--image`；需要先检查单张样例时使用 `--first-only`。提示词最多 1023 个 token，图片 token 也计入其中；超过范围时缩短问题。本版本官方预填充实现要求最后一块非空，输入 token 数恰为 128 的整数倍时，例程会提示调整问题后再运行。

## 查看回答与输入图片

| 文件或字段 | 判断方法 |
| --- | --- |
| `input-1.jpg`、`input-2.jpg` | 与两个图文问题对应的实际输入 |
| `deployment-result.json` 的 `samples` | 每个问题的原文、回答、token、停止原因和耗时 |
| `sessions` | 30 个 AXCL 模型的实际调用、形状组与有限值检查 |
| `completed` | 所有样例均正常结束时为 `true` |

每个回答的 `stopReason` 应为 `eos`，表示模型生成结束标记。`length` 表示达到输出上限，`context` 表示上下文耗尽；这两种情况会保留已有回答并以非零状态退出，不计作完整回答。可在范围内调整 `--max-new-tokens` 后用新的输出目录重试。

下方展示本次输入图片和回答原文。生成耗时包含预处理、主机与卡之间的数据传输、模型推理及示例记录开销，不含模型加载；首 token 时间表示示例内部拿到首个 token 的时间，不是网页首字延迟。模型加载时间在 JSON 中单独记录。

本页先核对少量图文和文本样例；它们不能代替完整数据集精度、长上下文、多图、多轮对话或真实 8GB 卡回归。使用业务图片时继续检查动物类别、颜色、位置和数量等细节。
