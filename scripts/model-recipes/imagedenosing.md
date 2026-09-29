## 安装图像处理依赖

本页先运行已取得输出的 DnCNN、FFDNet 与 NAFNet。Restormer 尚未取得有效输出，FastDVDnet 视频推理尚未实测，不包含在以下运行命令中。

在 RK3576 主机激活已安装 PyAXEngine 的环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install \
  'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
python -m pip check
```

下载 [enhancement_card.py](../../../static/examples/enhancement_card.py) 和 [image-denoising-cases.json](../../../static/examples/image-denoising-cases.json)，保存到 `$MODEL_DIR`。脚本复用官方前后处理，指定 `AXCLRTExecutionProvider`，并配置模型、输入和输出路径。

## 运行三种图像降噪算法

在模型目录执行。使用新的结果目录，避免混入旧输出。

```bash
cd "$MODEL_DIR"
for name in dncnn ffdnet nafnet; do
  python enhancement_card.py --model-dir . \
    --cases image-denoising-cases.json --case "$name" \
    --output "results/$name" || break
done
```

DnCNN 与 FFDNet 分别向官方图片添加 sigma=25、sigma=10 的高斯噪声，再运行降噪；NumPy 随机种子固定为 `20260923`。NAFNet 直接使用仓库提供的 `noisy.png`。

确认日志使用 `AXCLRTExecutionProvider`、退出码为 0，并生成以下文件：

| 算法 | 输出文件 | 图片排列 |
| --- | --- | --- |
| DnCNN | `results/dncnn/outputs/axmodel_res.png` | 原图、加噪图、降噪图 |
| FFDNet | `results/ffdnet/outputs/axmodel_res.png` | 原图、加噪图、降噪图 |
| NAFNet | `results/nafnet/outputs/axmodel_compare.png` | 含噪输入、降噪图 |

每个结果目录还包含 `enhancement-result.json`，用于核对实际权重、输入校验值、输出尺寸和耗时。判断效果时同时查看噪点、文字或边缘是否丢失，不能只检查图片是否生成。
