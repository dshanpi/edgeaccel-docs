## 准备 Python 环境

先按 [Python 接口](../../usage/python.md) 安装 PyAXEngine，再在连接算力卡的 RK3576 主机执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'librosa==0.11.0' 'soundfile==0.13.1' 'einops==0.8.1' tqdm
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本页以 44.1 kHz 立体声音乐为输入，输出鼓、贝斯、其他伴奏和人声四路音频。

## 准备音乐片段

下载本页的 [实际输入片段](../../../static/validation/effects/mel-band-roformer-20260928/input.wav)，保存到上方下载步骤使用的 `$MODEL_DIR/input.wav`，并校验：

```bash
echo '331a96b35f6140659447e163cf785bf024ed503c752beeef07e643f2f0d9d3b3  '"$MODEL_DIR/input.wav" | sha256sum -c -
```

结果须为 `OK`。样例取自 Karissa Hobbs 的 **Let's Go Fishin'** 第 20～28 秒，经 Vorbis 解码后保存为 PCM24 WAV，未调整音量。原曲采用 [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)；见 [作者作品页](https://freemusicarchive.org/music/Karissa_Hobbs/Age_of_Flowers/09_Lets_Go_Fishin) 和 [Librosa 固定版本来源](https://github.com/librosa/data/blob/38f4b06556fa0ff1acda5e677d8ba05d1bc0fff0/audio/Karissa_Hobbs_-_Lets_Go_Fishin.txt)。下方分轨由本次模型处理生成，属于对原片段的修改。

## 运行四路分离

下载 [MelBandRoformer 算力卡示例](../../../static/examples/mel_roformer_card.py)，保存为 `~/edgeaccel/mel_roformer_card.py`：

```bash
python ~/edgeaccel/mel_roformer_card.py \
  --model-dir "$MODEL_DIR" \
  --audio "$MODEL_DIR/input.wav" \
  --output ~/edgeaccel/results/mel-roformer-01
```

输出目录须尚不存在。程序处理音乐片段、重复同一片段，再处理两秒静音。模型经 AXCL 在 M.2 算力卡运行，音频前后处理由主机完成。

沿用官方参数：每块 2 秒、重叠比例 25%、STFT 点数 2048、帧移 441。八秒输入共运行六块；不足两秒的最后一块补零，输出按实际长度裁切后拼接。

## 查看分离音频

输出目录中的 `music-drums.wav`、`music-bass.wav`、`music-other.wav` 和 `music-vocals.wav` 分别为鼓、贝斯、其他伴奏和人声预测。下方提供与输入对应的四路实际音频，便于对照。

`deployment-result.json` 记录每路的峰值、均方根幅度、保存时的缩放系数和推理调用。保存规则沿用官方入口：除以 `max(1.01 × 峰值, 1)`，再编码为 PCM24。`music-stems.npz` 保留缩放前的浮点结果，`io-*.npz` 和 `chunk-*.npz` 用于复核频谱、掩码和拼接过程。

程序记录的文件处理时间包含前后处理及原始证据压缩写入。重复输入会复用相同输入输出的证据文件，因此首轮与重复耗时不能直接用来比较模型速度。单次 AXCL 调用耗时另列。

四路输出有声音或波形不代表分离质量已达标。本次没有原始独立分轨参考，尚未计算 SDR 等分离指标；人声残留、乐器串音及音乐细节需结合目标素材评估。

## 更换音乐输入

将 `--audio` 改为自己的 WAV 路径。当前示例要求 44.1 kHz、双声道、最长 15 秒，需先裁剪并转换其他格式。更长歌曲的连续处理、不同音乐风格与分离质量仍需进一步验证。
