## 准备配套程序

本例使用约 4GB RAM 的 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16。下载前为模型预留至少 4GB 存储空间；词嵌入读取约占 594 MiB 主机内存。程序依赖 OpenCV 4.6，当前结果仅覆盖 16GB 卡。

下载[配套运行包](/examples/qwen3-vl2-standard-fixed-20261002.tar.gz)，保存到 `~/edgeaccel/`。保留前文设置的 `MODEL_DIR`，在连接算力卡的 Linux 主机执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3-vl2-standard-fixed-20261002.tar.gz
chmod +x qwen3-vl2-standard-fixed/main_axcl_aarch64
ldd qwen3-vl2-standard-fixed/main_axcl_aarch64
python3 qwen3-vl2-standard-fixed/verify_models.py "$MODEL_DIR"
```

`ldd` 输出不应出现 `not found`，校验程序应输出 `Verified 72 model files`。文件校验失败时，重新下载对应固定版本文件后再运行。

运行包使用本模型导出的本地分词文件，无需启动 HTTP 分词服务。图像编码器、28 个文本层和输出层在算力卡执行；分词、图像预处理和词嵌入读取在主机完成。配套入口固定使用设备 0、384 × 384 视觉输入和 `top_k=1` 贪心解码。

## 运行图片问答

在同一终端执行：

```bash
python3 ~/edgeaccel/qwen3-vl2-standard-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/images/ssd_horse.jpg" \
  --prompt 'Name the two animals in the foreground. Reply in one sentence.'
```

等待加载和推理完成，终端会输出回答并退出。程序应报告 `termination_reason=eos last_token=151645`。再使用巴士图片测试中文描述：

```bash
python3 ~/edgeaccel/qwen3-vl2-standard-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/images/ssd_car.jpg" \
  --prompt '请用一句中文描述图片中的主要内容。'
```

替换 `--input` 为自己的单张图片路径、`--prompt` 为问题即可测试新输入。每次命令启动独立进程，完成后释放模型。

## 运行视频帧问答

本例输入是仓库内已经抽取的八张 JPEG 帧。按文件名顺序、1 fps 解释帧序列，每两帧组成一个视觉组，共四组。这里的 1 fps 是输入配置，不代表原始视频的实际帧率。

```bash
python3 ~/edgeaccel/qwen3-vl2-standard-fixed/run_model.py video \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/video" \
  --prompt '请用两句中文描述这些视频帧中动物的动作。'
```

配套入口仅接受包含八张 JPEG 的目录。本例未覆盖 MP4 解码、实时视频、多轮问答或任意长度视频。新增场景需单独检查抽帧顺序、输入长度和结果。

## 检查运行结果

```bash
echo $?
axcl-smi
```

退出码应为 `0`，日志应包含真实 EOS 结束记录，设备列表不应继续显示该推理进程。`context-limit` 表示到达上下文上限，不能作为正常回答结束。对照输入核对对象、人数和动作，原始回答及本次核对结果见下方效果展示。

本轮进程耗时包含网络模型读取、加载和推理，不代表模型存放在本地存储时的性能。实际 8GB 卡、更多输入和连续运行仍需独立验证。

## 查看配套源码

运行包包含固定源码、修改差异、编译信息、词表导出记录和文件校验值。程序基于 AXERA 的 AX-LLM 提交 `3be4cc3fee4a4c730ec7c9b8982ff4b398eefac7`，使用本页复测配套版本；请保持程序、分词文件和模型版本一致。
