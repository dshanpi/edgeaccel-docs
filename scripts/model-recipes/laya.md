## 安装独立运行环境

Laya 接收文字或 JSON 状态，按给定问题输出类别、分值或判断概率。它不生成聊天回复。仓库包含 `english`、`multilingual`、`typed-decisions` 三个检查点，需要分别选择模型目录。

在 RK3576 主机执行。先按[PyAXEngine 安装说明](../../usage/python.md)下载并校验官方 wheel，再创建 Laya 专用环境：

```bash
python3 -m venv ~/edgeaccel/laya-env
source ~/edgeaccel/laya-env/bin/activate
python -m pip install \
  ~/axcl-setup/axengine-0.1.3-py3-none-any.whl \
  'numpy==2.5.3' 'transformers==5.17.0' \
  'tokenizers==0.23.2' 'ml-dtypes==0.6.0'
python -m pip check
```

本例采用仓库要求的 NumPy、Transformers 和 Tokenizers 版本；独立环境避免改变其他模型的依赖。

## 指定算力卡后端

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
p = Path('python/ax650/infer.py')
s = p.read_text()
old = 'provider = "AxEngineExecutionProvider"'
new = 'provider = "AXCLRTExecutionProvider"'
if old in s:
    backup = p.with_suffix('.py.upstream')
    if not backup.exists():
        backup.write_text(s)
    p.write_text(s.replace(old, new))
else:
    assert new in s, '源码与固定版本不匹配'
PY
```

只改变推理后端，保留官方分词、问题编码和分值后处理。

## 运行中文决策样例

```bash
cd "$MODEL_DIR"
python python/ax650/infer.py multilingual \
  --input multilingual/sample_request.json
```

日志应显示 `AXCLRTExecutionProvider`，随后输出包含 4 个问题的 `answers` 对象。中文样例询问重复扣款工单的处理部门、紧急程度、是否要求退款、是否表示取消服务。

## 运行英文与工作流样例

```bash
cd "$MODEL_DIR"
python python/ax650/infer.py english \
  --input english/sample_request.json
python python/ax650/infer.py typed-decisions \
  --input typed-decisions/sample_request.json
```

`choice` 返回选中的类别，`score` 按本题给出的等级计算期望分值，`noul` 返回命题为真的概率值。`score` 不是百分比；同一个数值在不同等级定义下含义不同。下方展示三个检查点的实际输出。

## 制作桌面演示

需要在桌面观察决策过程时，可继续部署 [Laya 智能温室](../../projects/laya-greenhouse.md)。项目提供环境滑块、中文观察输入、动作概率与温室动画，使用同一 multilingual 检查点和 AXCL 后端。

也可体验 [Laya 游戏实验室](../../projects/laya-games.md)：包含打方块、Flappy Bird、俄罗斯方块与贪吃蛇，支持观察模型决策和手动落点评分。
