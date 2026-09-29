## 准备 Python 环境

先按 [Python 接口](../../usage/python.md) 安装 PyAXEngine，再在连接算力卡的 RK3576 主机执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'scikit-image==0.25.2'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本页运行固定版本 `buffalo_l` 的五份权重，覆盖检测、106 点关键点、3D 68 点关键点、属性和 512 维特征。

上游将预训练权重用于非商业研究评估，商业使用需单独确认授权；见 [InsightFace 模型说明](https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md)。本页展示部署方法和样例输出，不代表模型已获商业授权。

## 准备测试图片

下载 [两张虚构人脸测试图](../../../static/validation/effects/insightface-20260928/input.png)，保存为 `$MODEL_DIR/fictional-people.png`，并校验：

```bash
echo '16c9acc754c595d92be86b2ea452f603b92d952ad068fc24265406636640b7d4  '"$MODEL_DIR/fictional-people.png" | sha256sum -c -
```

结果须为 `OK`。图片由 AI 生成，人物为虚构角色，没有真实身份或年龄、性别标注。下方检测框和关键点来自算力卡的实际推理，不是生成图片自带的标注。

## 运行五份模型

下载 [Insightface 算力卡示例](../../../static/examples/insightface_card.py)，保存为 `~/edgeaccel/insightface_card.py`。在同一主机终端执行：

```bash
python ~/edgeaccel/insightface_card.py \
  --model-dir "$MODEL_DIR" \
  --image "$MODEL_DIR/fictional-people.png" \
  --output ~/edgeaccel/results/insightface-01
```

输出目录须尚不存在。当前示例固定使用上方图片，依次处理原图、重复图和同尺寸空白图。各模型显式使用 AXCL 后端；图片前后处理在主机完成。

本次检测结果为 `2、2、0` 张人脸。检测模型调用三次；其余四份模型各调用四次，分别处理原图和重复图中的两张人脸，共 19 次调用。空白图没有检测到人脸，因此不调用后续四份模型。

`deployment-result.json` 中的 `completed` 应为 `true`。其中 `faces` 记录检测框、5 点、106 点、3D 68 点、姿态角、属性预测和特征向量；`sessions` 记录每份权重的形状与实际调用耗时。

## 查看检测与关键点

下载 [结果绘图脚本](../../../static/examples/insightface_view.py)，保存为 `~/edgeaccel/insightface_view.py`，执行：

```bash
python ~/edgeaccel/insightface_view.py \
  --result-dir ~/edgeaccel/results/insightface-01
```

在输出目录打开 `detection.png`、`landmarks-106.png` 和 `landmarks-68.png`，依次查看检测框与 5 点、106 点关键点、3D 68 点在原图平面的位置。绘图脚本读取实际结果，不会再次调用模型。

编号按图片从左到右排列，仅表示本张图片中的位置。3D 模型的第三维和姿态角是模型估计，不是经过标定的距离或测量值。

## 查看属性与特征结果

下方列出两张虚构人脸的属性预测，以及两条 512 维向量的余弦相似度。属性输出为模型分类和年龄估计，没有真值可用于计算准确率；相似度也不能直接作为身份判定阈值。

本次重复输入的原始模型输入、输出和最终结果完全一致，空白图未检出人脸。实际业务仍需补充合法测试数据、浮点模型对照和适用阈值评估；本页单张合成图片的结果不代表真实人群精度。
