## 运行 bird-m 和 bird-l

前面的下载命令已包含下表权重和七张样图。沿用已配置的 Python 环境及 `MODEL_DIR`。本节权重在16GB卡实测。

| 模型 | 权重 | 输入尺寸 |
| --- | --- | --- |
| bird-m | `model/bird-m/AX650/bird_650_npu3.axmodel` | 224×224 |
| bird-l | `model/bird-l/AX650/bird_650_npu3.axmodel` | 384×384 |

在主机选择一种规格运行，尺寸必须与权重对应：

```bash
VARIANT=m
case "$VARIANT" in
  m) SIZE=224 ;;
  l) SIZE=384 ;;
  *) echo "请选择m或l" >&2; exit 1 ;;
esac
OUT=~/edgeaccel/results/bird-$VARIANT
mkdir -p "$OUT"
cd "$OUT"
set -o pipefail
python "$MODEL_DIR/axmodel_infer.py" \
  --model_file "$MODEL_DIR/model/bird-$VARIANT/AX650/bird_650_npu3.axmodel" \
  --class_map_file "$MODEL_DIR/class_name.txt" --image_size "$SIZE" \
  --image "$MODEL_DIR/test_images/04251_3a52191e-be71-4539-98ea-14a8f2347330.jpg" \
  2>&1 | tee run.log
```

打开当前目录新生成的 `prediction_result_top5.png`，核对Top-5类别和分数。替换 `--image` 可逐张测试其余样图；结果图会覆盖，需另存。

## 运行鸟类检测与识别

配置 Python 后端时已将两个入口切换至 AXCL。检测模型以480×480输入定位鸟类，识别模型对外扩30%的裁剪图进行224×224分类。

```bash
OUT=~/edgeaccel/results/bird-end2end
mkdir -p "$OUT"
cd "$MODEL_DIR"
set -o pipefail
python axmodel_infer_end2end.py \
  --det_model model/bird-end2end/AX650/bird_det_650_npu1.axmodel \
  --rec_model model/bird-end2end/AX650/bird_rec_650_npu1.axmodel \
  --class_map_file class_name.txt --image_dir test_images \
  --output_dir "$OUT" 2>&1 | tee "$OUT/run.log"
```

检测框图保存到 `OUT`，实际识别裁剪图保存到 `OUT/crops`，每只鸟的Top-5写入 `OUT/results.json`。检查七张输入均被处理、框的位置合理，并核对JSON中的类别。上游脚本可能捕获异常后仍返回0，必须同时检查日志和新生成的文件。
