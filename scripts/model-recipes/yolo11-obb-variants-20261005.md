## 选择其他 AX650 权重

前面的下载命令包含本页实测的十个AX650权重。默认入口使用n规格NPU3；需要切换规模时，选择下表中的文件。`637/`目录面向AX637，不用于本页AX8850算力卡。

| 权重（位于650目录） | 本组实测容量 |
| --- | --- |
| `yolo11l-obb_640x640_npu1.axmodel` | 16GB |
| `yolo11l-obb_640x640_npu3.axmodel` | 16GB |
| `yolo11m-obb_640x640_npu1.axmodel` | 16GB |
| `yolo11m-obb_640x640_npu3.axmodel` | 16GB |
| `yolo11n-obb_640x640_npu1.axmodel` | 16GB |
| `yolo11s-obb_640x640_npu1.axmodel` | 16GB |
| `yolo11s-obb_640x640_npu3.axmodel` | 16GB |
| `yolo11x-obb_640x640_npu1.axmodel` | 16GB |
| `yolo11x-obb_640x640_npu3.axmodel` | 16GB |

在同一模型目录执行，修改`WEIGHT`选择一个文件：

```bash
cd "$MODEL_DIR"
WEIGHT=650/yolo11l-obb_640x640_npu1.axmodel
OUT=~/edgeaccel/results/yolo11-obb
mkdir -p "$OUT"
python ax_infer.py --model "$WEIGHT" --img boats.jpg \
  --providers AXCLRTExecutionProvider \
  --output "$OUT/$(basename "$WEIGHT" .axmodel).jpg"
```

打开`OUT`目录中的输出图，与下方同规模、同NPU配置的实测结果对照。NPU1与NPU3是编译配置；不表示需要连接一张或三张算力卡。保持默认置信度阈值0.25和NMS阈值0.45，以便复现下方样例。
