## 编译 AXCL 人脸检测程序

按照[编译 AXCL 视觉示例](../../usage/build-samples.md)准备源码与依赖，使用提交 `cbfa4c76891758983ca2b0c99c11d6621d59af39`。也可只构建本页目标：

```bash
cd ~/edgeaccel/src/axcl-samples
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target axcl_yolov7_face --parallel 2
export FACE_SAMPLE="$PWD/build/examples/axcl/axcl_yolov7_face"
ldd "$FACE_SAMPLE"
```

依赖列表不应出现 `not found`。本页实测使用主机 OpenCV 4.6.0 编译；仓库旧预编译程序依赖 OpenCV 4.5，不能通过随意修改库文件名替代。

## 检测样例中的人脸

```bash
cd "$MODEL_DIR"
test -x "$FACE_SAMPLE"
mkdir -p results/selfie
cd results/selfie
"$FACE_SAMPLE" -m "$MODEL_DIR/ax650/yolov7-face.axmodel" \
  -i "$MODEL_DIR/selfie.jpg" -r 3
```

打开本次生成的 `yolov7_face_out.jpg`，检查人脸框位置。固定示例的置信度阈值为 0.2，NMS 阈值为 0.5，计时前预热 5 次，再统计 3 次推理。该模型用于检测人脸区域，不判断人物身份；候选框数量不等于准确人数。
