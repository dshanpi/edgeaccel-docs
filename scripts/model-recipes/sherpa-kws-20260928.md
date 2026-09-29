## 安装 Python 依赖

本页使用官方 Python 单路径关键词检测流程，在 RK3576 + AX8850 16GB M.2 算力卡上对比 `chunk 8`、`chunk 16` 两种配置。每种配置均运行编码器、解码器和连接器三个模型，主机负责音频特征提取及关键词匹配。

完成 [Python 接口](../../usage/python.md) 配置后，在 RK3576 主机执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'kaldi-native-fbank==1.22.3' 'pypinyin==0.55.0'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本页使用 `models/650` 中的模型，经 AXCL 运行；仓库中的原生 AX650 二进制使用不同运行接口，不要直接作为 M.2 算力卡程序启动。

## 运行两种分块配置

完成上方固定版本下载后，保留 `$MODEL_DIR`。下载 [关键词检测算力卡示例](../../../static/examples/sherpa_kws_card.py)，保存为 `~/edgeaccel/sherpa_kws_card.py`，串行执行：

```bash
python ~/edgeaccel/sherpa_kws_card.py \
  --model-dir "$MODEL_DIR" --chunk-size 8 \
  --output ~/edgeaccel/results/sherpa-kws-chunk8-01

python ~/edgeaccel/sherpa_kws_card.py \
  --model-dir "$MODEL_DIR" --chunk-size 16 \
  --output ~/edgeaccel/results/sherpa-kws-chunk16-01
```

输出目录须尚不存在。每次运行处理仓库中的 9 段语音、重复 `zh_0.wav`，再处理两秒静音。输入均为 16 kHz、单声道、PCM16 WAV；按官方流程补入 0.8 秒静音以推进解码。

运行结束时退出码为 0，结果目录中的 `deployment-result.json` 应包含 `completed: true`。该字段表示整套样例执行完成，检测是否符合预期仍须查看每段的 `detections`、`detection_match` 和下方结果表。

## 查看关键词检测结果

`samples[].result.detections` 保存检测到的关键词。空数组 `[]` 表示没有触发。本次两种配置都能触发英文 `LIGHT_UP`、`LOVELY_CHILD` 及部分中文关键词，但 `zh_0`、`zh_1`、`zh_2` 均未触发。

`reference_detections` 来自仓库固定版本的历史推理记录，`detection_match` 表示本次输出是否与其相同。这份参考不是人工标注的完整测试集，不能据此计算实际业务召回率。

本次 chunk 8 的 9 段语音与参考记录一致；chunk 16 有两段不同：`en_0` 新触发 `LIGHT_UP`，`zh_5` 只触发“落实”，没有触发参考记录中的“周望军”。下方同时展示本次与参考结果，差异保留为后续质量核对项。

重复 `zh_0.wav` 的每次模型输入输出校验值一致，两秒静音没有触发。仅此短静音样例不能证明长期无误唤醒。完整文件处理时间包含特征提取、关键词解码及原始证据压缩写入；单次 AXCL 调用时间另列。

## 配置中文关键词

关键词由 `$MODEL_DIR/config/keywords.txt` 定义，模型权重无需重新导出。先备份，再追加新词：

```bash
cd "$MODEL_DIR"
cp -n config/keywords.txt config/keywords.txt.original
python scripts/generate_keyword_tokens.py --text '打开台灯' --threshold 0.25 --append
```

工具检查拼音 token 是否存在于词表中；遇到 `tokens not present` 时，先更换或核对关键词。成功时新增行包含拼音、阈值和 `@打开台灯` 标签。已存在的完全相同行不会重复追加。

修改关键词后，用对应录音重新验证命中和误触发。示例的 `jobs` 列表可指定输入录音；如修改为自定义样例，同时调整固定 9 个文件的数量检查，并为每次运行选择新输出目录。原仓库参考结果不适用于新录音或新关键词，应以自己的标注为准。

当前 Python 示例采用单路径解码，`max_active_paths = 1`。官方 C++ 的多路径搜索是另一套流程，本页没有验证其 16 路或 32 路搜索效果；不要将两者的参数或性能直接互换。

## 判断是否适合业务

先用目标关键词、相似发音、远场与噪声录音检查漏检，再用持续背景录音统计单位时间误触发次数。阈值调整后须同时检查两项。本次展示用于复现固定输入的部署效果，尚未完成完整唤醒率、误唤醒率、长时间运行或真实 8GB 卡容量验收。
