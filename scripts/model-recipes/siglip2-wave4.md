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

```bash
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4' 'sentencepiece==0.2.1' 'protobuf==4.25.8'
```

## 对比图片与两条描述

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task siglip2 --variant base224 \
  --output results/cats
```

输入为仓库自带的 `000000039769.jpg`，描述为 `a photo of 2 cats` 和 `a photo of 2 dogs`。例程从本地 `tokenizer/` 加载配套前处理文件，使用 `tokenizer.json` 对应的 fast tokenizer，将文本补齐或截断为编译模型要求的 64 token，不额外下载分词模型。

查看 `results/cats/deployment-result.json` 中的余弦相似度与 `sigmoidScore`。SigLIP 使用独立 sigmoid 匹配分数，两条描述的分数不要求相加等于 1，也不能当作已标定的识别准确率。
