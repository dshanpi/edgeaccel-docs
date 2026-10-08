## 选择其他 AX650 权重

前面的下载命令包含本页实测的十个AX650权重。默认入口使用n规格NPU3；需要切换规模时，选择下表中的文件。`ax615/`、`ax630C/`、`ax637/`目录面向其他芯片，不用于本页AX8850算力卡。

| 权重（位于ax650目录） | 本组实测容量 |
| --- | --- |
| `yolo26l-pose_npu1.axmodel` | 16GB |
| `yolo26l-pose_npu3.axmodel` | 16GB |
| `yolo26m-pose_npu1.axmodel` | 16GB |
| `yolo26m-pose_npu3.axmodel` | 16GB |
| `yolo26n-pose_npu1.axmodel` | 16GB |
| `yolo26s-pose_npu1.axmodel` | 16GB |
| `yolo26s-pose_npu3.axmodel` | 16GB |
| `yolo26x-pose_npu1.axmodel` | 16GB |
| `yolo26x-pose_npu3.axmodel` | 16GB |

在同一模型目录执行，修改`WEIGHT`选择一个文件：

```bash
cd "$MODEL_DIR"
WEIGHT=ax650/yolo26l-pose_npu1.axmodel
OUT=~/edgeaccel/results/yolo26-pose
mkdir -p "$OUT"
python ax_infer.py --model-path "$WEIGHT" --test-img bus.jpg \
  --providers AXCLRTExecutionProvider \
  --img-save-path "$OUT/$(basename "$WEIGHT" .axmodel).jpg"
```

打开`OUT`目录中的输出图，与下方同规模、同NPU配置的实测结果对照。NPU1与NPU3是编译配置；不表示需要连接一张或三张算力卡。保持默认置信度阈值0.25和NMS阈值0.7，以便复现下方样例。
