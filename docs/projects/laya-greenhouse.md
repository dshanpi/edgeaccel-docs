---
title: "Laya 智能温室桌面演示"
sidebar_label: "Laya 智能温室"
description: "在 M.2 算力卡上运行 Laya，通过温室界面展示动作选择、判断概率和推理耗时。"
---

# 运行 Laya 智能温室

在 RK3576 桌面上调整温度、湿度、光照或输入一句观察描述，由 AX8850 M.2 算力卡上的 Laya 判断通风、补水、补光或保持现状。界面显示真实模型返回的概率、紧急程度与耗时，并用动画演示建议动作。

本项目使用虚拟温室，未连接真实传感器、阀门或风扇。Laya 输出结构化决策，不生成聊天回复。模型基本用法见 [Laya 部署指南](../models/deploy/laya.md)。

## 准备运行环境

在已安装 AXCL 的 RK3576 Linux 主机上操作。本项目使用 AX8850 16GB 算力卡、Python 3.12 和独立 Python 环境。先确认 `axcl-smi` 能识别算力卡，并停止占用同一张卡的其他推理程序。

按 [PyAXEngine 安装说明](../usage/python.md)下载并校验官方 `axengine-0.1.3-py3-none-any.whl`，然后执行：

```bash
python3 -m venv ~/edgeaccel/laya-env
source ~/edgeaccel/laya-env/bin/activate
python -m pip install \
  ~/axcl-setup/axengine-0.1.3-py3-none-any.whl \
  'numpy==2.5.3' 'transformers==5.17.0' \
  'tokenizers==0.23.2' 'ml-dtypes==0.6.0'
python -m pip check
```

检查结果应为 `No broken requirements found`。桌面需要 Chromium 或其他支持现代 JavaScript 的浏览器。

## 下载程序和模型

下载 [智能温室程序包](../../static/examples/laya-greenhouse.zip)，复制到开发板的 `~/Downloads`，再解压：

```bash
mkdir -p ~/edgeaccel
python3 -m zipfile -e ~/Downloads/laya-greenhouse.zip ~/edgeaccel
cd ~/edgeaccel/laya-greenhouse
```

下载官方固定版本的 multilingual 检查点：

```bash
python3 download_model.py --model-dir ~/edgeaccel/models/Laya
```

下载约 568 MB，包含模型、分词器、配置和官方推理脚本五个文件。程序根据 `model-lock.json` 校验 SHA256；完成后显示“5 个文件已校验”。固定提交为 `4f02f411fb9b9b09b4a4842b4486177b9594ba9e`。

如果已有 Laya 文件，仍可运行下载命令，校验一致的文件会直接复用。被修改过的 `infer.py` 不能通过校验，请改用空目录下载；本项目启动时在内存中切换 AXCL 后端，不修改官方原文件。

## 启动桌面演示

先以前台方式确认服务可以启动：

```bash
cd ~/edgeaccel/laya-greenhouse
~/edgeaccel/laya-env/bin/python server.py \
  --model-dir ~/edgeaccel/models/Laya
```

在开发板浏览器打开 `http://127.0.0.1:8855/`。等待右上角显示“算力卡已就绪”，再提交场景。首次启动需要加载和校验模型。

按 `Ctrl+C` 退出前台服务后，可安装桌面入口：

```bash
bash install-desktop.sh
bash launch.sh
```

应用菜单和桌面会出现“Laya 智能温室”。若桌面要求信任启动器，右键选择“允许启动”。启动器运行用户级临时服务，不设置开机自启；关闭浏览器后，模型仍驻留以便再次打开。释放模型：

```bash
systemctl --user stop laya-greenhouse
```

使用其他安装路径时，在程序目录创建 `config.env`，填写实际绝对路径：

```bash
LAYA_PYTHON=/home/用户名/edgeaccel/laya-env/bin/python
LAYA_MODEL_DIR=/home/用户名/edgeaccel/models/Laya
```

## 观察场景响应

1. 选择“舒适晴天”“干燥缺水”“闷热潮湿”或“日落缺光”。场景按钮只填写输入，不预设模型答案。
2. 点击“让 Laya 判断”。温室状态与补充观察一起传给模型。
3. 查看四种动作的概率、紧急程度，以及“需要浇水”“需要降温”的判断。
4. 调整数值或描述后再次提交，比较最近判断。点击“导出本次输入与结果”可保存完整 JSON。

| 界面结果 | 含义 |
| --- | --- |
| 建议动作 | `choice` 返回最高概率的候选项，其他候选概率仍完整显示 |
| 处理紧急程度 | `score` 在 0（无需处理）、1（需要处理）、2（立即处理）上的期望分值 |
| 需要浇水 / 需要降温 | `noul` 对相应命题为真的概率 |
| 4 次推理调用 | 四个问题的 AXCL 调用总耗时，不包含首次模型加载 |
| 分词 + 推理 + 后处理 | 服务端处理本次请求的耗时，不包含浏览器通信 |

最高动作概率达到 55% 时自动播放模拟动画；低于该值时显示“待确认”，由使用者点击“演示建议”。55% 是界面演示阈值，不能解释为准确率或真实设备的自动控制条件。

## 查看部署效果

在 RK3576 + AX8850 16GB 上完成 6 次请求，每次包含四个问题，全部由 `AXCLRTExecutionProvider` 返回有效结果。四次推理调用合计耗时为 130.8–138.2 ms，不包含首次加载。

| 实际输入 | 模型建议 | 该动作概率 | 结果核对 |
| --- | --- | ---: | --- |
| 舒适晴天：25℃、土壤湿度 65%、光照 80%，生长正常 | 补光 | 64.6% | 与“无需操作”的预期不符 |
| 干燥缺水：土壤湿度 10%，土壤干裂、叶片萎蔫 | 补水 | 78.7% | 符合描述 |
| 闷热潮湿：42℃，需要通风降温 | 通风 | 93.7% | 符合描述 |
| 日落缺光：光照 5%，需要补充光照 | 补光 | 95.1% | 符合描述 |
| 重复提交相同的干燥缺水输入 | 补水 | 78.7% | 与上次概率一致 |
| 手动输入“今早忘记浇水，泥土干燥，先补水” | 补水 | 49.4% | 最高概率项符合描述，界面提示人工确认 |

以上证明本项目可完成真实推理和结果展示，不代表温室控制准确率已达标。“舒适晴天”的误判也表明，较高概率不等于判断正确。可下载 [本次输入与完整结果](../../static/projects/laya-greenhouse/results.json)复核；三个官方检查点的固定样例见 [Laya 部署效果](../models/deploy/laya.md#查看部署效果)。

## 在电脑上查看

服务仅监听开发板的回环地址。电脑与开发板在同一网络时，在电脑终端建立 SSH 转发：

```bash
ssh -L 8855:127.0.0.1:8855 用户名@开发板IP
```

保持终端连接，在电脑浏览器打开 `http://127.0.0.1:8855/`。推理仍在开发板连接的算力卡上执行。

## 处理输入与运行问题

- 补充观察最多 80 字。若问题、候选项和状态合计超过模型的 256 token 输入长度，服务会拒绝请求；缩短描述后重试。
- 场景文字会影响决策。可分别测试“只有数值”和“数值加观察”，评估实际应用数据，不能据几个预设场景判断农业控制能力。
- 显示“模型不可用”或“本次判断未完成”时，没有生成替代结果。检查运行终端的错误、模型文件和设备状态，处理后重新启动服务。
- 模型只用于桌面决策展示；接入实际执行器前，需要另行设计传感器校验、动作约束与人工确认流程。

模型来源与格式说明：[AXERA-TECH/Laya 官方仓库](https://huggingface.co/AXERA-TECH/Laya)。
