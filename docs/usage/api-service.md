---
title: "通过 HTTP 接入大模型"
---

# 通过 HTTP 接入大模型

在 Linux 主机先按[Qwen3-0.6B 部署指南](../models/deploy/qwen3-0-6b.md)启动服务，也可选择其他已有运行步骤的文本模型。本页以本机 HTTP 客户端访问为例，使用运行时提供的 OpenAI 风格接口。

## 启动服务

按对应模型页的“启动单卡服务”操作，保持终端 A 运行。下文默认服务端口为 `8000`，更换端口后同时修改所有客户端 URL。

等待模型加载完成。本文固定版本没有 `--host` 参数，服务可能同时可经主机局域网地址访问。示例客户端访问 `127.0.0.1` 并不表示服务只绑定回环地址；对外开放前应配置访问控制。

## 查询实际模型名称

主机终端 B 执行：

```bash
curl --fail http://127.0.0.1:8000/v1/models
```

返回应包含模型列表。将其中的 `id` 填入下面的 `MODEL_ID`，不要直接把文件夹名称当作接口中的模型名称。

```bash
MODEL_ID='替换为接口返回的模型ID'
export MODEL_ID
python3 - <<'PY'
import json, os, urllib.request
model = os.environ['MODEL_ID']
if model == '替换为接口返回的模型ID':
    raise SystemExit('请先设置 MODEL_ID')
payload = {
    'model': model,
    'messages': [{'role': 'user', 'content': '用一句话说明算力卡的用途。'}],
    'stream': False,
    'max_tokens': 128,
    'temperature': 0,
    'enable_thinking': False,
}
request = urllib.request.Request(
    'http://127.0.0.1:8000/v1/chat/completions',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json'},
)
with urllib.request.urlopen(request, timeout=180) as response:
    result = json.load(response)
print(result["choices"][0]["message"]["content"])
PY
```

确认响应包含可读回答，服务日志没有模型或内存错误。连接失败先核对进程、端口与加载日志；超时先缩短请求，不直接增加并发。

## 处理端口绑定失败

若日志提示 `Port ... is unavailable`，先用 `ss -ltnp` 检查该端口是否有服务监听。只停止确认不再需要的模型进程；也可给新模型分配另一个端口，并同步修改客户端 URL。

快速切换模型时，即使没有监听者，端口也可能暂时无法重新绑定。可等待端口释放，或为新模型分配其他端口。端口失败发生在模型加载前，不能据此判断模型或算力卡不兼容。

## 接入图片与向量检索

图片问答需要加载 VLM，按运行时示例构造媒体请求；普通文本模型不接受图像。向量模型需要对应配置，并调用 `/v1/embeddings`，不使用聊天接口代替。扩展前阅读[多模态](../models/vision-language.md)和[OCR 与检索](../models/extensions.md)。

首次测试保持单请求，记录加载时间、首 token 等待、完整响应时间及资源占用。终端 A 使用 Ctrl+C 正常停止服务，确认进程退出后再加载另一模型。

依据：[AX-LLM 服务接口](https://github.com/AXERA-TECH/ax-llm/tree/8501c22b940f8c5804cb35044c5ffc136918b8f1)。具体模型的实际输出与检查范围见对应部署页。
