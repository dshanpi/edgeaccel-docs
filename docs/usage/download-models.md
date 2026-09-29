---
title: "下载并核对模型文件"
sidebar_label: "手动操作：下载模型"
pagination_prev: null
pagination_next: null
---

# 下载并核对模型文件

本页是首次推理的手动操作步骤，用于下载并校验模型，也适用于切换下载来源或跨主机传输文件。选择[脚本运行](first-inference.md)时，YOLO11 所需文件由脚本自动准备，无需重复执行。

在 Linux 主机终端执行，也可在工作站下载后复制完整目录。先从[模型目录](../models/catalog.mdx)进入具体模型的部署文档，核对模型卡的编译目标、依赖版本、输入尺寸和许可证，再选择所需的下载方式。

## 选择同一套模型与应用

CV 示例通常需要 `.axmodel`、样例图片及相应后处理程序。大模型还需要 `config.json`、分词器、embedding 权重及全部分层模型。多模态模型额外需要视觉或音频编码器。保留仓库目录结构，不能只下载一个权重文件。

在仓库历史页面选择一个明确的提交或发布版本。Hugging Face 与 ModelScope 的 revision 不一定相同；不要用一个站点的提交号去访问另一个站点。

## 使用 Hugging Face 下载

```bash
sudo apt install -y python3-venv
python3 -m venv ~/edgeaccel/hf-env
~/edgeaccel/hf-env/bin/python -m pip install --upgrade huggingface_hub
```

工具安装完成后，进入[模型目录](../models/catalog.mdx)，复制具体模型页面的下载命令。各页已经固定仓库版本、目录和示例所需文件，下载后直接沿用该页的 `MODEL_DIR` 继续部署。

## 使用 ModelScope 下载

选择[模型目录](../models/catalog.mdx)中的 ModelScope 链接，在其文件页确认仓库 ID 和 revision。激活上节创建的虚拟环境，再安装下载工具。

```bash
source ~/edgeaccel/hf-env/bin/activate
python -m pip install --upgrade modelscope
```

以下 Python 示例中的 revision 需替换为 ModelScope 仓库实际提供的版本。若界面只提供 `master`，可使用该分支，并另外记录下载时间和文件 SHA256；分支名本身不能保证日后文件不变。

```python
from pathlib import Path
from modelscope import snapshot_download

snapshot_download(
    model_id="AXERA-TECH/YOLO11",
    revision="master",
    local_dir=str(Path.home() / "edgeaccel/models/YOLO11"),
)
```

Hugging Face 下载受阻时，可以使用 AXERA-TECH 官方 ModelScope 仓库中的对应文件。替代前逐项比较目标芯片、文件路径、文件大小和 SHA256，只有校验一致的文件才按同一份权重处理；相同文件名或相同模型名称不足以证明等价。

为两个来源分别记录仓库、revision、下载时间和文件校验值。模型分片、`config.json`、tokenizer、embedding 与前后处理程序必须来自已核对的同一套发布内容；不能因为某个权重相同就混用另一日期的配置。未经同哈希核对的包作为另一版本单独测试，不沿用已有实测结论。

## 控制下载与测试占用

下载前检查模型目录所在磁盘的可用空间，先确定当前模型需要的权重和配套资源，按独立页面逐个下载、测试。模型目录与日志、输入输出证据分别保存。

完成测试后，先把 revision、校验清单、运行命令、日志和输出复制到记录目录，并确认能够读取，再删除本次已不需要的模型权重。删除前核对绝对路径和目录内容，保留模型之外的工具、驱动、环境及原有项目。大模型的各层权重需完整下载后才能测试，不能用缺少分片的包判断容量或兼容性。

## 检查文件与校验值

以 YOLO11 为例，将 `MODEL_DIR` 设置为模型的实际下载目录（沿用具体模型页设置的变量也可）：

```bash
cd "$MODEL_DIR"
test -s ax650/yolo11s.axmodel
test -s football.jpg
sha256sum ax650/yolo11s.axmodel football.jpg > files.sha256
sha256sum -c files.sha256
```

跨主机传输时将 `files.sha256` 一起复制，并在接收端重新校验。自行生成的校验文件用于检测传输变化；只有与发布方提供的校验值比较，才能确认与发布文件一致。

通过 Git 下载时还需正确拉取 LFS 大文件。若 `.axmodel` 内容以 `version https://git-lfs.github.com/spec/v1` 开头，它只是指针文件，应重新下载真实权重。下载失败、缺少分片或校验不一致时停止运行。

首次手动运行 YOLO11 时，文件准备完成后继续[编译 AXCL 视觉示例](build-samples.md)，再按 YOLO11 部署指南执行推理。

依据：[HF 下载工具](https://huggingface.co/docs/huggingface_hub/guides/cli)、[ModelScope 下载说明](https://modelscope.cn/docs/models/download)、[YOLO11 模型仓库](https://huggingface.co/AXERA-TECH/YOLO11)。
