## 准备官方 AXCL 检测环境

本例在 RK3576 + AX8850 16GB M.2 上使用官方 YOLO-World-V2 SDK，根据四条英文类别词检测图片中的目标。使用 `install/lib/axcl_aarch64/libyoloworld.so`，配合 AX650 编译权重。

在 Linux 主机执行：

```bash
python -m pip install 'numpy==1.26.4' 'Pillow==11.3.0'
axcl-smi
```

确认设备 0 可用。保留前面下载步骤的 `MODEL_DIR`，检查库依赖：

```bash
ldd "$MODEL_DIR/install/lib/axcl_aarch64/libyoloworld.so"
```

依赖列表不得出现 `not found`。本例直接使用系统 ARM64 Python 环境；若其他环境中的 `libstdc++` 不兼容，先切换至配套系统环境再运行。

## 运行两张图片与两组词表

下载 [YOLO-World 算力卡示例](../../../static/examples/yoloworld_card.py)，保存为 `~/edgeaccel/yoloworld_card.py`，使用尚不存在的输出目录：

```bash
python ~/edgeaccel/yoloworld_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/yoloworld-01
```

例程校验官方动态库与 Python 接口，把 ARM64 AXCL 库复制到 SDK 的 `pyyoloworld/aarch64` 加载目录，显式选择 `axcl_device`、设备 0。

程序对 `host.jpg`、`football.jpg` 分别运行以下词表，每种组合重复检测两次：

| 词表 | 类别词 |
| --- | --- |
| 第一组 | `person`, `dog`, `car`, `horse` |
| 第二组 | `man`, `shoes`, `ball`, `person` |

词表是发送给模型的查询文本。返回标签用于观察本次模型响应，不应视作人物身份或属性的认定。

## 查看输出文件

| 文件 | 查看内容 |
| --- | --- |
| `deployment-result.json` | `completed: true`、四组检测框、类别、分数及重复结果 |
| `host-input.png` / `football-input.png` | 实际输入 |
| `*-set1-result.png` | 第一组词表结果 |
| `*-set2-result.png` | 第二组词表结果 |

控制台应出现 `AXCLWorker start with devid 0`，结束时释放模型与设备。`sessions` 不包含逐权重的底层调用跟踪，本例记录的是官方 SDK 完整流程和 `yw_set_classes`、`yw_detect` 的主机侧耗时。

## 接入自己的类别与图片

在示例代码中修改 `sets` 内的四条英文类别词，以及 `for file in ['host.jpg','football.jpg']` 中的文件名，将图片放入模型目录。每组保持四个类别词，每个词的 UTF-8 编码长度小于 64 字节，重新运行时使用新的输出目录。

SDK 接收连续内存的 RGB、`uint8` 图像。更换类别后先调用 `set_classes`，再调用 `detect`；无需每张图片重新创建模型。类别词之间含义接近时，检测类别与保留框可能变化，需要结合业务图片核对。

## 对照部署效果

下方展示两图两组词表的全部结果，包括零检测结果。阈值固定为 0.1，保留低分框；检测框数不是实际物体数量。

检测耗时包含 SDK 内部前处理、数据传输、推理和后处理，不含图片读取、模型加载、绘图和保存。词表更新时间单独记录，不计入检测均值。当前结果用于检查基本运行，未进行完整精度或视频吞吐测试。
