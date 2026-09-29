## 安装例程依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程指定 `AXCLRTExecutionProvider`，使用本页固定版本的权重和样例，并保存本次输出。

## 提取图片特征

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task dinov3 --variant vits16 \
  --output results/features
```

例程依次输入官方的 `ILSVRC2012_val_00000001.jpeg`、`ILSVRC2012_val_00000005.jpeg`，再重复第一张图片，使用官方 `preprocess_image` 函数。每张图片的 `pooler_output` 保存为 384 维 `.npy` 向量。

查看 `results/features/deployment-result.json` 中的向量维度、范数和余弦相似度。该模型输出图片特征，不生成分类名称；相似度不能解释为分类准确率。
