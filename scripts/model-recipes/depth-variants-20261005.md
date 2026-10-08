## 运行其他三种 AX650 权重

前面的下载命令包含20张官方样图和下表权重。在已配置AXCL后端的Python环境中运行，输入由官方程序缩放为504×280、RGB uint8。本节组合在16GB卡实测。

| 规格 | 权重 | 结果解读 |
| --- | --- | --- |
| base | `models-ax650/da3-base.axmodel` | 本页使用单图深度输出 |
| metric-large | `models-ax650/da3metric-large.axmodel` | 保留原始输出；本次未进行尺度标定 |
| mono-large | `models-ax650/da3mono-large.axmodel` | 本页使用单图深度输出 |

在主机选择一个权重，运行仓库内20张样图。每张图保存在独立目录，避免覆盖：

```bash
WEIGHT=da3-base
# 也可设为 da3metric-large 或 da3mono-large
OUT=~/edgeaccel/results/depth-anything-3/$WEIGHT
mkdir -p "$OUT"
set -euo pipefail
for INPUT in "$MODEL_DIR"/examples/demo*.jpg; do
  NAME=$(basename "$INPUT" .jpg)
  mkdir -p "$OUT/$NAME"
  (
    cd "$OUT/$NAME"
    python "$MODEL_DIR/python/infer.py" \
      --model "$MODEL_DIR/models-ax650/$WEIGHT.axmodel" \
      --img "$INPUT" 2>&1 | tee run.log
    test -s output-ax.png
  )
done
```

打开新生成的 `OUT/demo01/output-ax.png`：左侧是原图，右侧是深度可视化。依次核对前景汽车、远处建筑、桥梁结构与室内物体的边界及近远关系。玻璃、反射、细小物体和绘画中的层次仍需人工检查。

### 判断可视化结果

官方程序将每张深度图单独归一化到0–255，再应用INFERNO配色。相同颜色在不同图片、不同权重中不代表相同距离；下面表格中的数值是归一化前的模型输出，不标注为米。

[上游metric模型卡](https://huggingface.co/depth-anything/DA3METRIC-LARGE)说明其使用规范化的公制深度表达，恢复实际尺度需要相机焦距。本页固定AXERA入口未接收相机标定参数；如需测距，须保留原始输出、核对导出定义及缩放后的相机参数，再用已知距离验证。不能将彩色图直接用作米制测量。
