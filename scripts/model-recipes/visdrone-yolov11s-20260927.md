## 准备算力卡例程

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境，安装图像处理依赖：

```bash
sudo apt install libopencv-dev
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86'
cd "$MODEL_DIR"
ldd cpp/lib/libdet.so
```

依赖检查不能出现 `not found`。下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程先加载系统 OpenCV C++ 库，再加载官方 ARM64 `libdet.so`，以 `AxDeviceType.axcl_device` 显式选择 AXCL 设备 0。Python 的 `opencv-python` 包不能替代这里的系统 C++ 库。

## 检测航拍图片

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task visdrone --variant official \
  --output results/official
```

例程按 `model_meta.json` 使用 11 个输出类别，阈值为 0.25。按固定版本前处理将图像直接缩放到 640×640，保留 BGR 通道顺序，由检测库执行 1/255 归一化。

三张图片各运行三次，保存缩放后的输入、`-output.png` 检测图和 `deployment-result.json`。输出目录必须尚不存在；再次运行时换一个目录名。

检查检测框、类别和分数，再对照原图评估漏检与误检。官方 SDK 单次结果结构最多容纳 64 个候选目标，密集航拍场景需要单独评估这项限制。记录的耗时包含检测库内部前后处理，不是纯 NPU 时间。
