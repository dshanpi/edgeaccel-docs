## 准备 Python 环境

本例在 RK3576 主机运行官方 Python 图像问答流程。视觉嵌入与分词在主机 CPU 上执行；视觉编码器、32 层解码器和输出层通过 AXCL 在算力卡上执行。

先按 [Python 接口](../../usage/python.md) 创建 `~/edgeaccel/python-env`，再激活并安装依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchvision==0.20.1' 'transformers==4.51.3' 'Pillow==11.3.0' 'ml_dtypes==0.5.3' tqdm
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。模型目录应包含 `smolvlm2_axmodel/`、`smolvlm2_tokenizer/`、`vit_model/`、`embeds/`、`utils/` 和 `assets/bee.jpg`。

## 运行官方图片问答

下载 [SmolVLM2-500M 算力卡示例](../../../static/examples/smolvlm500_card.py)，保存为 `~/edgeaccel/smolvlm500_card.py`。保持前面下载步骤中的 `MODEL_DIR`，执行：

```bash
python ~/edgeaccel/smolvlm500_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/smolvlm500-01
```

输出目录须尚不存在。程序对官方花朵与蜜蜂图片执行描述、花瓣颜色问答和重复描述；每次请求清空 KV 缓存。使用只读 NPY 词嵌入，并按文件 SHA256 核对官方源码和 CPU 视觉嵌入文件。

CPU 视觉嵌入保留 `weights_only=True`，仅允许固定文件实际需要的 Torch 类。不要把其他来源的同名文件替换到该路径，也不要关闭限制来绕过校验。

图片先按官方入口调整为 512×512，再交由配套 processor 处理。若视觉编码器只接受 batch=1，程序逐块运行全部图像块，并按原顺序合并；不丢弃额外图像块。

## 查看模型回答

输出目录中的 `deployment-result.json` 保存输入 token、原始回答、CPU 与 AXCL 调用记录及耗时。查看：

- `samples[].output`：实际回答。
- `samples[].stopReason`：`eos` 为正常结束，`length` 为达到输出上限，`context` 为达到上下文限制。
- `samples[].pixelValuesShape` 与 `imageTokenCount`：本次 processor 的分块和视觉 token 数。
- `cpuEmbedding.calls` 与 `sessions`：CPU 视觉嵌入及每份 AXMODEL 的实际执行情况。

`generationSeconds` 包含主机预处理、传输和推理，不含模型加载；它不是纯 NPU 耗时。默认上限为 160 个新 token，达到上限的回答可能未完成。

## 使用自己的图片

```bash
python ~/edgeaccel/smolvlm500_card.py \
  --model-dir "$MODEL_DIR" \
  --image ~/Pictures/example.jpg \
  --question 'Describe this image in one sentence.' \
  --output ~/edgeaccel/results/smolvlm500-custom-01
```

当前入口对应官方单图 Python 示例。视频、多图及更长输入需分别验证，不应直接用单图结果代替。
