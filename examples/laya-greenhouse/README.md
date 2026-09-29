# Laya 智能温室

在 RK3576 + AX8850 M.2 算力卡上运行 Laya multilingual。Python 服务加载官方固定版本模型，浏览器显示动作概率、紧急程度、耗时和模拟执行动画。未接入真实传感器或执行器。

## 准备并下载

需要已安装 AXCL 的 Linux ARM64 主机、Python 3.12、PyAXEngine 0.1.3（官方 rc3 wheel）、NumPy 2.5.3、Transformers 5.17.0、Tokenizers 0.23.2、ml-dtypes 0.6.0。使用独立虚拟环境，避免改变其他模型依赖。

```bash
cd ~/edgeaccel/laya-greenhouse
export https_proxy=http://192.168.1.38:7897  # 替换为可用代理；直连时省略
export http_proxy="$https_proxy"
python3 download_model.py --model-dir ~/edgeaccel/models/Laya
```

`model-lock.json` 固定官方提交与五个文件的 SHA256。下载约 568 MB，不包含其他语言检查点。已有修改过的官方脚本请放在其他目录，本项目需要未修改的原文件。

## 运行

```bash
~/edgeaccel/laya-env/bin/python server.py --model-dir ~/edgeaccel/models/Laya
```

在开发板浏览器打开 `http://127.0.0.1:8855/`。等待“算力卡已就绪”，选择场景后点击“让 Laya 判断”。四个问题依次在卡上推理。界面没有离线伪造结果或 CPU 回退。

## 安装桌面入口

先退出前台服务，再执行：

```bash
bash install-desktop.sh
bash launch.sh
```

非默认路径可在同目录 `config.env` 中设置 `LAYA_PYTHON` 和 `LAYA_MODEL_DIR`。启动器使用用户级临时服务，不设置开机自启。停止服务：

```bash
systemctl --user stop laya-greenhouse
```

电脑远程查看时运行 `ssh -L 8855:127.0.0.1:8855 用户名@开发板IP`，再打开电脑上的同一地址。服务仅监听回环地址。

## 理解决策

- 选择动作：通风、补水、补光、保持中的最高概率项。
- 紧急程度：0（无需处理）、1（需要处理）、2（立即处理）的期望分值。
- 是否缺水 / 是否过热：对应命题为真的概率。
- 当最高动作概率达到 55% 时，自动播放**模拟动画**；否则由用户点击演示。这是演示界面的阈值，不是模型准确率标准。
- 输入不超过 80 字；若组合问题后超过 256 token，会拒绝请求，避免静默截断。数字量程不表示实际传感器校准。
- 模型错误或超时后停止工作进程，界面显示错误，不生成替代结果。检查设备并重新启动应用后再试。

模型及官方推理代码来源：[AXERA-TECH/Laya](https://huggingface.co/AXERA-TECH/Laya)。项目运行时仅在内存中将执行后端切换为 `AXCLRTExecutionProvider`，保留官方问题编码与后处理。
