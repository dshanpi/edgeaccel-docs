> 配套程序正在更新，请暂缓使用本页运行包。后续将替换为复测通过的版本。

## 准备原生程序

本例使用 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16.0。模型文件约 11.35GB，模型目录所在文件系统建议预留至少 15GB 可用空间。先完成驱动安装，确认 `axcl-smi` 可以识别设备。程序依赖主机上的 OpenCV 4.6；模型的图像编码器、36 个文本层和输出层在算力卡执行，分词、图像处理和词嵌入读取在主机执行。

下载[配套运行包](/examples/qwen3-vl8-standard-20261001.tar.gz)，保存为 `~/edgeaccel/qwen3-vl8-standard-20261001.tar.gz`。包内包含固定源码编译的 ARM64 程序、文件校验工具、两张图片和八帧视频样本。保留前文下载后设置的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3-vl8-standard-20261001.tar.gz
chmod +x qwen3-vl8/bin/main
ldd qwen3-vl8/bin/main
python3 qwen3-vl8/verify_models.py --model-dir "$MODEL_DIR"
python3 qwen3-vl8/prepare.py \
  --model-dir "$MODEL_DIR" \
  --output "$HOME/edgeaccel/qwen3-vl8-run"
```

`ldd` 输出不应出现 `not found`，校验工具应输出 `Verified 52 model files`。准备工具会创建独立运行目录；再次准备时换用一个新目录。

使用默认 384 × 384 视觉编码器，贪心选择 `top_k=1`，关闭嵌入文件内存映射。词嵌入在主机占用约 1187 MiB，运行前确认主机 `MemAvailable` 至少为 2400MiB（执行 `grep MemAvailable /proc/meminfo` 查看，输出单位为 kB）。当前结果仅覆盖 16GB 卡。

## 运行图片问答

```bash
bash ~/edgeaccel/qwen3-vl8-run/run_image.sh
```

本次权重分放在板载与外置存储，通过符号链接组织为一个模型目录；也可将全部文件放在容量充足的同一目录。首次加载耗时受存储读取速度影响，不计入本页单次问答耗时。加载完成后出现 `prompt >>`。依次输入问题和相对于运行目录的图片路径：

```text
prompt >> Name the two animals in the foreground. Reply in one sentence.
image >> images/ssd_horse.jpg
```

等待回答后可继续提问，例如输入 `画面中有几个人清晰可见？只回答人数。`，并再次输入 `images/ssd_horse.jpg`。描述巴士图片时使用 `images/ssd_car.jpg`。在 `prompt >>` 输入 `q` 退出并释放模型。

## 使用自己的图片并检查退出状态

图片模式支持输入主机上图片的绝对路径。先使用配套样图确认部署结果，再替换自己的图片和问题。当前仅确认图片问答流程，视频帧问答尚未通过完整验证。

在提示符输入 `q`，程序退出后检查：

```bash
echo $?
axcl-smi
```

退出码应为 `0`，设备列表中不应继续显示该推理进程。回答中的人数、对象和动作仍需对照输入人工核对；生成流畅不等于所有细节准确。

## 查看固定源码

配套程序由官方 AX-LLM 提交 `3be4cc3fee4a4c730ec7c9b8982ff4b398eefac7` 编译，分词子模块提交为 `0eed4120c6e1b5ea1e51b51c576924faddc8b2a1`。包内 `build-info.json` 记录程序和源码校验值，`official-source.tar.gz` 保存本例固定源码。

## 使用本地分词文件

运行包中的 `qwen3_tokenizer.txt` 由固定版本官方转换工具，从本模型的词表和配置导出。导出时使用本仓库十二个分词相关文件。准备工具会校验导出文件及其源文件，无需另启 HTTP 分词服务。`tokenizer-export.json` 记录源文件与输出校验值；`convert_tokenizer.py` 保存配套转换工具。
