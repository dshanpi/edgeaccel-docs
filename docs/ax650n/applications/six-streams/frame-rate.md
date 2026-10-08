---
title: "更换六路推流视频与模型配置"
sidebar_label: "7. 更换视频与配置"
pagination_prev: usage/services
pagination_next: ax650n/applications/six-streams/inference
---

# 更换视频与配置

先完成默认资源的部署验收，再修改 `configs/six.json`。保留六路结构，每次修改后重新检查单路和总览。

## 停止并备份配置

```bash
cd ~/ax8850-multistream-demo
bash stop.sh
cp configs/six.json configs/six.json.bak
```

备份文件已存在时，使用新的文件名保留上一版本。输入视频建议另存新文件，不覆盖仓库资源，以便继续使用原始资源校验和回退。

## 准备输入视频

项目默认输入为 1920×1080 H.264。先查看新文件编码、分辨率、平均帧率和时长：

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,avg_frame_rate:format=duration \
  -of default=noprint_wrappers=1 videos/new-input.mp4
```

需要统一尺寸与帧率时，可将新文件转换为 1080p、30 FPS：

```bash
ffmpeg -i videos/new-input.mp4 -an \
  -vf 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30' \
  -c:v libx264 -pix_fmt yuv420p videos/custom-1080p.mp4
```

转换可能耗时较长，可在电脑完成后复制到开发板。输出文件名应与输入不同。默认第 3、4 路使用半速视频；需要改变播放速度时应重新处理视频时间戳，仅修改 `source_fps` 不能替代半速文件转换。

## 修改对应通道

编辑 `configs/six.json` 中目标通道，保持六个 `name` 唯一。

| 字段 | 修改要求 |
|---|---|
| `input` | 新视频路径；相对路径以项目根目录为基准 |
| `source_fps` | 与实际输入平均帧率一致，必须大于 0；例如 `30000/1001` 对应约 `29.97003` |
| `model` | 与任务匹配的 AX8850 模型 |
| `plugin` | 检测模型对应的后处理插件 |
| `plugin_options.model_path` | 存在此字段时，随 `model` 同步修改 |
| `source_loop_us` | 计数通道的视频循环周期，单位微秒；更换视频后同步核对 |

默认 `pcd` 使用 PCD 插件，`vehicle` 和 `count` 使用 YOLOv8 split 插件，`driving` 使用 YOLO26 插件；分割和深度由应用内对应逻辑处理。模型输入输出结构必须与处理代码匹配，不能仅靠更换文件名接入任意模型。

`driving` 默认由应用层完成跟踪，通道 `enable_tracking` 为 `true`，插件选项中的跟踪为 `false`。修改时保持两层职责一致，避免重复跟踪。计数通道的 `line_x` 和 `deadband` 也应根据新画面设置。

## 检查并重新启动

下例使用预编译程序；若已构建源码，将运行目录改为 `$PWD/build/install`。

```bash
python3 tools/prepare_config.py --config configs/six.json \
  --runtime "$PWD/prebuilt/linux-aarch64" --output run/config-check.json
bash start.sh
```

配置生成成功后再启动；重新完成[效果与验收](validation.md)。更换模型需要同时检查推理计数和实际标注，不能仅检查视频仍能播放。

## 回退

```bash
bash stop.sh
cp configs/six.json.bak configs/six.json
bash start.sh
```

确认原配置恢复后再清理自定义资源，避免删除仍被配置引用的文件。
