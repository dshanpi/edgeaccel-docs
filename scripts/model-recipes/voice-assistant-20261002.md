## 获取适配运行包

下载 [离线语音助手运行包](../../../static/examples/voice-assistant-20261002.tar.gz)，保存为 `voice-assistant-20261002.tar.gz`，复制到开发板的 `~/edgeaccel/apps` 目录。包内包含程序、匹配运行库、固定模型清单和两条输入音频。

在开发板执行：

```bash
cd ~/edgeaccel/apps
echo "4ce7d92e99c7b7d5c90cd5491f9ee3988c82b35af9a05c0e4fbcccbce47be9a6  voice-assistant-20261002.tar.gz" | sha256sum -c -
tar -xzf voice-assistant-20261002.tar.gz
cd voice-assistant
```

本配置使用 AX-FSMN 检测语音、FireRedASR2 识别问题、Qwen3.5-0.8B 生成回答、MeloTTS 合成语音。适用环境为 RK3576、Linux aarch64、Python 3.12、AXCL 3.16.0 与 AX8850 16GB M.2 算力卡。8GB 配置尚未完成回归。

## 安装 Python 依赖

在开发板上确认 `axcl-smi` 能识别算力卡，保持风扇运行。安装目录预留至少 5GB 可用空间；模型文件约 2.56GB，另需程序、Python 依赖和生成音频空间。

在本目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c "import axengine; print(axengine.get_available_providers())"
```

输出应包含 `AXCLRTExecutionProvider`。包内 PyAXEngine wheel 与本次测试版本一致。系统须已安装 AXCL 驱动及 `libsndfile1`。

## 下载模型

```bash
.venv/bin/python prepare.py
.venv/bin/python prepare.py --check
```

程序从固定提交下载模型并校验 SHA256。末尾显示 `All package and model files verified.` 后继续。如已有同目录布局的模型，可用 `--reuse /已有安装目录` 校验并复用文件。

需要代理时，在下载前按实际代理地址设置 `http_proxy` 和 `https_proxy`。下载完成后推理不需要外网连接。

## 运行音频问答

在开发板第一个终端启动应用：

```bash
sudo .venv/bin/python run.py --port 8008
```

在第二个终端进入同一目录，发送两条配套样本：

```bash
.venv/bin/python send_wav.py --input samples/Q1.wav samples/Q3.wav --output output-demo
```

首次加载模型需要等待。完成后，`output-demo/result.json` 保存识别文本和模型回答，`answer-*.wav` 保存实际生成的44.1kHz语音片段。输出目录不能预先存在；再次运行时更换目录名。文件问答结束后会停止模型服务，网页入口仍保留。退出应用时在第一个终端按 Ctrl+C。

使用自己的输入时，提供0至10秒、16kHz、单声道、PCM16 WAV 文件。一次请求只提出一个简短问题。回复为模型生成内容，需要自行核实。

## 打开网页

在电脑终端建立端口转发，将 `开发板IP` 替换为实际地址：

```bash
ssh -L 8008:127.0.0.1:8008 baiwen@开发板IP
```

浏览器访问 `http://127.0.0.1:8008`，点击“一键启动服务”，确认三个模型服务就绪后再开始对话。麦克风需浏览器授权；当前实测使用音频文件经WebSocket输入，物理麦克风与扬声器效果需结合现场设备确认。

本运行包只列出已配置的离线组合。仓库其他组合使用不同模型与运行库，不能直接替换权重路径。

## 核对版本与输出

`deployment-manifest.json` 包含程序、运行库和模型的逐文件SHA256及固定来源；`runtime/sources` 保留源码版本和适配补丁。两条配套输入来自 `AXERA-TECH/Spoken-Communication.axera@ecd09194a4ed417f6466dedebcd85192118a7bc8`，由原始24kHz样本转为16kHz PCM16。

语音检测、识别、文本模型和语音解码器使用算力卡；音频预处理、文本前端和Melo ONNX编码器使用RK3576主机CPU。默认未启用Qwen图像输入，不能据此认定视觉分支通过。
