---
title: "chatterbox-p192-ctx384-ax650 部署指南"
sidebar_label: "chatterbox-p192-ctx384-ax650"
description: "chatterbox-p192-ctx384-ax650 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# chatterbox-p192-ctx384-ax650 部署指南

chatterbox-p192-ctx384-ax650 用于语音合成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备主机与算力卡

本例将英文文字转换为语音：Windows 完成文本和音色条件预处理，RK3576 通过 AXCL 调用 32 个 T3 模型生成语音 token，再调用配套的单步 S3Gen 和 HiFT 模型生成 24 kHz WAV。

已验证 RK3576（约 4GB 主机内存）+ AX8850 16GB M.2 算力卡、AXCL V3.16.0。模型文件保存在 Windows，通过 SSH 只读提供给 RK3576；运行期间需保持连接。

RK3576 先完成[驱动与设备检查](../../usage/device-check.md)和[安装 PyAXEngine](../../usage/python.md)，再执行：

```bash
axcl-smi
sudo apt-get install -y rclone fuse3
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'ml_dtypes==0.5.3' \
  'torch==2.5.1' 'transformers==4.51.3'
python -c "import axengine; print(axengine.get_available_providers())"
```

Python 使用 3.12，输出须包含 `AXCLRTExecutionProvider`。停止其他推理程序并保持散热风扇运行。

## 下载三个固定版本

在 Windows 下载并解压 [Chatterbox 文字转语音部署包](../../../static/examples/chatterbox-tts-deployment-20261004.zip)。部署包提供运行脚本与文件清单，权重通过下面的命令下载。

| 仓库 | 固定提交 | 用途 |
| --- | --- | --- |
| AXERA-TECH/chatterbox-p192-ctx384-ax650 | `f37f2a4bd7331fbf511e089a6741f5685d58c2c0` | T3 编译模型和嵌入表 |
| AXERA-TECH/chatterbox-onestep | `2bec38c6ef8b34b721422d41d2030f6a226bfaac` | 单步 S3Gen、HiFT 和频谱处理 |
| ResembleAI/chatterbox | `5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18` | Windows 预处理所需的原始 T3、分词器和内置音色条件 |

权重与配套文件合计约 3.06GB，另需预留 Python 环境空间。在解压目录打开 PowerShell，使用 Python 3.12：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r .\requirements-pc.txt
.\.venv\Scripts\python.exe .\download_models.py
```

完成后输出 `Verified 73 fixed model and support files`。代理设置见[下载方式与文件校验](../../usage/download-models.md)。模型目录和配套源码保留在部署包目录内。

## 准备输入文字

继续在 Windows 的同一目录执行：

```powershell
.\.venv\Scripts\python.exe .\prepare_chatterbox_t3.py `
  --text "Hello, welcome to the demo." --language en `
  --cfg-weight 0.5 --bos-count 2 --cpu-tokens 0 --output .\prepared
```

`prepared` 目录须尚不存在。命令校验原始权重与编译嵌入表，生成 `input-embeddings.npy`、音色条件和 `preparation.json`；最后的 `completed` 应为 `true`。

将下面的用户名和 IP 替换为实际 SSH 登录信息，复制输入与运行脚本，并启动模型文件服务：

```powershell
$Board = "baiwen@192.168.1.44"
ssh $Board 'mkdir -p ~/edgeaccel/chatterbox'
scp .\chatterbox_t3_card.py .\chatterbox_audio_card.py "${Board}:edgeaccel/chatterbox/"
scp -r .\prepared "${Board}:edgeaccel/chatterbox/"
.\.venv\Scripts\python.exe .\serve_models.py --models-dir .\host-models --port 18870
```

看到 `"ready": true` 后保持窗口运行。在另一个 PowerShell 窗口建立转发：

```powershell
$Board = "baiwen@192.168.1.44"
ssh -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -N `
  -R 127.0.0.1:18870:127.0.0.1:18870 $Board
```

## 运行 T3 和语音合成

在 RK3576 的另一个 SSH 终端执行：

```bash
mkdir -p ~/edgeaccel/chatterbox/models
env http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= ALL_PROXY= all_proxy= \
  rclone mount :http: ~/edgeaccel/chatterbox/models \
  --http-url http://127.0.0.1:18870/ --read-only \
  --vfs-cache-mode off --buffer-size 0 \
  --vfs-read-chunk-size 8M --vfs-read-chunk-size-limit 32M \
  --config /dev/null --daemon --daemon-wait 20s
source ~/edgeaccel/python-env/bin/activate
MODEL_ROOT=~/edgeaccel/chatterbox/models
python ~/edgeaccel/chatterbox/chatterbox_t3_card.py \
  --model-dir "$MODEL_ROOT/chatterbox-p192-ctx384-ax650" \
  --prepared ~/edgeaccel/chatterbox/prepared \
  --max-new-tokens 240 --output ~/edgeaccel/results/chatterbox-t3-01
```

T3 使用 CFG 0.5、重复惩罚 1.2、温度 0.8 和随机种子 42。本次生成 52 个 token，其中最后一个为结束标记。先确认输出已完整结束，再运行后半段：

```bash
python ~/edgeaccel/chatterbox/chatterbox_audio_card.py \
  --model-dir "$MODEL_ROOT/chatterbox-onestep" \
  --reference-dir ~/edgeaccel/chatterbox/prepared \
  --voice-embedding ~/edgeaccel/chatterbox/prepared/s3gen-embedding.npy \
  --t3-result ~/edgeaccel/results/chatterbox-t3-01/deployment-result.json \
  --output ~/edgeaccel/results/chatterbox-audio-01
```

两个输出目录均须尚不存在。后半段会检查 T3 的完成状态及结束标记，使用全部声学 token 生成音频。本次为 51 个声学 token、2.04 秒音频，无 token 截断。

## 播放并检查结果

```bash
aplay ~/edgeaccel/results/chatterbox-audio-01/complete-t3-voice-clone/output.wav
python - <<'PY'
import json
from pathlib import Path
root = Path.home() / 'edgeaccel/results'
t3 = json.loads((root / 'chatterbox-t3-01/deployment-result.json').read_text())
audio = json.loads((root / 'chatterbox-audio-01/deployment-result.json').read_text())
assert t3['completed'] and t3['terminatedWithEos'] and audio['completed']
assert audio['sourceTokenCount'] == len(t3['generatedTokenIds']) - 1
print(t3['text'])
print('音频时长：', audio['samples'][0]['audioSeconds'], '秒')
PY
```

若 RK3576 没有音频输出设备，可将 WAV 复制回 Windows 播放。检查是否完整读出输入文字，有无漏词、重复、异常尾音或失真；文件生成成功不能替代内容检查。

本次 T3 完整运行约 73.82 秒，其中生成阶段约 41.49 秒；已加载的 S3Gen/HiFT 合成并保存输出约 1.82 秒。这些耗时包含校验或记录开销，不等同于常驻服务性能。

## 更换文字与结束运行

更换 Windows 预处理命令中的 `--text`，使用新的预处理目录和结果目录，复制新输入后重新运行。当前只验证了下方英文短句；其他语言、长文本和自定义参考音色需分别检查效果。

此编译版的 clone 路径最多接收 99 个生成的声学 token，加上 157 个参考 token，共 256 个。超过限制会停止，不能通过截断音频来判定部署成功。T3 也受预填充长度和 384 上下文限制。

完成后，在 RK3576 卸载目录，再在 Windows 的两个运行窗口按 `Ctrl+C` 关闭连接和文件服务：

```bash
cd ~
fusermount3 -u ~/edgeaccel/chatterbox/models
```


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成 T3 文字生成语音 token，并串接官方 S3Gen/HiFT 生成 2.04 秒音频；独立识别内容与输入英文短句一致。

**英文文字 → T3 → S3Gen/HiFT → WAV**

使用官方内置音色条件生成完整短句。Windows 只执行预处理，T3 语音 token 生成、S3Gen 和 HiFT 神经网络通过 AXCL 执行。

| 输入文字 | 独立 Whisper 识别 |
| --- | --- |
| Hello, welcome to the demo. | Hello, welcome to the demo. |

| 声学 token | 音频时长 | T3 完整运行 | T3 生成阶段 | S3Gen/HiFT 合成与保存 |
| --- | --- | --- | --- | --- |
| 51（另含1个结束标记） | 2.04 s | 73.817 s | 41.492 s | 1.821 s |

播放算力卡合成结果：Hello, welcome to the demo.

<audio controls preload="metadata" src="/validation/effects/chatterbox-p192-ctx384-ax650-20261004/hello-welcome-to-the-demo.wav" aria-label="播放算力卡合成结果：Hello, welcome to the demo."></audio>

[下载音频](../../../static/validation/effects/chatterbox-p192-ctx384-ax650-20261004/hello-welcome-to-the-demo.wav)

**使用时注意：**

- 本次为 16GB 卡、固定英文短句与官方内置音色的基本运行验证；其他语言、长文本、自定义参考音色和真实 8GB 卡尚未验证。
- 音频内容由独立 ASR 辅助核对；未完成人工试听或音质评分。输出保留声码器默认限幅，约 0.20% 的样本触及限幅阈值。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`f37f2a4bd7331fbf511e089a6741f5685d58c2c0`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 生成内容 | Hello, welcome to the demo. | 一条英文短句，官方内置音色条件。 |
| 算力卡模型 | 32 + 3 个 | 32 个 T3 编译模型及 3 个 S3Gen/HiFT 配套模型；共 3334 次实际调用。 |
| 输出音频 | 2.04 秒 / 24 kHz | T3 正常结束，51 个声学 token 全部用于合成。 |

适用范围：

- clone 路径最多容纳 99 个生成声学 token，超过限制须单独设计和验证分段流程。
- 耗时包含文件读取、加载、校验或记录开销；未验证常驻服务、实时率或并发。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`llama_p64_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/llama_p64_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`llama_p64_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/llama_p64_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`llama_p64_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/llama_p64_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`llama_p64_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/llama_p64_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`llama_p64_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/llama_p64_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`f37f2a4bd7331fbf511e089a6741f5685d58c2c0`。仓库中的 32 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/tree/f37f2a4bd7331fbf511e089a6741f5685d58c2c0)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/tree/f37f2a4bd7331fbf511e089a6741f5685d58c2c0)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/README.md)。

返回[完整模型目录](../catalog.mdx)。
