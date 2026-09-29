## 准备标点恢复环境

在 RK3576 主机使用已安装 PyAXEngine 的虚拟环境，模型、字典和 SDK 必须来自前一节的同一提交。

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip check
cd "$MODEL_DIR"
test -s model.axmodel && test -s tokens.json
```

## 恢复文本标点

本模型接收无标点文字，输出补入标点的文字，不提供聊天或翻译接口。推理使用 M.2 卡，字典编码和文本拼接在主机执行。

```bash
cd "$MODEL_DIR"
PYTHONPATH="$MODEL_DIR/python" python - <<'PY'
from sherpa_punct_sdk import PunctuationPipeline
model = PunctuationPipeline(
    'model.axmodel', 'tokens.json', provider='AXCLRTExecutionProvider')
texts = [
    '今天天气真不错我们出去走走吧',
    '这个方案有三个优点第一成本低第二效率高第三维护简单',
    '人工智能技术正在改变我们的生活方式明天下午三点在公司会议室开会请准时参加他是一名优秀的工程师工作认真负责北京是中国的首都拥有悠久的历史文化随着科技的发展人们的生活越来越便利',
]
for text in texts:
    print('输入：', text)
    print('输出：', model(text))
PY
```

日志应显示 `AXCLRTExecutionProvider`。逐句检查输出是否保留原文，句号、逗号是否放在合理位置。第三段输入超过单窗口长度，经过 SDK 的滑动窗口处理；下方保留本次实际断句，仍存在句末逗号和错误停顿。
