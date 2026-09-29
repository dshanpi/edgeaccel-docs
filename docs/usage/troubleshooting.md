---
title: "按故障现象定位问题"
---

# 按故障现象定位问题

从最先失败的一层开始检查。PCIe 尚未枚举时，不通过反复加载大模型验证连接。

| 现象 | 检查与处理 | 恢复后确认 |
|---|---|---|
| `lspci` 找不到卡 | 断电检查插槽 PCIe 能力、接触、转接板和供电 | 设备能够枚举 |
| 驱动编译失败 | 核对 headers、内核版本、编译器及安装日志 | 模块 vermagic 与运行内核一致 |
| 模块存在但加载失败 | 检查内核日志和主机 Secure Boot 状态 | 模块可加载，日志无初始化错误 |
| PCIe 存在但 SMI 无卡 | 核对容量与配套 PAC、AXCL 版本、启动日志 | SMI 列出设备及 CMM |
| SMI 长时间不返回 | 中断查询，保存日志，停止重复查询；排查卡端启动 | 恢复后单次查询正常返回 |
| `device ... is dead` / 心跳超时 | 停止后续推理，保存应用日志与主机内核日志，再按[设备恢复步骤](maintenance.md#恢复失去响应的设备)处理 | SMI 正常返回，固定小模型完成实际推理 |
| `Exec format error` | 程序架构与主机不一致 | `file` 显示对应架构 |
| 库 `not found` | 检查 AXCL 与应用依赖安装路径、架构 | `ldd` 不再缺库 |
| 模型格式不支持 | 核对 AX650 目标、编译版本和运行时 | 配套模型能加载 |
| CMM 不足 | 停止旧服务，减小模型、上下文或路数 | 资源满足且可正常释放 |
| 推理有输出但结果错误 | 核对模型、预处理、后处理、类别字典与版本 | 固定样例与参考结果一致 |
| 视频卡顿但 NPU 空闲 | 分段测量取流、解码、拷贝、CPU 和输出 | 端到端指标恢复 |
| `Port ... is unavailable` | 检查监听进程；为新模型选择独立端口，同时更新客户端 URL | health 接口成功后再发送推理请求 |
| 文本乱码或重复 | 核对 tokenizer、配置、量化文件与已知限制 | 短问答及多轮结果正确 |

## 区分主机内存与卡端内存

`axcl-smi` 的 CMM 表示卡端可供模型等任务使用的内存。RK3576 的 `MemAvailable`、CMA 和驱动内存分配属于主机侧，换用更大容量的算力卡不会增加主机内存。

确认卡端容量不足后，可缩短上下文、选择更小的量化版本，或使用 16GB 卡并核对配套 PAC。检查主机内存时，结合 `free -h`、应用占用与内核日志判断；主机空闲内存与卡端 CMM 不能相互替代。

## 收集定位资料

在 Linux 主机执行。日志可能包含主机名或业务信息，提交前按需要脱敏。

```bash
mkdir -p ~/edgeaccel/logs/support
uname -a > ~/edgeaccel/logs/support/kernel.txt
cat /etc/os-release > ~/edgeaccel/logs/support/os.txt
lspci -nn > ~/edgeaccel/logs/support/pci.txt
dpkg-query -W axclhost > ~/edgeaccel/logs/support/axcl.txt
sudo dmesg > ~/edgeaccel/logs/support/dmesg.txt
sudo tail -n 200 /var/log/axclhost-install.log \
  > ~/edgeaccel/logs/support/install-tail.txt
```

如果没有该安装日志文件，说明安装方式或日志路径不同，应按实际软件包说明收集。另附卡型号与容量、PAC 校验值、模型来源、程序版本、完整命令、退出码及最小复现输入。不要提交账号密码。

## 避免扩大故障范围

服务的 `/health` 成功只表示接口就绪，还需发送一次固定输入，检查实际输出内容。发生设备错误或请求持续超时时，先停止后续推理，保留应用日志与内核日志。

设备恢复、重启或回退按[维护流程](maintenance.md)进行。文件仍在写入时不要直接断电。PCIe 问题应按所用 AXCL 版本的说明逐项定位，不默认通过禁用 IOMMU 处理。

依据：[AXCL FAQ](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_faq.html)。
