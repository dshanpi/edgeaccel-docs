## 准备图文检索运行程序

本例在 RK3576 主机通过 AXCL 使用 AX8850 16GB M.2 算力卡，将图片和文本转换成 2048 维向量，再用余弦相似度检索图片。使用 Linux ARM64、AXCL 3.16.0，以及本页固定版本的 2B 权重。

下载[配套运行包](/examples/qwen3-vl-embedding-20261001.tar.gz)，保存到主机的 `~/edgeaccel`。包内包含运行程序、固定源码与适配文件、三张样图、检索示例和模型校验工具。保留前文下载模型后设置的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3-vl-embedding-20261001.tar.gz
sudo apt-get install -y libopencv-dev
chmod +x qwen3-vl-embedding/bin/axllm
ldd qwen3-vl-embedding/bin/axllm
python3 qwen3-vl-embedding/verify_models.py --model-dir "$MODEL_DIR"
```

`ldd` 应找到全部动态库，模型校验应输出 `Verified 33 model files`。模型及配套文件约 3.3 GB，可把 `MODEL_DIR` 指向已挂载的存储卡。运行程序基于官方 AX-LLM 提交 `a51df2d43b3ec1c49b30792bbe4fad5a964231ea`，包含 AXCL 设备与两组形状 K/V 缓冲区适配。

## 启动图文向量服务

```bash
cd ~/edgeaccel
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  ./qwen3-vl-embedding/bin/axllm serve "$MODEL_DIR" --port 3611
```

保持该终端运行。在 RK3576 的另一个终端检查接口：

```bash
curl --noproxy '*' --fail http://127.0.0.1:3611/health
curl --noproxy '*' --fail http://127.0.0.1:3611/v1/models
```

模型列表应包含 `AXERA-TECH/Qwen3-VL-Embedding-2B`。首次启动需要加载模型；出现服务就绪信息后再发送请求。使用结束后，在服务终端按 `Ctrl+C` 释放模型。

## 运行中英文图片检索

以下命令在运行服务的同一台 RK3576 上执行。图片路径由服务端读取，应使用主机上存在的文件。

```bash
cd ~/edgeaccel
python3 qwen3-vl-embedding/retrieval_demo.py \
  --images "$HOME/edgeaccel/qwen3-vl-embedding/images" \
  --api http://127.0.0.1:3611 \
  --output "$HOME/edgeaccel/results/qwen3-vl-embedding/retrieval-result.json"
```

程序依次编码鸟、猫、狗三张图片，再发送 `a bird`、`a cat`、`a dog`、`一只鸟`、`一只猫`、`一只狗` 六个查询。终端按相似度从高到低列出图片，JSON 保存原始输入、2048 维向量、请求耗时和排序。

该示例使用 `messages` 接口，每次编码一个输入，统一指令为 `Represent the user's input.`。分词器使用仓库内的 `qwen3_tokenizer.txt`；运行程序在序列末尾添加 EOS，取最后一个位置的特征并作 L2 归一化。余弦相似度用于比较相关性，不是分类概率。

使用自己的图片时，修改示例中的图片文件名与查询文本，保持图片和文本的指令一致。图文联合输入可在同一条用户消息的 `content` 中同时放入 `image_url` 和 `text`。同一图片的后续请求可能使用视觉特征缓存，不能直接与首次编码耗时比较。

<details>
<summary>重新编译运行程序</summary>

若系统动态库与预编译程序不匹配，使用包内固定源码重新编译：

```bash
sudo apt-get install -y build-essential cmake libopencv-dev
cd ~/edgeaccel/qwen3-vl-embedding
mkdir source
tar -xzf official-source.tar.gz -C source
cp -r adapted/src/. source/src/
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_AX650=OFF -DBUILD_AXCL=ON
cmake --build build --target axllm -j1
```

后续命令改用 `build/axllm`。固定源码包已包含对应版本子模块。

</details>
