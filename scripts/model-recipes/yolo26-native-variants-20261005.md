## 运行其他 AX650 权重

前面的下载命令同时包含下表权重。默认入口保留原8GB样例；以下权重在16GB卡上实测。

| 权重 | 本组实测容量 |
| --- | --- |
| `ax650/yolo26l.axmodel` | 16GB |
| `ax650/yolo26m.axmodel` | 16GB |
| `ax650/yolo26s.axmodel` | 16GB |
| `ax650/yolo26x.axmodel` | 16GB |

已按[编译视觉示例](../../usage/build-samples.md)取得固定版本源码后，可单独构建本页程序：

```bash
SRC=~/edgeaccel/src/axcl-samples
git -C "$SRC" rev-parse HEAD
# 确认提交为 cbfa4c76891758983ca2b0c99c11d6621d59af39
cmake -S "$SRC" -B "$SRC/build-variants" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="$SRC/build-variants/bin"
cmake --build "$SRC/build-variants" --target axcl_yolo26 --parallel 1
SAMPLE="$SRC/build-variants/bin/axcl_yolo26"
ldd "$SAMPLE"
```

在同一终端选择上表中的一个权重运行。程序将结果写入当前目录，用不同目录保存每个权重的图片：

```bash
WEIGHT=ax650/yolo26l.axmodel
OUT=~/edgeaccel/results/yolo26/$(basename "$WEIGHT" .axmodel)
mkdir -p "$OUT"
cd "$OUT"
set -o pipefail
"$SAMPLE" -m "$MODEL_DIR/$WEIGHT" \
  -i "$MODEL_DIR/bus.jpg" -g 640,640 -r 10 2>&1 | tee run.log
```

打开新生成的`yolo26_out.jpg`，与下面同一权重的结果对照。原始程序使用置信度阈值0.45、NMS阈值0.45，`-r 10`之外还执行5次预热。运行结束后同时核对日志、图片和设备状态，不能只看退出码。
