## 准备 Python 环境

以下命令在连接算力卡的 RK3576 主机执行，沿用前文的 `MODEL_DIR`。本页选用的文件约 2.79GB，放在主机内部存储，并另外预留运行与输出空间。

在已安装 PyAXEngine 的 Python 环境中安装依赖：

```bash
python -m pip install 'torch==2.5.1' 'torchvision==0.20.1' \
  'transformers==4.51.3' 'tokenizers==0.21.4' 'jinja2==3.1.6' \
  'numpy==1.26.4' 'ml_dtypes==0.5.3' 'tqdm' 'pillow'
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认提供者列表包含 `AXCLRTExecutionProvider`，且算力卡没有其他推理任务。本次使用 PyAXEngine `0.1.3`。Torch 用于主机端数据处理；28 个主模型和 post 模型通过 AXCL 在算力卡上执行。

## 运行文本问答

下载 [Python 算力卡示例包](../../../static/examples/qwen15b-python-card-example.zip)，解压到 `~/edgeaccel/`，得到 `~/edgeaccel/qwen15b-python-example/`。示例沿用官方 `infer.py` 的分词、prefill、decode 和 `top_k=1` 采样，接受命令行输入，指定 AXCL 后端，并保存完整 token 解码结果。

在同一 Python 环境中执行，输出目录使用一个尚不存在的路径：

```bash
EXAMPLE_DIR=~/edgeaccel/qwen15b-python-example
python "$EXAMPLE_DIR/qwen_python_card.py" \
  --model-dir "$MODEL_DIR" \
  --candidate "$EXAMPLE_DIR/infer_axcl.py" \
  --manifest "$EXAMPLE_DIR/download-manifest.json" \
  --output ~/edgeaccel/results/qwen15b-python-01
```

默认依次运行算术、中文用途说明和 JSON 输出三条独立输入，每条重新加载模型。运行结束后查看结果：

```bash
python -m json.tool ~/edgeaccel/results/qwen15b-python-01/result.json
axcl-smi
```

`completed` 为 `true`、各条 `exitCode` 为 `0` 且 `eosReached` 为 `true`，表示这些输入已完成生成。`output` 保留完整回答，`processSeconds` 包含模型加载、一次问答和进程退出，不是首 token 延迟。

指定自己的问题时增加 `--question`，并更换输出目录：

```bash
python "$EXAMPLE_DIR/qwen_python_card.py" \
  --model-dir "$MODEL_DIR" \
  --candidate "$EXAMPLE_DIR/infer_axcl.py" \
  --manifest "$EXAMPLE_DIR/download-manifest.json" \
  --question '请用一句中文说明 PCIe 的用途。' \
  --output ~/edgeaccel/results/qwen15b-python-02
```

本例为单轮问答。上游示例包含固定角色和日期背景，不应把其中的日期或天气当作实时信息。连续对话、接近上下文上限的长输入和实际 8GB 容量需要分别核对。
