## 安装图像处理依赖

本页使用 RK3576 主机和 AX8850 16GB M.2 算力卡，运行 OCR、版面分析、图像分类和规则决策。五个 `.axmodel` 均使用 AXCL；二维码解析、文本规则和图像处理在主机 CPU 上执行。

保留上方下载得到的 `$MODEL_DIR`，在 RK3576 主机执行：

```bash
sudo apt-get install -y libzbar0 unzip
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' \
  'Pillow==11.3.0' 'pyzbar==0.1.9' 'pyahocorasick==2.3.1' 'google-re2==1.1.20251105' \
  'opencc-python-reimplemented==0.1.7' 'pyclipper==1.4.0'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本例无需安装 Flask，也不要同时安装 `opencv-python` 和 `opencv-python-headless`。

## 检查配套文件

| 文件 | 用途 |
| --- | --- |
| `axmodel/ppocrv5/det_npu1.axmodel` | 检测文字区域 |
| `axmodel/ppocrv5/cls_npu1.axmodel` | 判断文字方向 |
| `axmodel/ppocrv5/rec_npu1.axmodel` | 识别文字 |
| `axmodel/ppstructurev3/ppstructure_npu1.axmodel` | 分析图文版面 |
| `axmodel/nsfw/nsfw_npu1.axmodel` | 输出图像内容分类分数 |
| `src/perception/dict/ppocrv5_dict.txt` | OCR 字典 |
| `src/understanding/keywords/` | 关键词规则 |
| `src/understanding/blacklists/` | 二维码域名规则 |

保留全部 `src/` 目录和字典、规则文件。当前固定版本实际提供上述五个 NPU1 权重；运行示例会核对文件版本与校验值。

## 运行八组示例

下载 [图像审核算力卡示例包](../../../static/examples/inspector-card-example.zip)，保存到 `~/edgeaccel/` 后执行：

```bash
mkdir -p ~/edgeaccel/inspector-example
unzip ~/edgeaccel/inspector-card-example.zip -d ~/edgeaccel/inspector-example
python ~/edgeaccel/inspector-example/inspector_card.py \
  --model-dir "$MODEL_DIR" \
  --inputs ~/edgeaccel/inspector-example/inputs \
  --output ~/edgeaccel/results/inspector-01
```

输出目录须尚不存在。八组输入包含普通文字、虚构联系账号、营销组合、离线二维码、图文版面、竖版文档、空白图和重复输入。

`deployment-result.json` 中 `completed` 为 `true` 表示所有样例完成。每组记录包含原图、预处理图、文字框、OCR 文本、图像分类分数、规则命中和最终决策。绿色框标记 OCR 区域，橙色框标记版面中的图片区域；框上的序号对应文字块顺序。

| 决策 | 含义 |
| --- | --- |
| `PASS` | 本次规则和阈值没有触发复核或拒绝条件 |
| `REVIEW` | 需要人工复核，例如联系信息、未知二维码或缺少预期文字 |
| `REJECT` | 命中较强规则或图像分类拒绝阈值 |

决策是模型信号与规则的组合，不是某一个模型的“正确率”。最终 `score` 也不是通过概率；规则触发拒绝时，该字段仍可能为 0。

## 检查自己的图片

```bash
python ~/edgeaccel/inspector-example/inspector_card.py \
  --model-dir "$MODEL_DIR" \
  --inputs ~/edgeaccel/inspector-example/inputs \
  --image ~/Pictures/example.png \
  --output ~/edgeaccel/results/inspector-custom-01
```

打开结果目录中的 `overlay.png` 结尾文件，并对照 JSON 中的实际文字和决策理由。竖版文档采用 0.5°～15° 的小角度矫正；超过该范围时保留原图，必要时先手动调整方向。

本例按串行方式调用算力卡，二维码保留离线解析和域名规则，不访问二维码中的网址，也不展开短链接。需要接入联网审核服务时，应另行验证跳转、域名规则和并发行为。

## 查看结果和耗时

下方展示本次算力卡生成的文字框、实际识别文本与决策。OCR 可能出现多余字符或大小写混淆，应结合原图查看。

流程耗时包含预处理、延迟加载模型、CPU 规则、设备调用、原始张量保存和结果绘制；首次调用还包含模型初始化。AXCL 时间仅累计网络的 Python `run` 调用，不代表整张图片的处理时间或服务吞吐。

本次使用普通图片和合成规则样例，未验收 NSFW 类别的召回率、误报率或完整审核规则覆盖，也未进行长期运行和实际 8GB 卡回归。
