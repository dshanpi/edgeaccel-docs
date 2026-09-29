## 编译算力卡例程

本例在 RK3576 主机通过 **AXCL C 接口**运行模型，保留官方 C 音频前后处理。Tiny V5、Conv SE 使用上下文掩码，GTCRN 使用七组输入和循环缓存。

安装编译工具，并准备 Python 音频检查环境：

```bash
sudo apt-get update
sudo apt-get install -y git cmake gcc libssl-dev python3-venv
python3 -m venv ~/edgeaccel/lightweight-env
source ~/edgeaccel/lightweight-env/bin/activate
python -m pip install 'numpy==1.26.4'
mkdir -p ~/edgeaccel/src
GIT_LFS_SKIP_SMUDGE=1 git clone \
  https://github.com/AXERA-TECH/Lightweight-Speech-Denoising.axera.git \
  ~/edgeaccel/src/lightweight
git -C ~/edgeaccel/src/lightweight checkout ede9b239cf6b347dbc26a3ce70b574937f4c5771
```

下载 [AXCL 适配脚本](../../../static/examples/lightweight_axcl_patch.py) 和 [音频处理示例](../../../static/examples/lightweight_card.py)，分别保存为 `~/edgeaccel/lightweight_axcl_patch.py`、`~/edgeaccel/lightweight_card.py`。在干净的固定版本源码上执行一次适配：

```bash
python ~/edgeaccel/lightweight_axcl_patch.py ~/edgeaccel/src/lightweight
cmake -S ~/edgeaccel/src/lightweight/c_infer \
  -B ~/edgeaccel/src/lightweight/build-axcl -DCMAKE_BUILD_TYPE=Release
cmake --build ~/edgeaccel/src/lightweight/build-axcl -j2
```

生成的程序为 `build-axcl/test_se_denoise_axcl`。适配将模型加载、内存传输和推理替换为 AXCL，检查浮点数值并记录调用耗时；官方 DSP、上下文拼接和缓存更新保持原样。保留源码文件中的版权与许可说明。

## 运行三份模型

保持下载步骤中的 `MODEL_DIR`，使用尚不存在的结果目录运行：

```bash
python ~/edgeaccel/lightweight_card.py \
  --model-dir "$MODEL_DIR" \
  --binary ~/edgeaccel/src/lightweight/build-axcl/test_se_denoise_axcl \
  --output ~/edgeaccel/results/lightweight-01
```

例程依次处理官方音频、两秒静音和三组块边界长度，每组重建模型和处理状态后运行两遍。`deployment-result.json` 中 `completed: true` 表示运行完成；各组 `repeatExact` 核对全部模型输入、输出、缓存的联合哈希及最终音频是否重复一致，不代表音质评分通过。

| 模型 | 一次处理 | 上下文长度 | 边界输入样本数 |
| --- | --- | --- | --- |
| Tiny V5 | 6 帧，共 1536 点 | 28 帧 | 4607 / 4608 / 4609 |
| Conv SE | 6 帧，共 1536 点 | 58 帧 | 4607 / 4608 / 4609 |
| GTCRN | 1 帧，共 256 点 | 循环缓存 | 767 / 768 / 769 |

输入为 **16 kHz、单声道、PCM16 WAV**。官方程序只处理完整块，写出前去掉最前面的 256 个输出点；本例保留这一行为。因此输出比输入短，没有补齐末尾。本次官方输入为 156302 点，Tiny V5、Conv SE 输出 154880 点，GTCRN 输出 155904 点。

## 处理自己的音频

可直接调用原生程序，最后两个参数选择配置和对应权重。例如使用 Tiny V5：

```bash
mkdir -p ~/edgeaccel/results
~/edgeaccel/src/lightweight/build-axcl/test_se_denoise_axcl \
  /绝对路径/录音.wav ~/edgeaccel/results/denoised.wav \
  "$MODEL_DIR/models/tiny_v5_ax650_config.ini" \
  "$MODEL_DIR/axmodels/ax650_tiny_v5_setrain.axmodel"
```

使用 Conv SE 时，替换为 `conv_se_ax650_config.ini` 与 `ax650_conv_se_setrain.axmodel`；使用 GTCRN 时，替换为 `gtcrn_7input_ax650_config.ini` 与 `ax650_gtcrn_setrain.axmodel`。本适配按这三组配置检查尺寸；Tiny V5、Conv SE 输入至少 3072 点，GTCRN 至少 512 点。

## 查看输出与试听

结果文件以模型和输入命名，例如 `tiny_v5-official-output.wav`：

| 文件 | 内容 |
| --- | --- |
| `*-input.wav` / `*-output.wav` | 实际输入与本次输出，可直接试听 |
| `*-raw.npz` | 保存前的浮点输入、输出 |
| `deployment-result.json` | 输入输出长度、逐次耗时及重复一致性 |

本次 Tiny V5、Conv SE 的静音浮点输出全零。GTCRN 有峰值约 `3.07e-6` 的微小浮点输出，保存为 PCM16 后为零；页面同时展示浮点波形，避免量化掩盖差别。

下方耗时覆盖完整处理循环，包括主机 DSP、传输、AXCL、数值检查和哈希记录；不含模型加载、文件读写及第二遍复测。RTF 是处理耗时与输入时长之比，不能替代麦克风端到端延迟和持续运行测试。

还比较了官方源码附带的 AX650 输出音频，输入文件哈希一致，结果接近。附带音频未提供可核对的权重哈希，因此该比较不等同于独立 ONNX/PyTorch 精度评测；噪声抑制、人声保真和真实麦克风效果仍需按应用场景评估。
