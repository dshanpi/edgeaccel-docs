## 准备 Python 环境

本例在 RK3576 主机通过 AXCL 运行 SmolVLM-256M 的图像编码器、30 层解码器及输出层。先按 [Python 接口](../../usage/python.md) 创建 `~/edgeaccel/python-env`，再激活并安装依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'transformers==4.51.3' 'ml_dtypes==0.5.3'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。模型下载目录应包含 `smolvlm-256m-ax650/`、`smolvlm_tokenizer/`、`smolvlm_tokenizer_512.py` 和 `ssd_car.jpg`。这里使用 AX650 权重，经 M.2 卡运行；不执行用于裸片开发板的 `main`。

## 运行图片问答

下载 [SmolVLM-256M 算力卡示例](../../../static/examples/smolvlm256_card.py)，保存为 `~/edgeaccel/smolvlm256_card.py`。保持前面下载步骤中的 `MODEL_DIR`，执行：

```bash
python ~/edgeaccel/smolvlm256_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/smolvlm256-01
```

输出目录须尚不存在。程序使用官方公交车图片进行描述、颜色问答和重复描述，最后执行一道纯文本问题。生成采用贪心选择，默认最多 160 个新 token，每次请求重新初始化 KV 缓存。

图像按官方 C++ 示例缩放为 512×512 RGB，由图像编码器生成 64 个视觉 token。分词与提示格式沿用本页固定版本的官方脚本；BF16 词嵌入通过只读内存映射加载，不需要下载原始浮点大模型。

## 查看输出与结束原因

打开输出目录中的 `deployment-result.json`：

- `samples[].output`：模型原始回答。
- `samples[].stopReason`：`eos` 表示正常结束，`length` 表示达到输出上限，`context` 表示达到上下文限制。
- `samples[].firstTokenSeconds` 和 `generationSeconds`：请求开始至首 token、请求完成的实测耗时，包含分词、图片处理及推理，不含模型加载。
- `sessions`：32 份 AXMODEL 的实际调用次数、输入规格和耗时。

`input-*.jpg` 为实际输入图片，`vision-*.npz` 保留输入像素和视觉特征。模型能生成回答不等于每条回答均正确，应结合输入图片核对内容。达到长度限制的结果可能未完整回答问题。

## 换成自己的图片

```bash
python ~/edgeaccel/smolvlm256_card.py \
  --model-dir "$MODEL_DIR" \
  --image ~/Pictures/example.jpg \
  --question 'Describe this image in one sentence.' \
  --max-new-tokens 160 \
  --output ~/edgeaccel/results/smolvlm256-custom-01
```

当前入口每次接受一张图片；包含视觉 token 的完整输入不得超过 128 token。问题过长时程序停止，缩短问题后使用新的输出目录重试。纯文本问答可省略 `--image`。
