## 安装依赖与运行包

本例使用 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16.0，模型保存在板载存储。先确认 `axcl-smi` 能识别设备，模型目录所在存储建议预留至少 5GB 空间。运行前退出其他模型程序。

在已安装 PyAXEngine 的 Python 环境中安装配套依赖：

```bash
python -m pip install numpy==1.26.4 Pillow==11.3.0 ml-dtypes==0.5.3 tokenizers==0.22.2
python -c "import axengine; print(axengine.get_available_providers())"
```

提供器列表中应包含 `AXCLRTExecutionProvider`。下载[配套运行包](/examples/locateanything3b-20261001.tar.gz)，保存到 `~/edgeaccel`。保留前文设置的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf locateanything3b-20261001.tar.gz
python locateanything3b/verify_models.py --model-dir "$MODEL_DIR"
mkdir -p locateanything-results
```

校验通过后应输出 `Verified 48 model files`。运行入口调用固定版本的官方 Python 程序，并指定算力卡提供器。图像编码器、36 个文本层和输出层由算力卡执行；图像缩放、分词、坐标转换和结果绘制由主机完成。

## 检测图片中的人物

```bash
python locateanything3b/run.py --model-dir "$MODEL_DIR" \
  --image "$MODEL_DIR/test_data/person.jpg" \
  --task object_detection --target person \
  --temperature 0 --repetition-penalty 1 --max-new-tokens 256 \
  --output locateanything-results/people.png \
  --save-response locateanything-results/people.json
```

程序将检测框绘制到 `people.png`，原始 token、坐标及运行参数保存在 `people.json`。打开图片，对照每个检测框与原图中的人物；检测框数量不等同于标注真值。

## 定位图片中的文字

定位路牌上的 `AMETHYST`：

```bash
python locateanything3b/run.py --model-dir "$MODEL_DIR" \
  --image "$MODEL_DIR/test_data/ocr.jpg" \
  --task text_grounding --target AMETHYST \
  --temperature 0 --repetition-penalty 1 --max-new-tokens 256 \
  --output locateanything-results/sign.png \
  --save-response locateanything-results/sign.json
```

将输入图片换为 `test_data/book.jpg`、目标换为 `GEORGE`，可定位书封面上的对应文字。此任务按输入文字定位区域，不代表完整 OCR 转录。

## 用一句话指定目标位置

```bash
python locateanything3b/run.py --model-dir "$MODEL_DIR" \
  --image "$MODEL_DIR/test_data/sushi.jpg" \
  --task pointing \
  --target 'the green wasabi paste in the small white dish' \
  --temperature 0 --repetition-penalty 1 --max-new-tokens 256 \
  --output locateanything-results/wasabi.png \
  --save-response locateanything-results/wasabi.json
```

打开 `wasabi.png`，检查定位点是否位于小白碟中的绿色芥末上。替换为自己的图片时，使用图片绝对路径，并在 `--target` 中描述需要定位的对象。

## 检查输出与释放状态

程序结束后检查退出码和设备状态：

```bash
echo $?
axcl-smi
```

退出码应为 `0`。同时检查输出图片和 JSON 是否生成、原始回答是否完整结束、坐标是否符合输入目标。输出文件存在仅表明完成了结果保存，定位是否正确仍需对照图片判断。
