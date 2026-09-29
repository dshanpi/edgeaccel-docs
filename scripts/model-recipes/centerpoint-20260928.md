## 安装点云处理依赖

本页通过 RK3576 主机调用 AX8850 16GB M.2 算力卡，对官方 50 帧点云运行 CenterPoint 检测并保存鸟瞰图。

**当前权重仅完成基本运行核对，车辆检测效果尚未通过。** 第 49 帧在固定阈值下，算力卡未检出目标，桌面 CPU 浮点参考检出 34 个。接入业务前先查看下方对照结果。

在 RK3576 主机执行，沿用前文的 `$MODEL_DIR`：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'numba==0.67.0' 'llvmlite==0.49.0' 'tqdm==4.70.1' 'opencv-python-headless==4.11.0.86'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出应包含 `AXCLRTExecutionProvider`。点云分组、后处理和绘图使用主机 CPU；神经网络使用算力卡。首次执行会编译 Numba 函数，首帧耗时明显较长。

## 检查点云与运行配置

| 文件 | 用途 |
| --- | --- |
| `ax650/centerpoint.axmodel` | 算力卡推理模型 |
| `extracted_data/config.json` | 点云范围、体素尺寸与类别配置 |
| `extracted_data/sample_index.json` | 50 帧输入顺序 |
| `extracted_data/points/*.bin` | 每点五个 float32：x、y、z、强度、时间差 |
| `inference_axmodel.py` | 固定版本的点云预处理和 NMS 函数 |
| `pointpillars.onnx` | 桌面 CPU 对照使用的浮点模型；不参与下面的算力卡推理 |

运行配置使用 `extracted_data/config.json`；仓库根目录的 `config.json` 是模型转换配置，不能替代运行配置。

本页输入为单帧扫描，时间差均为 0。体素尺寸为 `0.2×0.2×8.0` 米，每柱最多 20 个点，模型接收最多 30000 个柱。输入张量为 `1×10×30000×20` float32 特征与 `1×30000×2` int32 索引。

自备点云必须使用相同坐标、单位和特征定义。不能把原始传感器的线束编号直接放入时间差通道。本页示例固定读取官方样例，接入新数据时需同步修改样例索引和输入校验。

## 运行点云检测

下载 [CenterPoint 算力卡示例包](/examples/centerpoint-card-example.zip)，保存为 `~/edgeaccel/centerpoint-card-example.zip`，然后执行：

```bash
mkdir -p ~/edgeaccel/centerpoint-example
unzip ~/edgeaccel/centerpoint-card-example.zip -d ~/edgeaccel/centerpoint-example
python ~/edgeaccel/centerpoint-example/centerpoint_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/centerpoint-01 \
  --limit 50 \
  --repeat
```

输出目录须尚不存在。程序先核对固定文件的 SHA256，再按索引运行 50 帧，最后重复前三帧。只试跑一帧时，将 `--limit 50 --repeat` 改为 `--limit 1`，并使用新的输出目录。

示例使用仓库的轴对齐、跨类别 NMS，IoU 阈值为 `0.2`，候选阈值为 `0.1`，最终保留分数 **大于 `0.5`** 的框。尺寸按训练及导出定义中的宽、长、高读取。该简化后处理不等同于标准 nuScenes 评估流程。

## 查看检测画面

正常结束后，`deployment-result.json` 中 `completed` 为 `true`，目录中包含：

| 文件 | 内容 |
| --- | --- |
| `main-000.jpg` 至 `main-049.jpg` | 50 帧点云及实际检测框 |
| `repeat-000.jpg` 至 `repeat-002.jpg` | 前三帧的重复运行结果 |
| 同名 `.json` | 类别、分数、框、点数及分阶段耗时 |
| 同名 `.npz` | 两路实际输入与 42 路原始输出 |
| `deployment-result.json` | 本次完整结果 |

将 JPG 复制到桌面主机查看。每张图左侧为输入点云，右侧为算力卡检测；x 轴朝右、y 轴朝上，范围为正负 51.2 米。矩形保留模型的原始尺寸，短线表示方向，类别颜色见图片底部。

本次 50 帧共保留 474 个检测框，**这是逐帧框数之和，不是 474 个独立目标**。前三帧分别为 8、9、17 个，重复运行结果一致。第二个场景的十帧中，只有第 41 帧保留 1 个框，其余为 0；没有通过降低阈值替换展示结果。

下面两段短片由实际输出图片按 **2 FPS** 编码，分别包含 40 帧和 10 帧。播放速度不代表推理帧率。

## 判断结果适用范围

本次算力卡调用约 `208–221 ms/帧`。含读取、后处理、张量压缩保存和绘图的后续帧流程约 `1.36–1.74 秒/帧`，首帧约 `21.93 秒`，包含首次 JIT 编译。实际应用关闭记录后的吞吐量需要另测。

浮点对照使用相同输入和阈值，在桌面 CPU 上运行；它不是算力卡效果。第 49 帧的浮点参考包含 32 个汽车框、2 个卡车框，算力卡为 0，当前版本不宜直接用于车辆检测业务。

仓库的 `gt_annotations` 是空占位文件，无法据此计算 mAP、NDS 或漏检率。本次未完成带标注精度、长期稳定性和实际 8GB 卡回归。
