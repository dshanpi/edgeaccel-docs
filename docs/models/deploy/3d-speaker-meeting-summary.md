---
title: "3D-Speaker-Meeting-Summary 部署指南"
sidebar_label: "3D-Speaker-Meeting-Summary"
description: "3D-Speaker-Meeting-Summary 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# 3D-Speaker-Meeting-Summary 部署指南

3D-Speaker-Meeting-Summary 用于多阶段应用。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本例将一段会议录音转换为带说话人标签的文本，再生成会议总结。已验证的组合为 RK3576（约 4GB 主机内存）、AX8850 16GB M.2 算力卡和 AXCL V3.16.0。40 个神经网络模型均通过 AXCL 在算力卡上执行。

模型与样例约 5.32GB，保存在 Windows 主机。RK3576 通过 SSH 只读访问这些文件；Windows 负责提供文件，不执行模型推理。运行期间需要保持网络连接。此页展示这一实际验证过的部署方式。

在 RK3576 上完成[驱动与设备检查](../../usage/device-check.md)和[安装 PyAXEngine](../../usage/python.md)，然后执行：

```bash
axcl-smi
sudo apt-get install -y rclone fuse3 build-essential python3-dev
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' \
  'torchaudio==2.5.1' 'transformers==4.51.3' 'funasr==1.2.7' \
  'librosa==0.11.0' 'soundfile==0.13.1' 'hdbscan==0.8.44' \
  'kaldi-native-fbank==1.22.3' 'ml_dtypes==0.5.3' \
  'sentencepiece==0.2.1' 'scipy==1.17.1' 'scikit-learn==1.9.1' \
  'umap-learn==0.5.12' 'jieba==0.42.1' 'PyYAML==6.0.3' \
  'loguru==0.7.3' setuptools wheel
python -m pip install --no-deps --no-build-isolation 'fastcluster==1.2.6'
python -c "import axengine, funasr, hdbscan, fastcluster; print(axengine.get_available_providers())"
```

Python 环境使用 3.12；最后一条命令应输出 `AXCLRTExecutionProvider`。模型运行前停止其他推理程序，保持散热风扇运行，并为输出文件预留空间。

## 下载模型与配套程序

在 Windows 下载[会议总结部署包](../../../static/examples/meeting-summary-deployment-20261004.zip)，解压到独立目录。部署包包含运行脚本、文件校验清单、只读文件服务和嵌入表校验数据，不包含模型权重。

在解压目录打开 PowerShell。Windows 需安装 Python 3.12 和 OpenSSH 客户端，并预留至少 6GB 模型存储空间：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install huggingface_hub
.\.venv\Scripts\python.exe .\download_models.py --models-dir .\models
```

下载固定版本 `b55d044e8eb419c779dc15c4b3e486dfe531f67e`，完成后输出 `Verified 86 fixed model and support files`。需要代理时，在此 PowerShell 窗口设置 `HTTP_PROXY` 和 `HTTPS_PROXY`，具体设置见[下载方式与文件校验](../../usage/download-models.md)。

将下面的用户名和 IP 替换为实际 RK3576 的 SSH 登录信息，复制运行文件：

```powershell
$Board = "baiwen@192.168.1.44"
ssh $Board 'mkdir -p ~/edgeaccel/meeting-summary'
scp .\meeting_summary_card.py .\embedding-row-sha256.bin "${Board}:edgeaccel/meeting-summary/"
.\.venv\Scripts\python.exe .\serve_models.py --models-dir .\models --port 18869
```

看到 `"ready": true` 后保持此窗口运行。在同一目录另开一个 PowerShell 窗口，建立 SSH 转发：

```powershell
$Board = "baiwen@192.168.1.44"
ssh -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -N `
  -R 127.0.0.1:18869:127.0.0.1:18869 $Board
```

登录后命令会持续运行，保持窗口开启。文件服务仅监听本机回环地址，RK3576 通过这条 SSH 连接读取文件。

## 挂载模型并运行

在 RK3576 的另一个 SSH 终端执行：

```bash
mkdir -p ~/edgeaccel/meeting-summary/models
env http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= ALL_PROXY= all_proxy= \
  rclone mount :http: ~/edgeaccel/meeting-summary/models \
  --http-url http://127.0.0.1:18869/ --read-only \
  --vfs-cache-mode off --buffer-size 0 \
  --vfs-read-chunk-size 8M --vfs-read-chunk-size-limit 32M \
  --config /dev/null --daemon --daemon-wait 20s
MODEL_DIR=~/edgeaccel/meeting-summary/models/3D-Speaker-Meeting-Summary
test -f "$MODEL_DIR/.validation-download.json" && echo '模型目录已就绪'
source ~/edgeaccel/python-env/bin/activate
python ~/edgeaccel/meeting-summary/meeting_summary_card.py \
  --model-dir "$MODEL_DIR" --audio wav/vad_example.wav \
  --embedding-oracle ~/edgeaccel/meeting-summary/embedding-row-sha256.bin \
  --embedding-oracle-sha256 aa2ca3f481fa7bf2bc8bb26355515af94d6e46cf7c19a20cc0e672b969032a63 \
  --max-new-tokens 1024 --output ~/edgeaccel/results/meeting-summary-01
```

输出目录须尚不存在。脚本依次完成文件校验、语音活动检测、说话人聚类、语音识别和 Qwen3 总结，最后再次校验文件。本样例约 70.47 秒，实测完整流程约 41.7 分钟；耗时包含文件读取、校验、模型加载及结果记录，不能作为常驻服务的吞吐指标。

## 检查转录与总结

```bash
cat ~/edgeaccel/results/meeting-summary-01/vad_example.wav.txt
cat ~/edgeaccel/results/meeting-summary-01/vad_example.wav_summary.md
python - <<'PY'
import json
from pathlib import Path
r = json.loads((Path.home() / 'edgeaccel/results/meeting-summary-01/deployment-result.json').read_text())
assert r['completed'] and r['endedWithEos']
assert len(r['sessions']) == 40 and len(r['filesAfter']) == 86
assert all(s['calls'] > 0 and s['provider'] == 'AXCLRTExecutionProvider'
           for s in r['sessions'])
print('完整流程结束，已生成转录和总结。')
PY
```

先对照录音检查转录，再核对总结是否保留原文信息。`Speaker_0` 等编号是当前录音中的聚类标签。识别错字、人物归属和模型补充的解释需要人工复核，不能直接当作正式会议纪要。

程序未生成结束标记、文件校验不一致或网络断开时，不能把已有部分输出视为完整结果。保留输出目录，修复连接后使用新的输出目录重试。

完成处理后，先在 RK3576 卸载模型目录，再在 Windows 的两个运行窗口按 `Ctrl+C` 关闭转发和文件服务：

```bash
cd ~
fusermount3 -u ~/edgeaccel/meeting-summary/models
```

下方展示本次原始音频、完整转录和模型总结。其他音频、实时麦克风、并发和真实 8GB 卡尚需分别验证。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成会议录音的转录与本地总结。部署页提供原始录音、完整转录和模型生成的总结。

**会议录音 → 说话人转录 → 本地总结**

同一段录音依次完成语音检测、说话人聚类、识别和 Qwen3 总结。以下为未修改的实际输出；识别错字及总结中的补充解释需对照录音复核。

**示例 1：输入**

```text
Speaker_0: [0.000 63.810] 试错的过程很简单，而且特别是今天报名昌雪卡的同学，你们可以。听到后面的有专门的活动课，他会大大降低你的试绸成本。其实你也可以不来听课。为什么你自己写嘛？我写今天写5个点，我就试试试验一下，反正这5个点不行，我再写5个点，这是再不行。那再写5个点吧，。你总会所谓的活动大神和所谓的高手都是只有一个。把所有的错，所有的坑全国趟一遍，留下正确的你就是所谓的大神。明白吗？所以说关于活动通过这一块，我只送给你们四个字啊，换位思考。如果说你要想降低。你的试错成本，今天来这里你们就是对的。。因为有畅血唱血卡这个机会，所以说关于活动过于不过这个问题，或者活动很难通过这个话题。呃，如果真的。那要坐下来聊的话，要聊一天。但是我觉得我刚才说的四个字足够。好，谢谢。
Speaker_1: [63.810 70.471] 好，非常感谢那个三茂老师的回答。三茂老师说，我们在。整个店铺的这个活动当中，我们要学会换位思考。其实我。
```

**实际回复**

```text
**参会人员总结：**  
会议中明确出现的发言人包括：  
- **三茂老师**（也称“Speaker_0”）：主讲人，围绕“活动试错成本”“换位思考”等核心议题进行分享，提出“换位思考”是降低试错成本的关键方法，并强调“活动大神”是通过遍历所有错误后才形成的。  
- **另一位与会者**（Speaker_1）：在三茂老师发言后进行补充，表示认同其观点，进一步展开“换位思考”在店铺活动中的实践意义。

---

**内容摘要：**  
本次会议聚焦于**活动策划与执行中的试错成本问题**，核心观点如下：  

1. **降低试错成本的关键是“换位思考”**：  
   三茂老师指出，真正“厉害”的活动从业者并非天生聪明，而是通过不断尝试、犯错、总结，将所有“坑”都走一遍，最终留下正确路径。因此，建议参与者以“换位思考”视角去理解用户需求与活动设计，从而减少盲目试错。  

2. **试错是必经之路，但可被优化**：  
   会议强调，即使不参加听课，参与者也可以自行尝试（如“写5个点，不行就再写”），但通过“畅血卡”等报名机会，可获得专业指导与资源，显著降低试错成本。  

3. **“活动大神”本质是“经历过所有错误的人”**：  
   三茂老师用“把所有错都走一遍”来解释高手的形成路径，打破“天赋论”，强调实践与反思的重要性。  

4. **会议主题明确但未深入展开**：  
   虽然三茂老师提出“换位思考”作为核心，但未展开具体案例或操作步骤，也未深入讨论活动通过率、流程设计等细节，后续可进一步探讨。  

**结论：**  
本次会议以“换位思考”为核心理念，倡导参与者以用户视角出发，主动试错、反思、迭代，从而在活动策划中实现低成本、高效率的实践路径。参会者主要为对活动运营感兴趣的学习者或从业者，会议内容具有启发性但尚属初步引导。
```

输入栏为完整转录文本，输出栏为本地 Qwen3 生成的总结。已生成结束标记。

| 输入时长 | 完整流程 | AXCL 调用合计 | 模型调用 | 生成 token（含结束标记） |
| --- | --- | --- | --- | --- |
| 70.471 s | 2500.734 s | 2137.277 s | 18187 | 488 |

播放本次完整输入录音（70.47 秒）

<audio controls preload="metadata" src="/validation/effects/3d-speaker-meeting-summary-20261004/vad_example.wav" aria-label="播放本次完整输入录音（70.47 秒）"></audio>

[下载音频](../../../static/validation/effects/3d-speaker-meeting-summary-20261004/vad_example.wav)

**使用时注意：**

- 本次为 RK3576 + 16GB 卡、Windows 只读提供模型文件的单段录音基本验证。真实 8GB 卡、实时麦克风、并发和长期运行尚未验证。
- 转录中有专有名词识别不一致；总结包含模型对人物身份和观点的归纳，需要对照原始录音复核。未报告识别、说话人分离或总结准确率。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`b55d044e8eb419c779dc15c4b3e486dfe531f67e`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 执行模型 | 40 个 AXModel | 语音检测、说话人模型、语音识别及 Qwen3 分层模型全部执行 AXCL。 |
| 输入录音 | 70.47 秒 | 单段官方样例，完整文件处理。 |
| 总结输出 | 488 token | 含结束标记；转录与总结原样保留。 |

适用范围：

- 完整流程约 41.7 分钟，包含网络读取、前后校验、加载及记录开销；不代表常驻服务性能。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`ax_meeting_transc_demo.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/ax_meeting_transc_demo.py) | Python 程序 / 前后处理 |
| [`demo.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/demo.py) | Python 程序 / 前后处理 |
| [`ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/qwen3_p256_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/qwen3_p256_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/qwen3_p256_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/qwen3_p256_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/qwen3_p256_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/qwen3_p256_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/qwen3_p256_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/qwen3_p256_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/qwen3_p256_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/qwen3_p256_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assert/gradio_demo.JPG`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/assert/gradio_demo.JPG) | 配套资源 |
| [`config.json`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/requirements.txt) | Python 依赖清单 |
| [`tokenizer_qwen3_int4/config.json`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/tokenizer_qwen3_int4/config.json) | 运行配置 |
| [`tokenizer_qwen3_int4/generation_config.json`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/tokenizer_qwen3_int4/generation_config.json) | 运行配置 |
| [`tokenizer_qwen3_int4/quantize_config.json`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/tokenizer_qwen3_int4/quantize_config.json) | 运行配置 |
| [`tokenizer_qwen3_int4/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/tokenizer_qwen3_int4/tokenizer_config.json) | 运行配置 |

仓库提交：`b55d044e8eb419c779dc15c4b3e486dfe531f67e`。仓库中的 40 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/tree/b55d044e8eb419c779dc15c4b3e486dfe531f67e)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/tree/b55d044e8eb419c779dc15c4b3e486dfe531f67e)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/README.md)。
- [主要程序入口：ax_meeting_transc_demo.py](https://huggingface.co/AXERA-TECH/3D-Speaker-Meeting-Summary/blob/b55d044e8eb419c779dc15c4b3e486dfe531f67e/ax_meeting_transc_demo.py)。

返回[完整模型目录](../catalog.mdx)。
