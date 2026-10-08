---
title: "获取六路推流项目与准备程序"
sidebar_label: "2. 获取项目与准备程序"
pagination_prev: ax650n/applications/six-streams/prepare
pagination_next: ax650n/applications/six-streams/usage
---

# 获取项目与准备程序

在 RK3576 上完成源码下载、资源校验和运行库检查，再启动推流。下列命令使用新的项目目录；已有同名目录时，先保留原项目并选择其他目录，不要覆盖配置或录像。

## 下载指定版本

```bash
cd ~
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/dshanpi/ax8850-multistream-demo.git
cd ~/ax8850-multistream-demo
git lfs install --local
GIT_LFS_SKIP_SMUDGE=1 git checkout --detach 2aa772bbf16b8a904ee6ca57877c0e602208bf49
git lfs pull
git rev-parse HEAD
```

最后输出应与上面的提交号一致。模型、视频及预编译程序使用 Git LFS 保存，仅下载源码 ZIP 或跳过 LFS 会留下指针文件，不能运行演示。

网络需要代理时，使用当前网络可访问的代理地址。以下命令只对本次下载生效；示例 `192.168.1.38:7897` 需要替换为实际地址。

```bash
git -c http.proxy=http://192.168.1.38:7897 \
  -c lfs.concurrenttransfers=2 lfs pull
```

## 校验模型与视频

```bash
cd ~/ax8850-multistream-demo
python3 tools/verify_assets.py
```

应看到 11 项资源校验通过且命令退出码为 0，覆盖 5 个模型和 6 个视频。脚本检查大小和 SHA256，不包含程序动态库或硬件运行验证。出现失败时先重新下载资源，不要继续启动。

## 选择运行程序

### 使用预编译程序

RK3576 的 `aarch64` 系统可先使用 `prebuilt/linux-aarch64/`。该程序依赖 OpenCV 4.6，对应的共享库后缀为 `.so.406`。检查程序、SDK 和插件依赖：

```bash
cd ~/ax8850-multistream-demo
RUNTIME="$PWD/prebuilt/linux-aarch64"
chmod +x "$RUNTIME/bin/six_app"
for f in "$RUNTIME"/bin/* "$RUNTIME"/lib/*.so "$RUNTIME"/lib/plugins/*.so; do
  LD_LIBRARY_PATH="$RUNTIME/lib:/usr/lib/axcl" ldd "$f"
done
```

全部输出应无 `not found`。其他 OpenCV ABI 版本不能通过随意创建软链接替代，应安装匹配依赖或使用下方源码构建。

### 从源码构建

需要适配本机依赖或修改程序时，在同一项目目录执行：

```bash
bash build.sh
ls build/install/bin/six_app
ls build/install/lib/libax_video_sdk.so
ls build/install/lib/plugins/
```

构建默认使用 2 个并行任务；主机内存紧张时可使用 `JOBS=1 bash build.sh`。AXCL 不在 `/usr` 时，按实际 SDK 根目录设置 `AXCL_ROOT`。项目依赖源码已放在 `vendor/`，不需要下载另一份旧工程。

`run.sh` 优先使用可执行的 `build/install/bin/six_app`，未构建时使用 `prebuilt/linux-aarch64/`。检查依赖时也应将 `RUNTIME` 改为实际使用的 `build/install`。

## 生成配置并检查路径

以下命令以预编译程序为例；使用构建产物时，将运行目录替换为 `$PWD/build/install`。

```bash
python3 tools/prepare_config.py \
  --config configs/six.json \
  --runtime "$PWD/prebuilt/linux-aarch64" \
  --output run/config-check.json
```

成功后输出 `run/config-check.json` 的路径。脚本检查六路名称、输入和模型文件、插件路径及 LFS 指针，并生成绝对路径配置。该步骤通过后继续[启动并检查](usage.md)；配置通过不代表模型已在算力卡上运行。
