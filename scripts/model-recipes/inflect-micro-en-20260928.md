## 准备英文语音环境

本例使用官方 `models/ax650` 权重，在 **RK3576 + AX8850 16GB M.2** 上运行 Inflect Micro。编码器和解码器通过 AXCL 在卡上执行；音素前端、Embedding、时长预测和对齐在主机 CPU 上完成。

在已安装 PyAXEngine 的 AXCL Python 环境中安装依赖：

```bash
python -m pip install 'numpy==1.26.4' 'onnxruntime==1.20.1' \
  'soundfile==0.13.1' 'phonemizer==3.3.0' 'num2words==0.5.14' \
  'Unidecode==1.4.0' 'espeakng-loader==0.2.4'
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

提供者列表应包含 `AXCLRTExecutionProvider`，设备 0 可用。本次使用 PyAXEngine `0.1.3.rc3`。没有系统 eSpeak NG 动态库时，官方前端使用 `espeakng-loader` 提供的库；本次采用这一方式。

下载 [英文语音运行示例](../../../static/examples/inflect_en_card.py)，保存为 `~/edgeaccel/inflect_en_card.py`。前面的固定版本下载包含约 16.2 MB 文件，需保留 `models/ax650` 和 `python/inflect_tts_sdk` 目录结构。本页不使用 AX620E 或 AX637 权重。

## 运行短句合成

沿用下载步骤中的 `MODEL_DIR`，指定尚不存在的输出目录：

```bash
python ~/edgeaccel/inflect_en_card.py \
  --variant micro --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/inflect-micro-01
```

例程固定 `speed=1.0`、`variation=0.667`、`seed=0`，依次合成问候、天气、双句提示和数字读法四组输入。模型只加载一次；双句使用官方 80 ms 静音间隔拼接。模型、音素转换、对齐和采样算法保持官方实现，适配层明确指定 AXCL 后端并记录实际调用。

合成自己的英文短句：

```bash
python ~/edgeaccel/inflect_en_card.py \
  --variant micro --model-dir "$MODEL_DIR" \
  --text 'Welcome to the voice assistant.' \
  --output ~/edgeaccel/results/inflect-micro-custom-01
```

每句最多 200 个含空白符的音素 token，解码最多 500 帧。超限时缩短句子；不能把截断输出作为完整语音。此模型面向英文，中文使用单独的 Inflect 中文部署页。

## 播放实际语音

| 文件 | 用途 |
| --- | --- |
| `01-english.wav` 至 `04-english.wav` | 四组实际生成的 24 kHz 单声道 PCM16 音频 |
| `*-raw.wav` | 官方限幅之前的浮点输出 |
| `deployment-result.json` | 原文、归一化文本、音素、模型后端、耗时和输出校验值 |

JSON 的 `completed` 应为 `true`，`sessions` 中两个 AXCL 模型和 `cpuSessions` 中的时长预测模型均应有实际调用。下方播放器展示对应 WAV；可先对照 `Hello world.`，再检查 `12` 是否读作 `twelve`、双句停顿是否自然。

生成耗时包含音素前端、CPU 处理、AXCL 推理和调用记录开销，不包含模型加载及 WAV 写入。RTF 是生成耗时除以音频时长，不等于纯 NPU 延迟。有限值、非静音和无 ±1 限幅只说明基本输出状态；发音、音色、长文本和真实 8GB 卡仍需单独验收。
