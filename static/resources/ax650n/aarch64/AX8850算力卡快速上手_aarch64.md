# AX8850 算力卡快速上手

aarch64 主机　Ubuntu / Debian　8GB 与 16GB 版本

按以下6步完成主机安装、PAC部署和运行检查。适用于已完成出厂配置的算力卡。

**所有命令均在主机的 Linux 终端或 SSH 中执行。** 首次安装先不接卡，完成软件和PAC部署后再断电接卡。每一步确认无报错后，再继续操作。

## 1 准备安装文件

按卡容量进入下载目录，选择文件名含 **aarch64**、后缀为 **.deb** 的安装包。

| 卡容量 | 安装包下载入口 |
|---|---|
| 8GB | [打开 8GB 下载目录](https://huggingface.co/AXERA-TECH/AXCL/tree/main/V3.16.0_8G) |
| 16GB | [打开 16GB 下载目录](https://huggingface.co/AXERA-TECH/AXCL/tree/main/V3.16.0_16G) |

在主机创建工作目录：

```sh
mkdir -p ~/axcl-setup
cd ~/axcl-setup
```

将安装包和**随卡提供的配套 PAC**上传到该目录，分别命名为 `axcl-aarch64.deb` 和 `card-runtime.pac`，以便直接使用下方命令。8GB与16GB的PAC不能混用；安装包自带的默认PAC不一定匹配本卡。

## 2 安装依赖与内核头

```sh
uname -m
uname -r
sudo apt update
sudo apt install -y build-essential patch kmod udev pciutils \
  libssl-dev bc flex bison libelf-dev
sudo apt install -y "linux-headers-$(uname -r)"
```

`uname -m` 应输出 `aarch64`。若找不到 headers 包，向开发板系统提供方获取与 `uname -r` **完全匹配**的包，放入当前目录并命名为 `kernel-headers.deb`，然后执行：

```sh
sudo apt install -y ./kernel-headers.deb
```

执行以下命令，确认输出的内核版本与 `uname -r` 一致，再继续安装驱动：

```sh
grep UTS_RELEASE \
  "/lib/modules/$(uname -r)/build/include/generated/utsrelease.h"
```

## 3 安装 AXCL 主机软件

```sh
cd ~/axcl-setup
sudo apt install -y ./axcl_host_aarch64*.deb
dpkg-query -W -f='${Status} ${Version}\n' axclhost
modinfo -F vermagic axcl_host
```

**成功标志**：软件包状态为 **install ok installed**，模块信息中的内核版本与 `uname -r` 一致。安装包已提供主机驱动、运行库和工具，无需另行复制SDK中的 `.ko` 文件。

## 4 部署配套 PAC

![PAC加载流程](images/pac-flow.png)

将随卡提供的 `card-runtime.pac` 复制到主机指定目录即可，无需解包或烧录。驱动会在启动卡时自动加载。

复制配套PAC：

```sh
cd ~/axcl-setup
sudo cp ax650_card*.pac /lib/firmware/axcl/ax650_card.pac
sudo sync
```

检查复制结果：

```sh
cmp ax650_card*.pac /lib/firmware/axcl/ax650_card.pac
```

**成功标志**：cmp没有输出且没有报错，表示两个文件相同。目标文件名必须为 **ax650_card.pac**。复制或检查报错时，先处理再继续。

首次安装继续第5步，断电接卡后开机；已在使用的卡更新PAC后，停止相关应用并执行 `sudo reboot`。后续开机无需重复复制，重新安装或升级AXCL包后需重新部署配套PAC。

## 5 接卡启动并检查状态

```sh
sudo poweroff
```

等待主机关机后**断电**，插好AX8850卡，固定散热片并接好风扇，再一起上电。进入主机Linux后执行：

```sh
lspci -nn | grep -iE 'axera|1f4b:0650'
sudo /usr/bin/axcl/axcl-smi
```

**成功标志**：能够发现PCIe设备，axcl-smi显示卡、温度和CMM信息，且没有 `init fail` 或 `no device connected`。此时可继续运行模型。

![设备状态检查](images/smi-check.png)

8GB实测输出节选，仅保留关键字段。当前配套PAC的CMM总量参考：**8GB为7040MiB，16GB为15232MiB**；温度和已用内存随运行变化。

## 6 运行模型验证

从应用提供方获取AX650 / AXCL兼容的 `.axmodel`，放入 `~/axcl-setup` 并命名为 `model.axmodel`。

```sh
cd ~/axcl-setup
sudo /usr/bin/axcl/axcl_run_model -m ./model.axmodel -r 10
echo $?
```

**成功标志**：程序输出推理时间，退出码为 **0**。这表示模型基本运行通过，业务效果仍需使用实际输入验证；ONNX等文件不能直接代替 `.axmodel`。

### 常见问题

**安装失败**：运行 `sudo tail -n 80 /var/log/axclhost-install.log` 查看原因，优先核对headers和依赖。

**PCIe有卡但SMI无设备**：核对配套PAC和SHA256，保存 `sudo dmesg` 输出并提供给供货方。卡端未启动时，不要反复查询SMI。

运行期间保持风扇工作，禁止带电插拔。升级主机内核后，重新匹配headers和驱动。[原厂文档](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_setup.html)
