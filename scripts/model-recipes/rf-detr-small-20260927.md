## 准备推理例程

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境，再安装本例依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0' 'onnxruntime==1.20.1'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程显式选择 `AXCLRTExecutionProvider`，使用本页固定提交中的前后处理代码，并将本次结果写入独立目录。

## 执行图片检测

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task rf-detr-b2 --variant small \
  --output results/small
```

输出目录需要尚不存在；再次运行时换一个目录名。每张图片运行三次，保存原始输入、检测图以及 `deployment-result.json` 中的候选框和调用耗时。

输入为仓库内三张 COCO 样例，图像转为 RGB 并直接缩放到 512×512，使用 U8 NHWC 输入。归一化由编译模型完成。骨干网络和分类输出在算力卡上运行，配套 `b2_post.onnx` 边界框后处理在 RK3576 CPU 上运行；两部分耗时单独记录。阈值为 0.5，结果图以 `-output.png` 结尾。

打开结果图片，核对检测框是否落在目标上；再查看记录中的 `completed`、`repeatedDetectionsEqual` 和分数。重复结果一致仅说明本组输入可复现，不能代替漏检、误检和定位精度评估。
