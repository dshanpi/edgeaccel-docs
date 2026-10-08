## 运行 NPU1 完整链路

前面的下载命令同时包含本节三个权重。在已配置 AXCL 后端的 Python 环境中执行，保留对应版本的字典、字体及前后处理。本节组合在16GB卡上实测。

| 权重 | 阶段 |
| --- | --- |
| `ax650/cls_npu1.axmodel` | 方向分类 |
| `ax650/det_npu1.axmodel` | 文本检测 |
| `ax650/rec_npu1.axmodel` | 文字识别 |

```bash
cd "$MODEL_DIR"
INPUT="$MODEL_DIR/11.jpg"
OUT=~/edgeaccel/results/ppocr-v5-npu1/original
mkdir -p "$OUT"
set -o pipefail
python infer_axmodel.py \
  --img_path "$INPUT" --det_model_dir ax650/det_npu1.axmodel \
  --rec_model_dir ax650/rec_npu1.axmodel --cls_model_dir ax650/cls_npu1.axmodel \
  --character_dict_path ppocrv5_dict.txt 2>&1 | tee "$OUT/run.log"
cp res_ax.jpg "$OUT/result.jpg"
```

识别文本逐行写入 `run.log`，结果图为 `OUT/result.jpg`。检查三个模型均加载成功、没有设备错误，并逐行比对图片中的文字。标题正确不代表金额、编号和细字全部正确。

### 检查倒置图片

在同一终端生成180°旋转输入，并设置独立输出目录：

```bash
OUT=~/edgeaccel/results/ppocr-v5-npu1/rotated180
mkdir -p "$OUT"
python - "$MODEL_DIR/11.jpg" "$OUT/input.png" <<'PY'
import cv2, sys
image = cv2.imread(sys.argv[1])
assert image is not None
assert cv2.imwrite(sys.argv[2], cv2.rotate(image, cv2.ROTATE_180))
PY
INPUT="$OUT/input.png"
python infer_axmodel.py \
  --img_path "$INPUT" --det_model_dir ax650/det_npu1.axmodel \
  --rec_model_dir ax650/rec_npu1.axmodel --cls_model_dir ax650/cls_npu1.axmodel \
  --character_dict_path ppocrv5_dict.txt 2>&1 | tee "$OUT/run.log"
cp res_ax.jpg "$OUT/result.jpg"
```

查看倒置输入对应的新结果图及识别文字。方向分类纠正的是文本裁剪，输出可视化仍保留倒置原图；两种输入的检测框或文字不一定完全相同。
