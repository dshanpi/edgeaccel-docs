## 安装模型运行依赖

本页在 RK3576 主机上通过 AXCL 调用 AX8850 16GB M.2 算力卡，将六路相机图像转换为三维检测框和鸟瞰图（BEV）。模型使用前一帧的 BEV 特征，因此同一场景应按帧顺序运行，切换场景时清空历史状态。

保留上方下载得到的 `$MODEL_DIR`，在 RK3576 主机执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。推理使用算力卡；图像处理、三维框解码和绘制使用主机 CPU。

## 检查模型与六路输入

| 文件 | 用途 |
| --- | --- |
| `ax650/compiled.axmodel` | 算力卡推理模型 |
| `inference_config.json` | 类别、BEV 大小和检测范围 |
| `inference_data/scene_index.json` | 官方场景和帧顺序 |
| `inference_data/<场景>/cam_00_*.png` 至 `cam_05_*.png` | 每帧六路图像 |
| `inference_data/<场景>/meta_*.json` | 相机投影矩阵、图像归一化参数和车辆状态 |
| `bevformer_tiny_fixed.onnx` | 官方浮点参考模型；不参与下面的算力卡推理 |

下载清单选取两个官方场景的前三帧：`fcbccedd…` 的 0、1、2 帧，以及 `325cef68…` 的 40、41、42 帧，共 36 张图像。原始索引包含 81 帧；示例明确只运行已下载的六帧，不修改索引。

每次推理输入包括 `1×6×3×480×800` 图像、六个投影矩阵、18 维车辆状态和 `2500×1×256` 历史 BEV。自备数据时必须同时提供这些条件，不能只替换某一路图片。

## 运行三维检测

下载 [BEVFormer 算力卡示例包](../../../static/examples/bevformer-card-example.zip)，保存到 `~/edgeaccel/` 后执行：

```bash
mkdir -p ~/edgeaccel/bevformer-example
unzip ~/edgeaccel/bevformer-card-example.zip -d ~/edgeaccel/bevformer-example
python ~/edgeaccel/bevformer-example/bevformer_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/bevformer-01 \
  --repeat
```

输出目录须尚不存在。程序先核对下载文件 SHA256，再运行两个场景各三帧，最后清空历史状态并重复第一个场景的三帧。

只检查第一帧时，使用另一个输出目录并将 `--repeat` 改为 `--first-only`。默认不加这两个参数时，运行两个场景的六帧。

## 查看六路画面与鸟瞰图

`deployment-result.json` 中的 `completed` 应为 `true`，输出目录包含：

| 文件 | 内容 |
| --- | --- |
| `main-fcbccedd-000000.jpg` 至 `000002.jpg` | 第一个场景的连续三帧 |
| `main-325cef68-000040.jpg` 至 `000042.jpg` | 第二个场景的连续三帧 |
| `repeat-fcbccedd-000000.jpg` 至 `000002.jpg` | 重复运行第一个场景 |
| 同名 `.json` | 检测类别、分数、三维框、投影线段和耗时 |
| 同名 `.npz` | 实际模型输入与原始输出 |

将 JPG 复制到桌面主机查看。左侧为六路相机画面，上排依次为 CAM 2、0、1，下排为 CAM 4、3、5；右侧为鸟瞰图，前方朝上、左侧朝左，黑色箭头表示车辆朝向。

示例使用固定分数阈值 **大于 0.30** 和按类别设置半径的圆形 NMS。绿色为汽车，红色为行人；完整类别和颜色定义见示例中的 `COLORS` 与配置 `class_names`。三维框按原始 LiDAR 坐标定义绘制，保留模型输出的尺寸和方向；跨越相机近裁剪面的框先裁剪再投影。

本次六帧分别检出 **22、34、25、18、29、32** 个目标。重复三帧的模型输入输出、检测框及投影结果与首次运行一致。图片上的框不代表每个目标均已通过标注核验。

## 对照部署效果

下方图片和短片均来自本次算力卡输出。短片每个包含三帧，按 3 FPS 播放，播放速度不等于实时处理速度。

本次算力卡单次调用约 191–212 ms；包括图像读取、后处理、原始张量保存和图片写入的流程约 4.50–5.35 秒/帧。两种耗时范围不同。

使用仓库 FP32 ONNX 在桌面 CPU 上进行了同输入对照和独立时序对照。检测数量及部分框与量化模型存在差异，当前仅确认基本部署、数据流和重复性；尚未完成 nuScenes 全量精度、长序列稳定性或实际 8GB 卡回归。
