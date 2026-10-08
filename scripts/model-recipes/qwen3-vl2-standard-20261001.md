> 配套程序正在更新，请暂缓使用本页运行包。后续将替换为复测通过的版本。

## 准备原生程序

本例使用 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16.0。模型放在主机板载存储，准备至少 5GB 可用空间。先完成驱动安装，确认 `axcl-smi` 可以识别设备。程序依赖主机上的 OpenCV 4.6；模型的图像编码器、28 个文本层和输出层在算力卡执行，分词、图像处理和词嵌入读取在主机执行。

下载[配套运行包](/examples/qwen3-vl2-standard-20261001.tar.gz)，保存为 `~/edgeaccel/qwen3-vl2-standard-20261001.tar.gz`。包内包含固定源码编译的 ARM64 程序、文件校验工具、两张图片和八帧视频样本。保留前文下载后设置的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3-vl2-standard-20261001.tar.gz
chmod +x qwen3-vl2/bin/main
ldd qwen3-vl2/bin/main
python3 qwen3-vl2/verify_models.py --model-dir "$MODEL_DIR"
python3 qwen3-vl2/prepare.py \
  --model-dir "$MODEL_DIR" \
  --output "$HOME/edgeaccel/qwen3-vl2-run"
```

`ldd` 输出不应出现 `not found`，校验工具应输出 `Verified 45 model files`。准备工具会创建独立运行目录；再次准备时换用一个新目录。

使用默认 384 × 384 视觉编码器，贪心选择 `top_k=1`，关闭嵌入文件内存映射。词嵌入在主机占用约 594 MiB，运行前为主机预留足够内存。当前结果仅覆盖 16GB 卡。

## 运行图片问答

```bash
bash ~/edgeaccel/qwen3-vl2-run/run_image.sh
```

首次加载完成后出现 `prompt >>`。依次输入问题和相对于运行目录的图片路径：

```text
prompt >> Name the two animals in the foreground. Reply in one sentence.
image >> images/ssd_horse.jpg
```

等待回答后可继续提问，例如输入 `画面中有几个人清晰可见？只回答人数。`，并再次输入 `images/ssd_horse.jpg`。描述巴士图片时使用 `images/ssd_car.jpg`。在 `prompt >>` 输入 `q` 退出并释放模型。

## 运行视频帧问答

退出图片程序后启动视频模式：

```bash
bash ~/edgeaccel/qwen3-vl2-run/run_video.sh
```

```text
prompt >> 请用两句中文描述这些视频帧中动物的动作。
video >> video
```

此处输入目录包含八张按文件名排序的 JPEG 帧。程序按每两帧一组执行视觉编码，共执行四组，再生成回答。本例验证已经抽取的帧序列；未覆盖原始 MP4 的解码和抽帧，也不将这些帧的播放速度作为实测参数。

## 使用自己的图片并检查退出状态

图片模式支持输入主机上图片的绝对路径。先使用配套样图确认部署结果，再替换自己的图片和问题。视频帧模式需要按时间顺序命名图片，本页仅验证八帧输入。

在提示符输入 `q`，程序退出后检查：

```bash
echo $?
axcl-smi
```

退出码应为 `0`，设备列表中不应继续显示该推理进程。回答中的人数、对象和动作仍需对照输入人工核对；生成流畅不等于所有细节准确。

## 查看固定源码

配套程序由官方 AX-LLM 提交 `3be4cc3fee4a4c730ec7c9b8982ff4b398eefac7` 编译，分词子模块提交为 `0eed4120c6e1b5ea1e51b51c576924faddc8b2a1`。包内 `build-info.json` 记录程序和源码校验值，`official-source.tar.gz` 保存本例固定源码。

## 使用本地分词文件

运行包中的 `qwen3_tokenizer.txt` 由固定版本官方转换工具，从本模型的词表和配置导出。准备工具会校验导出文件及其源文件，无需另启 HTTP 分词服务。`tokenizer-export.json` 记录源文件与输出校验值；`convert_tokenizer.py` 保存配套转换工具。
