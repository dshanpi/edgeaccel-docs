---
title: "通过 HTTP 接入大模型"
description: "固定 Qwen3-0.6B 和 AXCL 运行时，完成下载、服务启动、中文问答与停止检查。"
---

# 通过 HTTP 接入大模型

将 **Qwen3-0.6B** 启动为 HTTP 服务，用 Python 标准库发送一个固定中文问题，保存原始响应后停止服务。全部命令在连接算力卡的 RK3576 主机执行。

| 项目 | 本页固定配置 |
| --- | --- |
| 主机 | RK3576 DShanPi-A1，Ubuntu 24.04，aarch64，Python 3.12.3 |
| 算力卡 | AX8850 16GB，AXCL / 固件 3.16.0 |
| AX-LLM | `8501c22b940f8c5804cb35044c5ffc136918b8f1`，Release / AXCL |
| 模型提交 | `9bd240869b5ec6f28964a635cd421a80fcad9dc8` |
| 请求 | 中文问答，非流式，关闭思考，最多 128 tokens |

## 准备运行环境

先完成[AXCL 设备检查](device-check.md)与[编译 AXCL 大模型运行时](../models/llm-runtime.md)。本页使用已编译的固定版本程序，不使用模型仓库中可能面向芯片板端的二进制文件。

保持风扇开启，停止其他推理应用。工作目录建议至少有 1.5 GB 可用空间。已有外部存储时，先设置 `EDGEACCEL_WORK` 为当前用户可写的目录。

```bash
APP_ROOT=${EDGEACCEL_WORK:-$HOME/edgeaccel/application-guides}
AXLLM=${AXLLM:-$HOME/edgeaccel/src/ax-llm/build-axcl/install/bin/axllm}
mkdir -p "$APP_ROOT/http/model"
cd "$APP_ROOT/http"
MODEL_DIR="$PWD/model"
test -x "$AXLLM"
"$AXLLM" version
ldd "$AXLLM"
/usr/bin/axcl/axcl-smi
df -h .
```

版本应为上述提交的 `AXCL` 后端，依赖没有 `not found`，算力卡无其他推理进程。程序在其他路径时，在运行此段命令前设置 `AXLLM` 为实际绝对路径。

## 下载固定模型包

主机需安装 `curl`，网络需要代理时使用 [Python 页的代理设置](python.md#准备设备与目录)。下面使用 4 个下载任务获取 28 个模型分片和 5 个配套文件。完整下载后才改名，重跑会重新下载缺失项，并保存本地 `files.json` 校验清单。

```bash
python3 - <<'PY'
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,hashlib,json
root=Path('model');rev='9bd240869b5ec6f28964a635cd421a80fcad9dc8'
files=['config.json','post_config.json','qwen3_post.axmodel','model.embed_tokens.weight.bfloat16.bin','qwen3_tokenizer.txt']+[f'qwen3_p128_l{i}_together.axmodel' for i in range(28)]
def fetch(name):
 p=root/name;tmp=p.with_suffix(p.suffix+'.part')
 if not p.exists():subprocess.run(['curl','--http1.1','--retry-all-errors','--fail','--location','--silent','--show-error','--retry','3','--connect-timeout','20','--max-time','600',f'https://huggingface.co/AXERA-TECH/Qwen3-0.6B/resolve/{rev}/{name}','-o',str(tmp)],check=True)
 if not p.exists():
  assert tmp.stat().st_size>0
  tmp.replace(p)
 print('Downloaded',name,p.stat().st_size,flush=True)
 return {'name':name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()}
with ThreadPoolExecutor(max_workers=4) as pool:manifest=list(pool.map(fetch,files))
Path('files.json').write_text(json.dumps(manifest,indent=2))
print('33 files ready')
PY
```

`33 files ready` 只说明文件齐全。继续执行下方固定版本校验，不以旧文件存在代替版本检查。

<details>
<summary>展开并执行 33 个文件的 SHA-256 校验</summary>

```bash
sha256sum -c <<'SHA256'
ac1bea1207e8c772128f95c800392342727fe1b70d3d05dd9bd826cd3f4e19f3  model/config.json
21ecd0699e5ba6a1b53e0811fd74ca4e11a31382ea22c05f7175f6bc56191305  model/post_config.json
19e7dd411f5c89b7f30fbb1a400819a36962c1c3d5f69483912f921e538b9c97  model/qwen3_post.axmodel
8f29acf519434862d95613b2b4f6b9d14933a5e4d16baebf8ac0b33b410acfb6  model/model.embed_tokens.weight.bfloat16.bin
46fafa42f69d10f67677adffd3ca6285e0c97b7deddfebaa98ceeac3557f04a3  model/qwen3_tokenizer.txt
74b6a2a89c6be0967b246234144f9d88866c386d7bd9d76eff62aeed5a89a5bb  model/qwen3_p128_l0_together.axmodel
9e94f24f4e39ffd1586c83b55c58916507957e365926288439a383bb935a19e9  model/qwen3_p128_l1_together.axmodel
2597d2cb29e4ed0ee7dc6e001b9f9caa4f637e883705427f680d263f631b8da3  model/qwen3_p128_l2_together.axmodel
daedb995d1599fa03225ef1ddbaceb3d2d01586b7c563b040010cdbb5893cfbc  model/qwen3_p128_l3_together.axmodel
c0c3d8ce0cc3a28f2c823df57e9cef6ed7764fbcad2b55c89c8ce59824ebc594  model/qwen3_p128_l4_together.axmodel
02d9e24b52a0525f846aee2e070f5b602a0e3c4f8752f55732491f578392c36d  model/qwen3_p128_l5_together.axmodel
e518f19a37dcc48e5e261a62fbd52c7dc229906e339f3ecb1f860eec6972d101  model/qwen3_p128_l6_together.axmodel
5c3579b4ad940ff4b22f42f998294b2488d9c90b45eab17ed396787977d1b881  model/qwen3_p128_l7_together.axmodel
6661495e78d506790da55d53966094f95f5d2c0b179d9c60f522b30a46382072  model/qwen3_p128_l8_together.axmodel
c244fb27581ebb2d841c311aa5d5e042fde4bc85b34fa9afedbb4f5344c6bd78  model/qwen3_p128_l9_together.axmodel
c69b7d74ed4b28e8b7bca091d10bd7763f865150d54c9693304944a2dcbb9af9  model/qwen3_p128_l10_together.axmodel
20881ac92e3ff7470604fe881a930870b9ff59fb0caf8d0990dfb6f51cb19ac5  model/qwen3_p128_l11_together.axmodel
659543c64898710d31e6ad49cedd35de445cf44cf757cdada3bd383e6314ce1a  model/qwen3_p128_l12_together.axmodel
1012a416b95abc4ec94e58932e80bbc04e6f508ae6e9b60716e6b3f9fab9dfb5  model/qwen3_p128_l13_together.axmodel
ebe9ff00a100e9121a7c2db763fc6c6a7d7cee65252685b3b1fe0462a7be6c1e  model/qwen3_p128_l14_together.axmodel
9b8b91ca5d9d242e0c79fe87ce38b738e0d98901a55303e99d3ae2fc8ed7ee9a  model/qwen3_p128_l15_together.axmodel
dfe3a9f0b328f70c4ea8ae08addc49e85286463c232ed01425960efd4c32346d  model/qwen3_p128_l16_together.axmodel
f70a45768b846f6c555f6174a6c048714c240914916bee61980cf7eadd1af38c  model/qwen3_p128_l17_together.axmodel
beadfba9abd8afcbf55324a7c2f9c99b9d78080cfe45253df902bd18763fdfec  model/qwen3_p128_l18_together.axmodel
2b5a005c1941518cf6c4b10ca768559d34158fc4cd5fd916b4d77786e3cc23a2  model/qwen3_p128_l19_together.axmodel
878519ae4df977e581bd2f891a6b354efc029940f6d90127605b8f5fab13df51  model/qwen3_p128_l20_together.axmodel
856f46a5a2b34dab3efe2ab6d668b5ed2280d3bf2fcc4489c8d9ad35e2238984  model/qwen3_p128_l21_together.axmodel
f6c9d9352119a25526b0b85ba96d01a8ce86df12c4a0f975951e305814aa97af  model/qwen3_p128_l22_together.axmodel
51a0e2de815f8bf1de7e96b71ef2f526b323a8da7bc5f1b863795ad56618507e  model/qwen3_p128_l23_together.axmodel
9e95e155a58334efcbd5c4f722e4e2b8e56610638b838bab9578a389a19ca489  model/qwen3_p128_l24_together.axmodel
8e5c77790652844e3b745e25bebf1bfcc58a699a14ee4ef66987ed4ea38635cd  model/qwen3_p128_l25_together.axmodel
2a22db9e912a6baa891aa30e3d2f31b87f21c7deac026dab41d00d7da49a5e4a  model/qwen3_p128_l26_together.axmodel
06e90bce112df42c0a92574a878e0d5f83b11dcdc5fa9ba494a0d6deb80e706b  model/qwen3_p128_l27_together.axmodel
SHA256
```

</details>

全部显示 `OK` 后启动。校验不符的文件先移出模型目录，再重新下载，不混用其他 revision 的分片。

## 启动单卡服务

先检查端口，第一条命令应没有输出；如果显示已有监听，先核对现有服务，不继续启动。后续命令在同一终端执行，保留 `SERVER_PID`。

```bash
ss -ltn | grep ':8000 ' || true
AXLLM_DEVICES=0 "$AXLLM" serve "$MODEL_DIR" --port 8000 >server.log 2>&1 </dev/null &
SERVER_PID=$!
echo "$SERVER_PID" >server.pid
```

本版本默认监听所有网络接口，本例仅通过回环地址调用；在可信局域网内使用，接入外网前另行配置认证与访问控制。

## 等待就绪并发送问题

客户端显式绕过代理，避免本机请求被转发到下载代理。加载期间自动等待；失败时查看 `server.log`。

```bash
python3 - <<'PY'
import json,time,urllib.request
from pathlib import Path
base='http://127.0.0.1:8000'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for i in range(180):
 try:
  with opener.open(base+'/v1/models',timeout=3) as r:models=json.load(r)
  break
 except (OSError,ValueError):time.sleep(1)
else:raise SystemExit('服务未就绪，请检查 server.log')
model=models['data'][0]['id'];assert model=='AXERA-TECH/Qwen3-0.6B'
print('MODEL',model,flush=True)
payload={'model':model,'messages':[{'role':'user','content':'请用一句话说明 PCIe 的用途。'}],'max_tokens':128,'temperature':0,'enable_thinking':False,'stream':False}
request=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
start=time.monotonic()
with opener.open(request,timeout=180) as r:
 assert r.status==200
 result=json.load(r)
content=result['choices'][0]['message']['content'];assert content.strip()
Path('response.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
Path('request.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
print('REPLY',content,flush=True)
print('HTTP_SECONDS',round(time.monotonic()-start,3),flush=True)
print('FINISH_REASON',result['choices'][0].get('finish_reason'),flush=True)
PY
```

应得到非空中文回答。`request.json` 和 `response.json` 分别保存本次请求和完整响应。若 `FINISH_REASON` 为 `length`，回答可能被 token 上限截断，需缩短问题或按容量调整上限后重新检查。

## 查看部署效果

固定问题为“请用一句话说明 PCIe 的用途。”，本次实际回答：

```text
PCIe 是一种用于高速数据传输的接口标准，广泛应用于计算机、服务器和存储设备等系统中。
```

模型列表与聊天请求均返回 HTTP 200，回复完整且与 PCIe 用途相关，结束原因为 `stop`。首次请求的客户端耗时约 4.309 秒，不包含服务启动和模型加载。

本页验证单次非流式中文问答，不将结果扩展为流式、多模态、向量接口、并发或长对话的验证结论。

## 停止服务并确认释放

在启动服务的同一终端执行，只停止本页记录的 PID：

```bash
kill -TERM "$SERVER_PID"
wait "$SERVER_PID" || true
if curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
  echo STILL_LISTENING
else
  echo SERVER_STOPPED
fi
/usr/bin/axcl/axcl-smi
```

本次停止后显示 `SERVER_STOPPED`，8000 端口不可访问，算力卡无残留推理进程，CMM 回到空闲基线 18 MiB。检查的是程序停止与资源释放，不是长期稳定性测试。

## 更换模型或接入其他应用

保持服务端与客户端的模型 ID 一致，从 `/v1/models` 读取实际名称。其他应用可按相同 JSON 格式调用 `/v1/chat/completions`。模型的容量、上下文和媒体输入必须按[对应部署指南](../models/catalog.mdx)核对。

服务无法启动时先阅读 `server.log`，检查文件校验、AXCL 后端、端口和可用 CMM。保留运行时内存预检，不关闭检查强行加载。
