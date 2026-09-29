## 准备算力卡运行环境

本页在 RK3576 主机上通过 AXCL 调用 AX8850 16GB M.2 算力卡，将 S3 语音 token 转为 24 kHz 音频，并运行带参考音频条件的合成。

本仓库提供的是 **语音 token → 频谱 → 音频** 流程。它不直接接收文字；文字生成语音 token 需要另配 T3 模型。下例使用仓库提供的 `sample_input`，不将语音 token 当作文本分词结果。

保留上方下载得到的 `$MODEL_DIR`，在 RK3576 主机执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。模型推理使用算力卡，频谱处理和 WAV 写入使用主机 CPU；板端不需要安装 PyTorch。

## 检查模型和输入文件

| 文件 | 用途 |
| --- | --- |
| `models/model.axmodel` | 基础语音 token → mel 频谱 |
| `models/model_clone.axmodel` | 带参考音频条件的 token → mel 频谱 |
| `models/hifift_f0.axmodel` | HiFT 基频预测 |
| `models/hifift_decode.axmodel` | HiFT 声码器 |
| `sample_input/*.npy` | 官方样例的 token、有效长度、音色向量和初始噪声 |
| `python/hift_linear_w.npy`、`python/hift_linear_b.npy` | 声码器激励参数 |
| `python/hift_vocoder.py` | CPU 频谱处理 |
| `clone_reference.wav` | 仓库提供的参考音频 LJ001-0001 |

保留完整固定版本文件。示例启动时逐文件检查 SHA256，不混用其他提交的权重和参数。

## 运行基础音频合成

下载 [Chatterbox 算力卡示例包](../../../static/examples/chatterbox-card-example.zip)，保存到 `~/edgeaccel/` 后执行：

```bash
mkdir -p ~/edgeaccel/chatterbox-example
unzip ~/edgeaccel/chatterbox-card-example.zip -d ~/edgeaccel/chatterbox-example
python ~/edgeaccel/chatterbox-example/chatterbox_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/chatterbox-base-01
```

输出目录须尚不存在。程序执行官方样例及一次重复运行，结果分别位于 `official-full/output.wav` 和 `official-repeat/output.wav`。

官方输入包含 242 个有效语音 token，生成 484 帧 mel。声码器每次接收 198 帧，因此示例按 **198 + 198 + 88 帧** 分三段处理，拼接有效输出，得到完整的 9.68 秒音频。这里未使用交叠或淡入淡出；分段连接处的听感仍需单独评估。

## 运行参考音频条件合成

示例包的 `reference` 目录包含由仓库 `clone_reference.wav` 实际提取的三个条件文件：

| 文件 | 形状 |
| --- | --- |
| `ref_embedding.npy` | `1 × 192` 音色向量 |
| `ref_prompt_token.npy` | `1 × 157` 参考语音 token |
| `ref_prompt_feat.npy` | `1 × 314 × 80` 参考频谱 |

这些条件由 [ResembleAI/chatterbox 固定版本](https://huggingface.co/ResembleAI/chatterbox/tree/5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18) 的 `s3gen.safetensors` 和官方 Chatterbox 0.1.4 的 `embed_ref` 方法在桌面 CPU 上生成。参考音频转为单声道 24 kHz，取前 6.28 秒；来源、权重与输出校验值记录在 `reference-preparation.json`。

在 RK3576 主机执行：

```bash
python ~/edgeaccel/chatterbox-example/chatterbox_card.py \
  --model-dir "$MODEL_DIR" \
  --reference-dir ~/edgeaccel/chatterbox-example/reference \
  --output ~/edgeaccel/results/chatterbox-clone-01
```

该命令依次执行两次基础合成，再执行两次参考条件合成。本次参考条件样例明确使用官方输入的 **前 99 个 token**，配合 157 个参考 token 填入模型，输出 3.96 秒音频；不是完整 242 token 样例的克隆。每次对四组固定种子的初始噪声分别推理，再平均生成频谱。

更换参考音频时，应使用仓库的 `python/extract_voice_embedding.py` 重新生成全部三个文件。仅替换音色向量不能复现完整参考条件路径；本页只验证示例包中的固定参考。

## 检查并播放结果

`deployment-result.json` 中的 `completed` 应为 `true`，输出目录包含以下音频：

| 目录 | 内容 | 音频长度 |
| --- | --- | --- |
| `official-full` | 完整官方 token 样例 | 9.68 秒 |
| `official-repeat` | 完整样例重复运行 | 9.68 秒 |
| `reference-first99` | 前 99 token，带参考音频条件 | 3.96 秒 |
| `reference-repeat` | 相同参考条件重复运行 | 3.96 秒 |

音频为 24 kHz、单声道、PCM16。可复制到桌面主机播放，或在已配置音频输出的 Linux 主机执行：

```bash
aplay ~/edgeaccel/results/chatterbox-clone-01/reference-first99/output.wav
```

下方展示本次算力卡生成的音频及实际波形。流程耗时包含推理、CPU 频谱处理、原始张量保存和 WAV 写入，不含权重加载或桌面端参考条件提取；AXCL 耗时只累计网络 `run` 调用。

本次核对了模型数据流、频谱还原、音频长度和重复性。发音准确率、音色相似度、分段听感以及实际 8GB 卡容量仍待专项验证。
