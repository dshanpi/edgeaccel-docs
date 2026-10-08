## 准备配套程序

本例使用 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16。模型目录至少预留 8GB 可用空间。程序依赖 OpenCV 4.6，词嵌入读取约占 742 MiB 主机内存；文件校验脚本需要 Python 3.11 或更高版本。

下载[配套运行包](/examples/qwen3-vl4-fixed-20261003.tar.gz)，复制到连接算力卡的 Linux 主机并命名为 `~/edgeaccel/qwen3-vl4-fixed-20261003.tar.gz`。保留前文设置的 `MODEL_DIR`，在该 Linux 主机执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3-vl4-fixed-20261003.tar.gz
chmod +x qwen3-vl4-fixed/main_axcl_aarch64
ldd qwen3-vl4-fixed/main_axcl_aarch64
python3 qwen3-vl4-fixed/verify_models.py "$MODEL_DIR"
```

`ldd` 不应出现 `not found`，校验应输出 `Verified 48 model files`。校验失败时先重新下载对应固定文件。程序使用本模型仓库的原生词表，无需启动分词服务。

视觉编码器、36 个文本层和输出层在算力卡运行；分词、图片预处理和词嵌入读取在主机执行。配套程序固定使用设备 0、贪心解码和独立进程，输入上限为 1152 token。

## 运行图片问答

先使用运行包内的骑乘场景图片：

```bash
python3 ~/edgeaccel/qwen3-vl4-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input ~/edgeaccel/qwen3-vl4-fixed/companion/images/ssd_horse.jpg \
  --prompt 'Name the two animals in the foreground. Reply in one sentence.'
```

`companion` 内的图片和八帧视频来自固定版本的官方 2B 仓库，用于对照同一输入的效果；推理使用本页下载的 4B 权重。再使用 4B 仓库自带的室内图片统计人数：

```bash
python3 ~/edgeaccel/qwen3-vl4-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/01.jpg" \
  --prompt '画面中有几个人清晰可见？只回答人数。'
```

将问题改为 `请用一句中文描述图片中的主要内容。` 可查看室内描述。街景样例位于 `~/edgeaccel/qwen3-vl4-fixed/companion/images/ssd_car.jpg`。每条命令等待回答完成后再运行下一条。

## 运行视频帧问答

先使用 4B 仓库自带的三张 JPEG 帧：

```bash
python3 ~/edgeaccel/qwen3-vl4-fixed/run_model.py video \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/video" \
  --prompt '请用两句中文描述这些视频帧中动物的动作。'
```

程序按文件名顺序、1 fps 解释输入。编码器每两帧组成一组，三帧输入会重复末帧以完成最后一组；重复帧沿用原末帧时间，不表示额外观察了一帧。

再测试运行包内的八帧配套样例：

```bash
python3 ~/edgeaccel/qwen3-vl4-fixed/run_model.py video \
  --model-dir "$MODEL_DIR" \
  --input ~/edgeaccel/qwen3-vl4-fixed/companion/video \
  --prompt 'Describe what the two animals are doing in these video frames. Use two sentences.'
```

当前入口接受三帧或八帧 JPEG 目录，目录内不应混入其他文件。1 fps 是本页的输入配置，未核实原视频时基；本页未覆盖 MP4 解码、实时视频或多轮问答。

## 检查运行结果

日志应出现 `termination_reason=eos last_token=151645`，随后输出完整回答并退出。每条命令完成后执行：

```bash
echo $?
axcl-smi
```

退出码应为 `0`，设备列表不应继续显示该推理进程。`context-limit` 表示输出触及上限，不能当作完整回答结束。对照原图检查人数、文字和场景，对照视频帧检查可见动作；实际回答及偏差见下方效果展示。

本轮进程耗时包含网络读取模型、加载和推理，不代表本地存储性能。结果来自 16GB 卡；实际 8GB 卡、更多输入和连续运行需独立验证。

## 查看配套源码

运行包包含固定源码、原生词表来源、配套图片来源、编译信息和文件校验值。程序基于 AXERA 的 AX-LLM 提交 `3be4cc3fee4a4c730ec7c9b8982ff4b398eefac7`，使用本页提供的配套版本。请保持程序、词表和模型版本一致。
