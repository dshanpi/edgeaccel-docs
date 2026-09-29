## 准备英文语音环境

本例使用官方 AX650 权重，在 **RK3576 + AX8850 16GB M.2** 上运行 Inflect Nano。编码器、解码器通过 AXCL 在卡上执行；音素前端、Embedding、时长预测和对齐由主机 CPU 完成。

在已安装 PyAXEngine 的 AXCL Python 环境中安装依赖：

```bash
python -m pip install 'numpy==1.26.4' 'onnxruntime==1.20.1' \
  'soundfile==0.13.1' 'phonemizer==3.3.0' 'num2words==0.5.14' \
  'Unidecode==1.4.0' 'espeakng-loader==0.2.4'
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认提供者包含 `AXCLRTExecutionProvider`，设备 0 可用。本次使用 PyAXEngine `0.1.3.rc3`，通过 `espeakng-loader` 提供英文音素转换所需的 eSpeak NG 库。

下载 [英文语音运行示例](../../../static/examples/inflect_en_card.py)，保存为 `~/edgeaccel/inflect_en_card.py`。前面的固定版本下载包含约 8.0 MB 文件，保留 `models` 和 `python/inflect_tts_sdk` 目录结构。此例不需要 PyTorch，也不启动 API 服务。

## 运行短句合成

沿用下载步骤中的 `MODEL_DIR`，指定尚不存在的输出目录：

```bash
python ~/edgeaccel/inflect_en_card.py \
  --variant nano --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/inflect-nano-01
```

程序固定 `speed=1.0`、`variation=0.667`、`seed=0`，合成问候、天气、双句提示和数字读法四组输入。模型只加载一次，双句之间保留官方 80 ms 静音间隔。例程使用官方音素转换、对齐和采样流程，补充 AXCL 后端选择、模块导入路径及输入长度检查。

合成自己的英文短句：

```bash
python ~/edgeaccel/inflect_en_card.py \
  --variant nano --model-dir "$MODEL_DIR" \
  --text 'Welcome to the voice assistant.' \
  --output ~/edgeaccel/results/inflect-nano-custom-01
```

每句限制为 200 个含空白符的音素 token，最多解码 500 帧。超限时缩短句子；例程报错停止，不静默截断。本模型面向英文，不能用它替代中文语音模型。

## 播放实际语音

| 文件 | 用途 |
| --- | --- |
| `01-english.wav` 至 `04-english.wav` | 四组实际生成的 24 kHz 单声道 PCM16 音频 |
| `*-raw.wav` | 官方限幅之前的浮点输出 |
| `deployment-result.json` | 原文、归一化文本、音素、后端、耗时和输出校验值 |

JSON 的 `completed` 应为 `true`，`sessions` 中两个 AXCL 模型和 `cpuSessions` 中的时长预测模型均应有实际调用。先播放 `Hello world.`，再对照数字 `12` 和双句停顿。下方播放器展示本页实际运行结果。

生成耗时包含音素前端、CPU 处理、AXCL 推理和调用记录开销，不含模型加载及 WAV 写入；RTF 为生成耗时除以音频时长。不能直接将上游 AX650 本机性能作为 M.2 卡性能。有限值、非静音和无 ±1 限幅不等于发音或听感验收通过，长文本、接口服务及真实 8GB 卡仍需单独验证。
