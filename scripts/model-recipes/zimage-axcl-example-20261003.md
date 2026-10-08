## 准备出图示例

本例在 RK3576 + AX8850 16GB M.2 算力卡上运行，使用 Python 3.12、AXCL 3.16.0 和 PyAXEngine 0.1.3.rc3。输入为两条固定的中英文提示词，输出为 512×512 图片。8GB 卡尚未完成本模型的回归验证。

下载[配套示例包](/examples/zimage-axcl-example-20261003.tar.gz)，保存到连接算力卡的 RK3576 主机 `~/edgeaccel/`。在主机终端校验并解压：

```bash
cd ~/edgeaccel
echo '863c6151e25f4683c31ce0d080e0190f860a43cf4f54afc4c7be1a450fdae8f3  zimage-axcl-example-20261003.tar.gz' | sha256sum -c -
tar -xzf zimage-axcl-example-20261003.tar.gz
cd zimage-axcl-example
```

校验应输出 `OK`。按 [Python 接口](../../usage/python.md#安装已核对的-pyaxengine-版本)下载并校验官方 wheel，保存到 `~/axcl-setup`，然后创建独立环境：

```bash
python3 -m venv ~/edgeaccel/zimage-env
source ~/edgeaccel/zimage-env/bin/activate
python -m pip install \
  ~/axcl-setup/axengine-0.1.3-py3-none-any.whl \
  -r requirements.txt 'opencv-python-headless==4.11.0.86'
python -m pip check
export PATH=/usr/bin/axcl:$PATH
axcl-smi
```

确认依赖无冲突，设备 0 可用且没有其他推理任务。示例明确选择 `AXCLRTExecutionProvider`，固定使用 `diffusers==0.32.1`，不要直接升级其他模型共用的 Python 环境。

## 下载模型文件

模型目录需要存放 102 个文件，约 11.65 GiB；建议至少预留 15 GiB。板载空间不足时，将 `MODEL_DIR` 改为已挂载的存储卡或 SSD 目录。

```bash
MODEL_DIR=~/edgeaccel/models/z-image-turbo/117d8586d5c5
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
python download_models.py --model-dir "$MODEL_DIR"
```

程序从官方仓库下载固定提交 `117d8586d5c50de6f4c6e0a7058e934c207407be`，逐一核对 SHA256。结束时应输出 `Verified 102 model files`。无需下载仅供 CPU 参考计算的三份 safetensors 权重。需要代理时，先在当前终端设置实际可用的 `http_proxy` 和 `https_proxy`，方法见[模型下载](../../usage/download-models.md)。

## 运行中英文出图

先检查示例包、依赖和模型文件。此命令不启动推理：

```bash
python run_examples.py --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/zimage-example --check-only
```

确认 `verifiedModelFiles` 为 `102` 后运行：

```bash
python run_examples.py --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/zimage-example
```

输出目录必须为新目录。程序依次执行文本编码、9 步去噪和 VAE 解码，使用随包提供的 seed 42 初始噪声。每次加载一个子模型，执行后释放其设备资源。去噪使用本轮算力卡生成的文本特征；包内 CPU 参考数组只用于数值核对。

此入口提供两条固定提示词，暂不接受自定义提示词参数。更换提示词需要重新准备对应的分词与 embedding 输入。

完成后应输出两条 `Saved` 信息，得到以下文件：

```text
~/edgeaccel/results/zimage-example/images/sample-1/result.png
~/edgeaccel/results/zimage-example/images/sample-2/result.png
```

打开图片后，结合下方提示词检查主体、颜色、动作和场景。再次执行 `axcl-smi`，确认模型进程已退出、资源已释放。程序报错时保留输出目录；排除原因后换用新的输出目录重试。

本次实测通过主机只读网络目录读取模型，逐个子模型的读取与加载占用较多时间。下方出图耗时包含这部分开销，且不含单独完成的文本编码阶段，不能作为本地 SSD 条件下的纯推理性能。
