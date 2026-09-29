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
python -m pip install 'ftfy==6.3.1' 'regex==2025.9.18'
```

## 对比图片与候选文本

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task mobileclip --variant s2 \
  --output results/s2
```

本页运行 MobileCLIP2-S2 的 AX650 配套图像、文本编码器。输入为 `zebra.jpg`，候选文本为 `a zebra`、`a dog`、`two zebras`。图像使用官方 v1 前处理；文本长度为 77，本模型一次接收 3 条候选文本。

查看 `results/s2/deployment-result.json` 的余弦相似度与 `probabilityWithinCandidates`。后者是在本组三条候选文本中计算的 softmax 相对分数，改变候选文本后会变化。仓库内 S4、S0 与其他微调版本不包含在本页实测结论中。
