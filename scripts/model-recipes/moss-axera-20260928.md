## 准备算力卡运行环境

本页在 RK3576 主机上使用 AX8850 16GB M.2 算力卡，将中英文文字合成为 48 kHz 双声道 WAV。预填充、逐帧语音采样和声码器在算力卡上运行；自回归解码使用 RK3576 CPU 上的 ONNX Runtime，这是该版本推荐的组合。

保留上方下载得到的 `$MODEL_DIR`，在 RK3576 主机执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'sentencepiece==0.2.1' 'onnxruntime==1.20.1'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。保持算力卡散热风扇开启，完成上方固定版本下载；本示例不需要 PyTorch。

## 检查模型文件

| 文件 | 执行位置 |
| --- | --- |
| `models/axmodels_650/tts_prefill.axmodel` | 算力卡：处理文本与内置音色条件 |
| `models/axmodels_650/tts_local_fixed_sampled_frame.axmodel` | 算力卡：生成一帧的 16 个语音 token |
| `models/axmodels_650/codec_decode.axmodel` | 算力卡：将语音 token 转为音频 |
| `models/onnxmodels/moss_tts_decode_step.onnx` | 主机 CPU：逐帧更新隐藏状态 |
| `models/onnxmodels/moss_tts_decode_step.data` | ONNX 外部权重，须与 `.onnx` 文件同目录 |
| `config/`、`scripts/` | 分词器、内置音色、参数和运行代码 |

示例按实际模型接口处理 512 行预填充和 320 行 CPU 解码缓存，并逐文件检查 SHA256。请保持权重、配置和示例版本一致。

仓库另有 `tts_decode_step.axmodel`。上游将全 NPU 解码列为诊断路径，本页的部署效果使用推荐的 CPU 解码组合。仓库中的 AX650 SoC 可执行程序不适用于本页 M.2 算力卡流程。

## 运行中英文合成

下载 [MOSS-TTS-Nano.AXERA 算力卡示例包](../../../static/examples/moss-axera-card-example.zip)，保存到 `~/edgeaccel/` 后执行：

```bash
mkdir -p ~/edgeaccel/moss-axera-example
unzip ~/edgeaccel/moss-axera-card-example.zip -d ~/edgeaccel/moss-axera-example
python ~/edgeaccel/moss-axera-example/moss_axera_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/moss-axera-01
```

输出目录须尚不存在。程序依次合成中文、英文和一次中文重复样例，默认随机种子为 42，每句最多生成 110 帧。

## 使用自己的文字

```bash
python ~/edgeaccel/moss-axera-example/moss_axera_card.py \
  --model-dir "$MODEL_DIR" \
  --text '你好，欢迎使用算力卡。' \
  --voice Junhao \
  --max-frames 110 \
  --output ~/edgeaccel/results/moss-axera-custom-01
```

中文示例使用 `Junhao`，英文示例使用 `Ava`。可用音色见 `config/browser_poc_manifest.json` 的 `builtin_voices`；其他音色尚未逐一验证。

缓存容量限制为“实际提示行数 + `--max-frames` ≤ 320”。文字和内置音色条件都会占用提示行数。超出时缩短文字、改用较短音色条件，或降低帧数；降低帧数可能使语音提前截断。每帧对应 0.08 秒，单句最多 128 帧。`result.json` 中的 `stopReason` 为 `model-end` 表示模型自行结束；`frame-limit` 表示达到设置上限，需检查是否读完。

当前示例使用仓库内置音色，不提供自定义参考 WAV 克隆：该发布包没有配套的 `codec_encode` 权重。

## 检查并播放结果

`deployment-result.json` 中的 `completed` 应为 `true`。默认样例输出如下：

| 文件 | 输入 | 本次音频长度 |
| --- | --- | --- |
| `zh/output.wav` | 你好，欢迎使用算力卡。 | 2.72 秒 |
| `en/output.wav` | Hello, welcome to the edge AI demo. | 2.48 秒 |
| `zh-repeat/output.wav` | 相同中文与随机种子 | 2.72 秒 |

音频为 48 kHz、双声道、PCM16。复制到桌面主机播放，或在配置了音频输出的 Linux 主机执行：

```bash
aplay ~/edgeaccel/results/moss-axera-01/zh/output.wav
```

自定义文字的音频位于 `custom/output.wav`。每个样例还保存 `result.json`、`tokens.npy`、`waveform.npy` 和原始输入输出，便于核对实际结果。

下方展示本次实测音频和波形。中文两次运行的模型输入、输出和 WAV 完全一致；英文的独立 ASR 转写与输入词语相符，中文转写存在偏差，发音和音色质量仍需试听核对。耗时包含原始张量保存，不能作为关闭记录后的性能基准。本次为 16GB 卡实测，实际 8GB 卡另行回归。
