## 安装中文合成依赖

本例在 RK3576 上执行文本前处理与 ONNX 编码，在 M.2 卡上执行 AX650 解码模型。中文权重、`g-zh_mix_en.bin` 和配套 Python 文件必须来自同一提交。

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install numpy==1.26.4 onnxruntime==1.20.1 \
  soundfile==0.14.0 torch==2.5.1 transformers==4.46.3 \
  cn2an==0.5.22 pypinyin==0.50.0 jieba==0.42.1 \
  g2p_en==2.1.0 inflect==7.3.1 num2words==0.5.12
```

本页只部署中文合成，不需要安装用于日语、韩语等其他语言的全部依赖。

## 下载分词资源并指定 AXCL 后端

中文入口同时导入中英混合文本处理模块，需要以下两套分词资源。保持指定目录名，避免运行时再次联网下载。

```bash
~/edgeaccel/hf-env/bin/hf download google-bert/bert-base-uncased \
  config.json tokenizer.json tokenizer_config.json vocab.txt \
  --revision 86b5e0934494bd15c9632b12f734a8a67f723594 \
  --local-dir "$MODEL_DIR/python/bert-base-uncased"
~/edgeaccel/hf-env/bin/hf download google-bert/bert-base-multilingual-uncased \
  config.json tokenizer.json tokenizer_config.json vocab.txt \
  --revision 7cbf9a625e29989f6b9c6c2fa68234c304f7e38f \
  --local-dir "$MODEL_DIR/python/bert-base-multilingual-uncased"
export NLTK_DATA="$MODEL_DIR/nltk_data"
```

在模型目录生成 `melotts_axcl.py`，保留原始入口。修改仅指定卡端解码后端并取消脚本内置的镜像地址；分词资源使用上一步下载的本地目录。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
source = Path("python/melotts.py").read_text(encoding="utf-8")
old = "sess_dec = axe.InferenceSession(dec_model)"
new = 'sess_dec = axe.InferenceSession(dec_model, providers=["AXCLRTExecutionProvider"])'
assert old in source, "源码与本页固定版本不匹配"
source = source.replace(old, new)
source = source.replace('os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"', '')
Path("python/melotts_axcl.py").write_text(source, encoding="utf-8")
PY
```

## 将中文文本合成为 WAV

必须从 `python` 目录运行，编码器、解码器和说话人特征通过其上一级路径读取。

```bash
cd "$MODEL_DIR/python"
export NLTK_DATA="$MODEL_DIR/nltk_data"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
mkdir -p ../outputs
set -o pipefail
python melotts_axcl.py \
  --sentence "你好，欢迎使用算力卡。" \
  --language ZH --speed 0.8 \
  --wav ../outputs/sample-1.wav 2>&1 | tee ../run.log
```

日志中应出现 `AXCLRTExecutionProvider`，末尾打印 `Save to`，并产生本次运行的 `outputs/sample-1.wav`。默认输出为 44.1 kHz、单声道；`ZH` 在该版本内部映射到 `ZH_MIX_EN`。

继续生成另外两段样例：

```bash
python melotts_axcl.py --sentence "模型已经加载完成，可以开始推理。" \
  --language ZH --speed 0.8 --wav ../outputs/sample-2.wav
python melotts_axcl.py --sentence "请检查电源连接，然后启动程序。" \
  --language ZH --speed 0.8 --wav ../outputs/sample-3.wav
```

将 WAV 下载到电脑播放，检查文字完整性、发音、停顿和尾部是否截断。更换文本时保留单句测试；本页未验证长文本、其他语言或音色克隆。
