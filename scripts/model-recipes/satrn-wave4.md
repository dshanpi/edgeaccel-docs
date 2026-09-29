## 安装例程依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程指定 `AXCLRTExecutionProvider`，使用本页固定版本的权重和样例，并保存本次输出。

## 识别单张文字裁剪图

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task satrn --variant word \
  --output results/word
```

输入为 `demo_text_recog.jpg`。例程将文字图缩放到 100×32，先运行 backbone/encoder，再逐字符运行 decoder，遇到结束标记停止，最多生成 25 个字符。

查看 `results/word/deployment-result.json` 中的 `text`，并与 `input.png` 核对。本页只运行文字识别；整张文档还需要文字检测、裁剪和阅读顺序处理。

字典和前处理依据：[MMOCR v1.0.1 SATRN 配置](https://github.com/open-mmlab/mmocr/blob/v1.0.1/configs/textrecog/satrn/_base_satrn_shallow.py)、[90 字符字典](https://github.com/open-mmlab/mmocr/blob/v1.0.1/dicts/english_digits_symbols.txt)。该字典不包含中文。
