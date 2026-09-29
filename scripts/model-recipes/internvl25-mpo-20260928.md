## 编译 ARM64 推理程序

本页使用 **RK3576 + AX8850 16GB M.2**。固定模型仓库提供芯片主机程序；在 RK3576 上从官方 AXCL 分支源码编译下面的版本，通过 PCIe 调用 M.2 算力卡。

在 RK3576 主机终端执行。首次构建使用一个新的源码目录：

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake git libopencv-dev libspdlog-dev
RUNTIME_DIR=~/edgeaccel/runtime/internvl3-72ada011
git clone --filter=blob:none --no-checkout https://github.com/AXERA-TECH/ax-llm.git "$RUNTIME_DIR"
git -C "$RUNTIME_DIR" checkout --detach 72ada011e58fc0015578e6b9b5fd6b4674e26429
cmake -S "$RUNTIME_DIR" -B "$RUNTIME_DIR/build" \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_WITH_YOLOV5_TEST=OFF
cmake --build "$RUNTIME_DIR/build" --target main -j1
ldd "$RUNTIME_DIR/build/main"
"$RUNTIME_DIR/build/main" --help
```

编译产物为 `build/main`，依赖检查不能出现 `not found`。此版本使用 HTTP 分词服务，参数名为 `--url_tokenizer_model`。后续提交已更改分词方式，复现本页结果时保留上述提交号。

本页构建环境使用 OpenCV 4.6.0。若找不到 AXCL 头文件或库，先完成驱动与开发包安装，再重新配置 CMake。

## 准备分词服务

在下载模型的终端中执行：

```bash
python3 -m venv ~/edgeaccel/internvl25-mpo-env
source ~/edgeaccel/internvl25-mpo-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
python - <<'PY'
import json
from pathlib import Path
t = Path('internvl2_5_tokenizer_448.py')
original = t.read_text()
old = 'prompt += "<|im_end|>\\n<|im_start|>assistant"'
new = 'prompt += "<|im_end|>\\n<|im_start|>assistant\\n"'
if old in original:
    assert original.count(old) == 1
    t.with_suffix('.py.upstream').write_text(original)
    t.write_text(original.replace(old, new))
else:
    assert new in original, '请确认使用本页固定版本的分词脚本'
p = Path('post_config.json')
backup = p.with_suffix('.json.upstream')
if not backup.exists():
    backup.write_bytes(p.read_bytes())
config = json.loads(p.read_text())
config.update(enable_temperature=False, enable_repetition_penalty=False,
              enable_top_p_sampling=False, enable_top_k_sampling=True, top_k=1)
p.write_text(json.dumps(config, indent=2) + '\n')
PY
python internvl2_5_tokenizer_448.py --host 127.0.0.1 --port 12345
```

看到 `http://127.0.0.1:12345` 后保持服务运行。上方补齐 `assistant` 后的换行，与配套 `tokenizer_config.json` 中的聊天模板保持一致。每题输入一张图片，编码尺寸为 448×448。样例采用贪心采样，与仓库默认随机采样配置不同。

## 运行图像问答

在另一终端设置目录并定义命令：

```bash
MODEL_DIR=~/edgeaccel/models/internvl2-5-1b-mpo/f0f00da263a7
RUNTIME_DIR=~/edgeaccel/runtime/internvl3-72ada011
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"

run_question() {
  printf '%s\n%s\nq\n' "$1" image1.jpg | "$RUNTIME_DIR/build/main" \
    --template_filename_axmodel './internvl2_5_1b_448_ax650/qwen2_p128_l%d_together.axmodel' \
    --axmodel_num 24 \
    --filename_image_encoder_axmodedl ./internvl2_5_1b_448_ax650/internvl2_5_1b_mpo_vit.axmodel \
    --use_mmap_load_embed 1 --url_tokenizer_model http://127.0.0.1:12345 \
    --filename_post_axmodel ./internvl2_5_1b_448_ax650/qwen2_post.axmodel \
    --filename_tokens_embed ./internvl2_5_1b_448_ax650/model.embed_tokens.weight.bfloat16.bin \
    --tokens_embed_num 151674 --tokens_embed_size 896 --devices 0 --live_print 0
}

run_question 'What animal is in the image? Answer in one short sentence.'
run_question 'What colors are the animal’s face and ears?'
run_question 'What is supporting the animal’s head?'
run_question '请用一句中文描述图片中的动物。'
```

程序从标准输入依次读取问题、图片路径和退出指令 `q`。此版本没有 `--prompt` 或 `--image` 参数。参数 `filename_image_encoder_axmodedl` 的拼写来自官方接口，照原样使用。

每题独立启动，运行结束后退出。`--live_print 0` 在生成结束后显示完整回复；内部首 token 计时不能解释为客户端首次看到文字的等待时间。

## 检查图片与回复

对照原图检查小熊猫类别、面部与耳朵颜色、头部与木板的位置关系，保留模型原文，不能把补充猜测视为图片中的事实。程序应产生回复并出现 `hit eos`；退出后用 `axcl-smi` 确认模型进程已释放。

本页只有一张图片的四次单轮问答，不代表完整数据集、视频、多图或长上下文评测。结束使用后，在分词服务终端按 `Ctrl+C`；恢复默认采样时，将 `post_config.json.upstream` 复制回 `post_config.json`。
