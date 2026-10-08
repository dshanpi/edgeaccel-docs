import fs from 'node:fs';
import path from 'node:path';

const asset = item => '../../../static' + item.path.split('/').map(encodeURIComponent).join('/');
// Dates stay in evidence files; remove calendar annotations only from editorial observations.
const observation = text => text.replace(/(?:\d{4}-\d{2}-\d{2})[，、 ]*/g, '');
const label = text => text.replaceAll('[', '\\[').replaceAll(']', '\\]');
const code = text => {
  const fence = '`'.repeat(Math.max(2, ...(text.match(/`+/g) ?? []).map(value => value.length)) + 1);
  return `\n${fence}text\n${text.trim()}\n${fence}\n`;
};
const tableCell = value => String(value ?? '—').replaceAll('|', '\\|').replaceAll('\n', ' ');
const table = (headers, rows) => `| ${headers.map(tableCell).join(' | ')} |\n| ${headers.map(() => '---').join(' | ')} |\n${rows.map(row => '| ' + row.map(tableCell).join(' | ') + ' |').join('\n')}\n`;

const summaries = {
  'Qwen3-Embedding-0.6B': '每批 4 条英文短句得到 4 个 1024 维向量。相同文本的余弦相似度为 1，近义句的相似度高于无关句；两次请求的向量一致。',
  Whisper: '使用 tiny 模型转写下方 4.204 秒中文音频。三次运行的文本一致，开头“擅职”与上游参考“甚至”不同，尚未通过识别质量核对。',
};

const specialNotes = {
  'Qwen3-0.6B': '三次请求包含一次中文问答和两次相同算术题；相同问答合并展示，尚未执行 JSON 问题。样例使用 temperature=0、enable_thinking=false、stream=false、max_tokens=128。',
  'Qwen3-Embedding-0.6B': '只检查了 3 种短英文文本及其中一条重复输入，尚未评估中文、长文本或检索召回率。',
  'FastVLM-1.5B-GPTQ-Int4': '这是一张图片的 3 次请求、2 种问题；第三次重复第一问且回复相同，下方合并展示。尚未测试多图、视频、OCR 或中文视觉问答。',
  Whisper: '原模型卡示例与同音频的 FireRedASR 官方标注存在“停止 / 停滞”差异，单句字符对照请查看上表。尚无独立人工标注集；文件转写未覆盖麦克风采集、长音频分段或流式识别。',
};

function media(run) {
  const images = run.evidence.filter(item => /\.(png|jpe?g|webp|gif)$/i.test(item.path));
  if (!images.length) return '';
  const inputs = images.filter(item => !item.path.includes('/outputs/'));
  const outputs = images.filter(item => item.path.includes('/outputs/'));
  const ordered = [...inputs, ...outputs.filter(item => !item.path.includes('alpha-mask')), ...outputs.filter(item => item.path.includes('alpha-mask'))];
  let text = '\n点击图片可查看原尺寸。\n\n<div className="model-effect-gallery">\n';
  for (const item of ordered) {
    const caption = item.path.includes('alpha-mask') ? '输出的 Alpha 掩码' : item.path.includes('/outputs/') ? '实际输出' : '输入图片';
    text += `\n<figure>\n\n[![${label(caption)}](${asset(item)})](${asset(item)})\n\n<figcaption>${caption}</figcaption>\n</figure>\n`;
  }
  return text + '\n</div>\n';
}

function apiExamples(root, run) {
  const evidence = run.evidence.find(item => item.path.endsWith('/api.json'));
  if (!evidence) return '';
  const api = JSON.parse(fs.readFileSync(path.join(root, 'static', evidence.path), 'utf8'));
  if (api.kind === 'embedding') {
    const request = api.requests.find(item => item.endpoint === '/v1/embeddings');
    const vectors = request.response.data.map(item => item.embedding);
    const cosine = (a, b) => a.reduce((sum, value, i) => sum + value * b[i], 0) / Math.hypot(...a) / Math.hypot(...b);
    return '\n以第一条文本 `' + request.request.input[0] + '` 为查询，对比结果如下：\n\n' + table(['对比文本', '余弦相似度'], request.request.input.slice(1).map((input, i) => [input, cosine(vectors[0], vectors[i + 1]).toFixed(6)])) + '\n相似度用于比较本模型中的文本关系，不能直接解释为百分比准确率。\n';
  }
  const unique = new Map();
  for (const item of api.requests.filter(item => item.endpoint === '/v1/chat/completions')) {
    const key = JSON.stringify(item.request.messages);
    if (!unique.has(key)) unique.set(key, item);
  }
  const samples = [...unique.values()].slice(0, 3);
  const singles = samples.map((item, i) => {
    const content = item.request.messages.at(-1).content;
    const prompt = typeof content === 'string' ? content : content.find(part => part.type === 'text').text;
    const limit = item.request.max_tokens;
    const used = item.response.usage?.completion_tokens;
    const limitNote = limit && used >= limit
      ? `\n本次输出已达到设置的 ${limit} token 上限，下面保留原始回复；不能仅凭接口的 finish_reason 判定句子已完整结束。\n`
      : '';
    return `\n**示例 ${i + 1}：输入**\n${code(prompt)}\n**实际回复**\n${limitNote}${code(item.response.choices[0].message.content)}` + (item.observation ? `\n${item.observation}\n` : '') + apiTiming(item);
  }).join('');
  const conversations = (api.conversations ?? []).map((conversation, index) => {
    const turns = conversation.requestIndices.map((requestIndex, i) => {
      const item = api.requests[requestIndex];
      return `\n**第 ${i + 1} 轮：输入**\n${code(item.request.messages.at(-1).content)}\n**实际回复**\n${code(item.response.choices[0].message.content)}\n${item.observation}\n` + apiTiming(item);
    }).join('');
    return `\n**连续对话 ${index + 1}**\n\n${conversation.observation}\n${turns}`;
  }).join('');
  return singles + conversations;
}

function apiTiming(item) {
  if (!Number.isFinite(item.requestSeconds)) return '';
  const ttft = item.response.usage?.ttft_ms;
  const native = Number.isFinite(ttft) ? `程序内部首 token 耗时：${ttft.toFixed(2)} ms；` : '';
  return `\n${native}完整 API 请求耗时：${item.requestSeconds.toFixed(3)} s。请求在模型加载完成后发出，包含响应传输，不含模型加载。\n`;
}

function textExamples(root, run) {
  const evidence = run.evidence.find(item => item.path.endsWith('/text-result.json'));
  if (!evidence) return '';
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', evidence.path), 'utf8'));
  const singles = result.samples.map((sample, i) => {
    const picture = sample.imagePath ? `\n[![${label('输入图片 · ' + sample.imageFile)}](${asset({path: sample.imagePath})})](${asset({path: sample.imagePath})})\n` : '';
    const frames = sample.framePaths?.length ? '\n按输入顺序查看视频帧：\n\n<div className="model-effect-gallery">\n' + sample.framePaths.map((frame, index) => `\n<figure>\n\n[![输入帧 ${index + 1}](${asset({path: frame})})](${asset({path: frame})})\n\n<figcaption>输入帧 ${index + 1}</figcaption>\n</figure>\n`).join('') + '\n</div>\n' : '';
    const split = sample.output.indexOf('</think>');
    const hasFinal = split >= 0 && sample.output.slice(split + 8).trim().length > 0;
    const reply = hasFinal ? sample.output.slice(split + 8) : sample.output;
    const original = hasFinal ? `\n模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。\n\n<details>\n<summary>查看模型原始完整回复</summary>\n${code(sample.output)}\n</details>\n` : '';
    const imageTiming = Number.isFinite(sample.nativeImageEncodeMs) ? `图像编码：${sample.nativeImageEncodeMs.toFixed(2)} ms；` : '';
    const timings = Number.isFinite(sample.firstContentSeconds) && Number.isFinite(sample.requestSeconds)
      ? `\n客户端首段文字：${sample.firstContentSeconds.toFixed(3)} s；完整流式请求：${sample.requestSeconds.toFixed(3)} s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。\n`
      : Number.isFinite(sample.nativeTtftMs) ? `\n${imageTiming}程序内部首 token 耗时：${sample.nativeTtftMs.toFixed(2)} ms；含模型加载的完整进程：${sample.processSeconds.toFixed(3)} s。内部计时不等同于客户端端到端首字延迟。\n` : Number.isFinite(sample.requestSeconds) ? `\n完整请求耗时：${sample.requestSeconds.toFixed(3)} s。\n` : '';
    const variant = sample.variantLabel ? ` · ${label(sample.variantLabel)}` : '';
    return `\n**示例 ${i + 1}${variant}：输入**\n${picture}${frames}${code(sample.input)}\n**实际回复${hasFinal ? '的最终回答部分' : ''}**\n${code(reply)}\n${sample.observation}\n${timings}${original}`;
  }).join('');
  const conversations = (result.conversations ?? []).map((conversation, index) => {
    const turns = conversation.turns.map((turn, i) =>
      `\n**第 ${i + 1} 轮：输入**\n${code(turn.input)}\n**实际回复**\n${code(turn.output)}\n${turn.observation}\n` +
      (Number.isFinite(turn.nativeTtftMs) ? `\n本轮程序内部首 token 耗时：${turn.nativeTtftMs.toFixed(2)} ms。\n` : '')
    ).join('');
    return `\n**连续对话 ${index + 1}**\n\n以下各轮使用同一个进程和会话，保留上一轮上下文。\n${turns}\n整个对话进程：${conversation.processSeconds.toFixed(3)} s，包含一次模型加载、全部轮次和退出；不代表单轮推理耗时。内部首 token 计时不含模型加载。\n`;
  }).join('');
  return (result.timingNote ? '\n' + result.timingNote + '\n' : '') + singles + conversations;
}

function audioPlayer(item, caption) {
  const url = (process.env.BASE_URL || '/').replace(/\/?$/, '/') + item.path.slice(1);
  return `\n<audio controls preload="metadata" src="${url}" aria-label="${caption}"></audio>\n\n[下载音频](${asset(item)})\n`;
}

function pythonExamples(root, run) {
  const item = run.evidence.find(e => /\/(classification|punctuation)-result\.json$/.test(e.path));
  if (!item) return '';
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', item.path), 'utf8'));
  if (result.kind === 'punctuation') return result.samples.map((sample, i) =>
    `\n**示例 ${i + 1}：无标点输入**\n${code(sample.input)}\n**实际恢复结果**\n${code(sample.output)}`
  ).join('') + '\n以上保留原始标点；句末逗号和不合理断句没有人工修正。\n';
  let text = '\n下面按原始类别编号展示 Top-5。英文标签按 [Torchvision v0.23.0 的 ImageNet 类别表](' + result.labelSource + ') 映射；Softmax 分数不是分类准确率。\n';
  for (const variant of result.variants) {
    text += `\n**${variant.name}**\n\n` + table(['类别编号', 'ImageNet 标签', 'Softmax 分数'], variant.samples[0].top5.map(row => [row.class_id, row.imagenetLabel, row.confidence.toFixed(6)]));
    text += '\n同一输入连续运行 3 次，上表类别和分数一致。\n';
  }
  return text;
}

function birdExamples(root, run) {
  const item = run.evidence.find(e => e.path.endsWith('/bird-result.json'));
  if (!item) return '';
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', item.path), 'utf8'));
  const rows = result.top5.map(row => [row.rank, row.classIndex, row.className.split('_')[0], row.className.split('_').slice(-2).join(' '), row.reportedScore]);
  return '\n下表来自原始运行日志，分数保留日志中的四位小数。输出索引按[本次固定版本类别表](' + result.labelSource + ')从 0 开始计数，与类别名称前缀编号不同。\n\n'
    + table(['排名', '输出索引', '类别编号', '物种名称', '日志分数'], rows)
    + '\n前处理：' + result.preprocessing + '\n\n'
    + result.limitations.join('\n\n') + '\n';
}

function qrExamples(root, run) {
  const item = run.evidence.find(e => e.path.endsWith('/qrcode-result.json'));
  if (!item) return '';
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', item.path), 'utf8'));
  let text = '\n以下 9 个 AX650 权重分别处理同版本仓库内的 48 张图片。统计“至少解码出一个结果”的图片数量，不能解释为检测准确率；一张图可能含多个二维码。\n\n';
  text += table(['编译模型', '完成图片', '检测到区域的图片', '成功解码的图片'], result.variants.map(v => [v.weight.split('/').pop().replace('.axmodel',''), v.batchSummary.images, v.batchSummary.detectedImages, v.batchSummary.decodedImages]));
  text += '\n下面用同一张 640×640 测试二维码复测全部 9 个变体。原始二维码内容与解码记录保留在配套结果文件中。其中 8 个模型完成检测与解码；NanoDet 没有检测到区域，下方保留实际空结果。\n';
  for (const variant of result.variants) {
    const sample = variant.samples.find(s => s.file === 'edgeaccel-qr.png');
    const preview = run.evidence.find(e => e.path.endsWith('/outputs/' + variant.weight.split('/').pop().replace('.axmodel','.jpg')));
    text += '\n**' + variant.weight.split('/').pop().replace('.axmodel','') + ' · edgeaccel-qr.png**\n';
    if (preview) text += `\n[![${label('实际检测框 · ' + variant.weight.split('/').pop())}](${asset(preview)})](${asset(preview)})\n`;
    text += sample.decoded.length ? '\n本次成功解码；[查看原始文字与记录](' + asset(item) + ')。\n' : '\n本次未解码出文字。\n';
  }
  return text + '\n以上标注图均为本次检测框绘制的结果。解码使用主机上的 ZBar；未执行二维码中的链接或内容，也未采用仓库预置效果图。\n';
}

function decisionExamples(root, run) {
  const item = run.evidence.find(e => e.path.endsWith('/decision-result.json'));
  if (!item) return '';
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', item.path), 'utf8'));
  let text = '\n三个检查点分别运行同版本的 sample_request.json，每份输入包含 4 个问题。下表按实际数值展示，未将概率自动转换为业务动作。\n';
  for (const variant of result.variants) {
    text += '\n**' + variant.checkpoint + '：输入状态**\n' + code(typeof variant.request.state === 'string' ? variant.request.state : JSON.stringify(variant.request.state, null, 2));
    text += '\n' + table(['问题', '类型', '实际输出'], Object.entries(variant.response.answers).map(([name, answer]) => [
      variant.request.questions[name].instructions, answer.type,
      answer.type === 'choice' ? `${answer.choice}（${answer.probabilities[answer.choice].toFixed(6)}）` :
      answer.type === 'score' ? `${answer.score.toFixed(6)} / 2；最高概率等级 ${Object.entries(answer.probabilities).sort((a,b) => b[1]-a[1])[0][0]}` : answer.noul.toFixed(6)
    ]));
  }
  text += '\n三组类别及数值与同版本仓库配套输出逐项对照，最大数值差小于 1×10⁻⁶。该对照检验运行结果的可复现性；样例本身包含低置信度判断，使用前仍需确定自己的阈值和人工复核规则。\n';
  return text;
}

function enhancementExamples(root, run) {
  const item = run.evidence.find(e => e.path.endsWith('/enhancement-result.json'));
  if (!item) return '';
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', item.path), 'utf8'));
  let text = '\n以下图片由本次运行生成，点击可查看原尺寸。各算法的输入、模型分辨率和后处理不同，不能直接根据这些样例比较算法优劣。\n';
  for (const variant of result.variants) {
    text += '\n**' + variant.label + '**\n\n' + observation(variant.observation) + '\n';
    text += '\n<div className="model-effect-gallery">\n';
    for (const preview of variant.previews) {
      const evidence = run.evidence.find(e => e.path === preview.path);
      text += `\n<figure>\n\n[![${label(preview.caption)}](${asset(evidence)})](${asset(evidence)})\n\n<figcaption>${preview.caption}</figcaption>\n</figure>\n`;
    }
    text += '\n</div>\n';
  }
  return text;
}

function compiledEmbeddingExamples(root, run) {
  const item = run.evidence.find(e => e.path.endsWith('/embedding-result.json'));
  if (!item) return '';
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', item.path), 'utf8'));
  let text = '\n以下结果由完整 28 层模型与最终归一化层在算力卡上生成。输入均为文字，输出为 1024 维单位向量；相似度是向量的余弦分数，不是准确率或概率。\n';
  for (const example of result.examples) {
    const record = example.record;
    text += `\n### ${example.label}\n\n`;
    text += table(['候选文档', '内容'], record.documents.map((d, i) => [`文档 ${i + 1}`, d]));
    text += '\n' + table(['查询', '文档 1 分数', '文档 2 分数', '首选结果'], record.queries.map((q, i) =>
      [q, ...record.similarities[i].map(v => v.toFixed(6)), `文档 ${record.matches[i].documentIndex + 1}`]));
    text += `\n本次模型加载 ${record.loadSeconds.toFixed(3)} 秒；加载后的单条编码耗时 ${Math.min(...record.samples.map(s => s.seconds)).toFixed(3)}–${Math.max(...record.samples.map(s => s.seconds)).toFixed(3)} 秒。编码耗时包含主机向量查表、数据传输、算力卡推理与归一化，不包含模型加载和分词。\n`;
  }
  text += '\n两组查询均将对应文档排在首位。中文“公共汽车”示例是在已有文字描述中检索答案，没有输入或识别图片。\n';
  text += `\n[下载本次实际向量、检索分数与 CPU 对照](${asset(item)})。这里的固定样例不能代替业务语料上的召回率评估。\n`;
  const qualityItem = run.evidence.find(e => e.path.endsWith('/retrieval-quality.json'));
  if (qualityItem) {
    const q = JSON.parse(fs.readFileSync(path.join(root, 'static', qualityItem.path), 'utf8'));
    text += '\n### 核对中英文与跨语言检索\n\n使用 20 篇候选文档测试 40 个不同查询，内容包含容易混淆的操作条件和中英文改写。语料与相关性标注由助手在推理前编写，不属于公开基准或独立人工标注。额外重复首条查询一次，输出向量逐值一致，重复项不计入命中率。\n';
    text += '\n' + table(['检查项', '实际结果'], [
      ['正确文档排在首位', `${Math.round(q.metrics.hitAt1 * 40)} / 40`],
      ['正确文档进入前三', `${Math.round(q.metrics.hitAt3 * 40)} / 40`],
      ['平均倒数排名（MRR）', q.metrics.mrrAt20.toFixed(4)],
      ['61 个向量与完整 CPU 模型的最低余弦相似度', q.numericalComparison.minCpuCosine.toFixed(6)],
      ['全部检索分数与 CPU 结果的最大差异', q.numericalComparison.maxRetrievalScoreDifference.toFixed(6)],
    ]);
    const misses = q.ranks.filter(r => r.rank > 1);
    if (misses.length) {
      const documents = new Map(q.documents.map(d => [d.id, d.text]));
      text += '\n以下查询的首选结果未命中预先指定的文档，完整结果中保留了该项：\n\n';
      text += table(['查询', '实际首选文档', '预期文档', '预期文档排名'], misses.map(r => [
        r.query, documents.get(r.top3[0].documentId), documents.get(r.relevantDocumentIds[0]), r.rank,
      ]));
    }
    text += `\n[下载全量输入样例](${asset({path:q.inputPath})})，保存到板端 \`$APP_DIR/recipe/bilingual-input.json\` 后，使用前文同一程序复现：\n\n\`\`\`bash\ncd "$APP_DIR/recipe"\npython qwen3_embedding_axcl.py --model-dir "$MODEL_DIR" \\\n  --input-json bilingual-input.json --output-dir "$APP_DIR/result-bilingual"\n\`\`\`\n`;
    text += `\n[查看全部排名、实际向量和 CPU 对照](${asset(qualityItem)})。本次小型构造语料结果不能替代业务文档和真实查询上的检索评估。\n`;
  }
  const externalItem = run.evidence.find(e => e.path.endsWith('/external-retrieval.json'));
  if (externalItem) {
    const r = JSON.parse(fs.readFileSync(path.join(root, 'static', externalItem.path), 'utf8'));
    text += '\n### 核对外部标注检索样本\n\n采用英文 SciFact 与中文 DuRetrieval 的固定版本，每种语言按查询 ID 顺序选取 16 条。保留全部已标注相关文档，并加入词面相近及按固定哈希顺序选取的候选；以下是缩小候选集后的子集测试，不是完整 BEIR 或 C-MTEB 基准成绩。\n';
    text += '\n长文档按 512 token 分段，相邻段重叠 64 token，保留全部内容；文档得分取最相似分段的余弦分数。标注与查询选择在模型推理前固定，未根据结果剔除样本。\n\n';
    text += table(['数据集', '查询 / 候选文档', '首选命中', 'Recall@3', 'Recall@10', 'NDCG@10'], r.datasets.map(d => [
      `[${d.name === 'scifact' ? 'SciFact' : 'DuRetrieval'}](https://huggingface.co/datasets/${d.repository}/tree/${d.revision})`,
      `${d.queries} / ${d.documents}`, `${Math.round(d.metrics.hitAt1 * d.queries)} / ${d.queries}`,
      d.metrics.recallAt3.toFixed(4), d.metrics.recallAt10.toFixed(4), d.metrics.ndcgAt10.toFixed(4),
    ]));
    text += '\n首选命中表示第一篇文档属于该查询的相关文档。Recall@k 先计算每个查询在前 k 篇中找回的相关文档比例，再取平均；同一查询可能有多篇相关文档。NDCG@10 使用原始相关性等级，增益为 2 的等级次方减 1。未标注候选仅在评分时按 0 处理，不表示经过人工确认的不相关文档。\n';
    text += `\n本次 ${r.cases.length} 条分段与查询输入的实际向量，均与原始完整 28 层 CPU 模型核对：最低余弦相似度 ${r.minCpuCosine.toFixed(6)}，文档检索分数最大差异 ${r.maxScoreDifference.toFixed(6)}。执行前后模型文件一致，首条输入在执行开始及结束时复测，输出逐值一致。\n`;
    text += `\n[下载全部排名、向量与对照结果](${asset(externalItem)})。数据来源和固定版本包含在结果中；原始语料请从对应数据集获取。\n`;
  }
  return text;
}

function deploymentExamples(root, run) {
  const item = run.evidence.find(e => e.path.endsWith('/deployment-result.json'));
  if (!item) return '';
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', item.path), 'utf8'));
  let text = '';
  for (const variant of result.variants) {
    const repeatedObservation = (variant.textSamples ?? []).some(sample => sample.observation === variant.observation);
    text += `\n**${variant.label}**\n${repeatedObservation ? '' : `\n${observation(variant.observation)}\n`}`;
    if (variant.previews.length) {
      text += '\n<div className="model-effect-gallery">\n';
      for (const preview of variant.previews) {
        const evidence = run.evidence.find(e => e.path === preview.path);
        text += `\n<figure>\n\n[![${label(preview.caption)}](${asset(evidence)})](${asset(evidence)})\n\n<figcaption>${preview.caption}</figcaption>\n</figure>\n`;
      }
      text += '\n</div>\n';
    }
    for (const [index, sample] of (variant.textSamples ?? []).entries()) {
      text += `\n**示例 ${index + 1}：输入**\n`;
      for (const picture of sample.images ?? []) {
        const evidence = run.evidence.find(e => e.path === picture.path);
        text += `\n[![${label(picture.caption)}](${asset(evidence)})](${asset(evidence)})\n`;
      }
      text += code(sample.input) + '\n**实际回复**\n' + code(sample.output) + '\n' + sample.observation + '\n';
    }
    for (const view of variant.tables ?? []) text += '\n' + table(view.headers, view.rows);
    for (const audio of variant.audio ?? []) {
      text += `\n${audio.caption}\n` + audioPlayer(run.evidence.find(e => e.path === audio.path), audio.caption);
    }
    for (const video of variant.videos ?? []) {
      const evidence = run.evidence.find(e => e.path === video.path);
      const url = (process.env.BASE_URL || '/').replace(/\/?$/, '/') + evidence.path.slice(1);
      text += `\n${video.caption}\n\n<video className="model-effect-video" controls playsInline preload="metadata" src="${url}" aria-label="${video.caption}"></video>\n\n[下载视频](${asset(evidence)})\n`;
    }
  }
  return text;
}

function audioExamples(root, model, run) {
  const name = {'3D-Speaker': 'speaker-result.json', SenseVoice: 'sensevoice-result.json', MeloTTS: 'tts-result.json'}[model.id];
  if (!name) return '';
  const file = run.evidence.find(item => item.path.endsWith('/' + name));
  if (!file) return '';
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', file.path), 'utf8'));
  const find = name => run.evidence.find(item => item.path.endsWith('/' + name));
  if (model.id === '3D-Speaker') {
    let text = '\n下面使用仓库提供的三段录音；“同一人”和“不同人”按样例文件的分组解释，未独立核验说话人身份。\n';
    for (const [i, input] of result.inputs.entries()) text += `\n**输入 ${i + 1}：${input.file} · ${input.seconds.toFixed(3)} 秒**\n` + audioPlayer(find(input.file), '3D-Speaker 输入 ' + (i + 1));
    const cosine = (a, b) => a.reduce((sum, value, i) => sum + value * b[i], 0) / (Math.hypot(...a) * Math.hypot(...b));
    text += '\n**卡端实际声纹分数**\n\n' + table(['模型', '输出维度', '录音 1 / 2（同组）', '录音 1 / 3（不同组）', '录音 2 / 3（不同组）'], result.models.map(m => [m.model, m.embeddings[0].length, cosine(m.embeddings[0], m.embeddings[1]).toFixed(6), cosine(m.embeddings[0], m.embeddings[2]).toFixed(6), cosine(m.embeddings[1], m.embeddings[2]).toFixed(6)]));
    text += '\n上表由保存的完整卡端向量复算。原始向量不是单位向量，余弦计算除以两者的 L2 范数；每次输入一段录音，不使用文本分词器。样例仅取前 360 帧音频特征，未覆盖整段长音频或重复输入测试。\n';
    text += '\n**使用相同前处理与配套 CPU ONNX 对照**\n\n' + table(['模型', 'AXCL / ONNX 向量相似度（3 段）', 'ONNX 同组 / 不同组'], result.models.map(m => [m.model, m.onnxComparison.embeddingCosine.map(v => v.toFixed(6)).join(' / '), `${m.onnxComparison.sameSpeaker.toFixed(6)} / ${m.onnxComparison.differentSpeaker.toFixed(6)}`]));
    return text + '\nCPU 对照表保留原始运行记录；此前未保存完整 CPU 向量，尚不能独立重算该表。余弦分数越大表示向量越接近，不是准确率。卡端与 ONNX 的差异按实际值保留，不能把两套模型的分数直接套用到同一个业务阈值。\n';
  }
  if (model.id === 'SenseVoice') {
    const languages = {zh: '中文', en: '英文', yue: '粤语', ja: '日语', ko: '韩语'};
    return '\n以下为五段官方样例的实际转写。可播放原音频逐句核对；本次没有独立人工标注稿，未计算字错率或词错率。\n' + result.samples.map(sample => `\n**${languages[sample.language]} · ${sample.audioSeconds.toFixed(3)} 秒**\n` + audioPlayer(find(sample.file), 'SenseVoice ' + languages[sample.language] + '输入') + '\n实际转写：\n' + code(sample.text)).join('') + '\n' + table(['输入', '文件转写耗时', '实时率（RTF）'], result.samples.map(s => [s.file, s.wallSeconds.toFixed(3) + ' s', s.wallRTF.toFixed(3)])) + '\nRTF 为处理时间除以音频时长，小于 1 表示处理速度快于音频播放速度。耗时包含文件加载、音频前处理、推理与文字后处理；第一次请求包含音频库初始化，不单独解释为 NPU 性能。\n';
  }
  const hasTranscripts = result.samples.some(sample => sample.asrText);
  return '\n下面三段 WAV 均由本次中文输入生成，可直接试听。采样率为 44.1 kHz，单声道，speed=0.8。\n' + result.samples.map((sample, i) => `\n**示例 ${i + 1}：输入文本**\n` + code(sample.text) + `\n生成音频：${sample.seconds.toFixed(3)} 秒。\n` + audioPlayer(find(sample.file), 'MeloTTS 合成结果 ' + (i + 1)) + (sample.asrText ? '\n' + (sample.asrModel ?? 'SenseVoice') + ' 自动回转写：\n' + code(sample.asrText) + (sample.asrObservation ? '\n' + sample.asrObservation + '\n' : '') : '')).join('') + (hasTranscripts ? '\n回转写用于发现明显内容差异，仍包含语音识别模型自身的误差；不能代替人工听音、自然度评分或长文本测试。\n' : '\n本次保留原始合成音频，尚未完成人工听音或自然度评分。\n');
}

export function displayedRuns(runs) {
  const latest = runs[0];
  if (['vision-layout', 'vision-weights'].includes(latest?.variantFamily)) return runs.filter(run => run.variantFamily === latest.variantFamily && run.revision === latest.revision);
  if (!latest?.variant || !latest.evidence.some(e => /\/(text-result|api)\.json$/.test(e.path))) return runs.slice(0, 1);
  const variants = new Map();
  for (const run of runs) {
    if (run.variant && run.revision === latest.revision && !variants.has(run.variant)) variants.set(run.variant, run);
  }
  return [...variants.values()];
}

export function effectSection({root, model: m, runs, environments, checks}) {
  let text = '\n## 查看部署效果\n';
  const selected = displayedRuns(runs);
  if (selected.length > 1) {
    for (const run of selected) {
      text += '\n### ' + (run.variantLabel ?? run.variant) + '\n';
      text += effectSection({root, model: m, runs: [run], environments, checks}).replace('\n## 查看部署效果\n', '');
    }
    return text;
  }
  const latest = runs[0];
  if (!latest && m.pendingValidationNote) return text + '\n' + m.pendingValidationNote + '\n';
  if (latest?.scope === 'local-components') {
    text += `\n**本地媒体功能已实测，完整应用尚未验证** · ${environments.get(latest.environmentId).label}。\n\n${latest.summary}\n`;
    text += deploymentExamples(root, latest);
    text += '\n**适用范围：**\n\n' + latest.limitations.map(note => '- ' + note).join('\n') + '\n';
    return text;
  }
  if (!latest || latest.status !== 'passed') {
    const partialAudio = latest ? audioExamples(root, m, latest) : '';
    if (latest) text += `\n**部署效果待验证**\n\n${latest.summary}\n\n${partialAudio ? '下方为部分输出，不代表整套部署通过。' : '当前没有可展示的成功运行结果。'}\n`;
    else text += '\n**本机尚未实测。** 部署后请按以下项目检查输出。\n';
    if (partialAudio) return text + partialAudio;
    if (m.id === '3D-Speaker') {
      text += '\n本例应展示两组声纹相似度：同一说话人的两段音频，以及不同说话人的两段音频。它输出声纹特征与比较分数，不直接生成转写文本或说话人时间轴。\n\n' + table(['音频组合', '用途', '当前本机结果'], [
        ['speaker1_a_cn_16k.wav + speaker1_b_cn_16k.wav', '检查同一说话人的相似度', '尚未实测'],
        ['speaker1_a_cn_16k.wav + speaker2_a_cn_16k.wav', '检查不同说话人的相似度', '尚未实测'],
      ]) + '\n保留两组实际分数后再比较排序；业务判断阈值需用自己的录音标定，不能根据文件名预填数值。\n';
    } else {
      if (m.recipe?.output) text += `\n运行后打开 \`${m.recipe.output}\`，确认文件是本次生成的。\n`;
      text += '\n' + checks.map(item => '- ' + item).join('\n') + '\n';
    }
    return text;
  }
  const state = latest.level === 'correctness' ? '固定样例已核对' : '已运行，效果仍需评估';
  text += `\n**${state}** · ${environments.get(latest.environmentId).label}。以下输入与输出来自本页固定版本的实际运行。\n\n${summaries[m.id] ?? latest.summary}\n`;
  if (!latest.evidence.some(e => /\/(enhancement|deployment)-result\.json$/.test(e.path))) {
    const textResult = latest.evidence.find(e => e.path.endsWith('/text-result.json'));
    const embedded = new Set(textResult ? JSON.parse(fs.readFileSync(path.join(root, 'static', textResult.path), 'utf8')).samples.flatMap(s => [s.imagePath, ...(s.framePaths ?? [])]).filter(Boolean) : []);
    text += media({...latest, evidence: latest.evidence.filter(e => !embedded.has(e.path) && (m.id !== 'QRCode-axera' || !e.path.includes('/outputs/')))});
  }
  text += apiExamples(root, latest);
  text += textExamples(root, latest);
  text += audioExamples(root, m, latest);
  text += pythonExamples(root, latest);
  text += birdExamples(root, latest);
  text += qrExamples(root, latest);
  text += decisionExamples(root, latest);
  text += enhancementExamples(root, latest);
  text += deploymentExamples(root, latest);
  text += compiledEmbeddingExamples(root, latest);
  if (m.id === 'Whisper') {
    const wav = latest.evidence.find(item => item.path.endsWith('/demo.wav'));
    // Markdown pages use HTML audio; keep the URL compatible with project subpath hosting.
    const audioUrl = (process.env.BASE_URL || '/').replace(/\/?$/, '/') + wav.path.slice(1);
    text += `\n**输入音频：16 kHz / 单声道 / PCM16**\n\n<audio controls preload="metadata" src="${audioUrl}" aria-label="Whisper 实测输入音频"></audio>\n\n[下载输入音频](${asset(wav)})\n\n**实际转写**\n${code('擅职出现交易几乎停止的情况')}\n**上游参考文本**\n${code('甚至出现交易几乎停止的情况')}`;
    if (latest.referenceReview) {
      text += '\n**核对同一音频的参考文字**\n\n' + latest.referenceReview.paragraph + '\n' + table(latest.referenceReview.table.headers, latest.referenceReview.table.rows);
    }
  }
  if (m.id === 'Plate-axera' && latest.variant !== 'nhwc') text += '\n控制台识别内容：\n' + code('车牌：川A2E7V7\n颜色：blue\n识别分数：0.9991') + '\n结果图中的省份汉字可能显示为问号，以控制台文字核对。\n';
  if (m.id === 'PPOCR_v5' || m.id === 'PPOCR_v6') text += '\n识别内容节选：\n' + code('纯臻营养护发素\nYM-X-3011\n220ml');
  const notes = visibleUsageNotes(m, latest);
  if (notes.length) text += '\n**使用时注意：**\n\n' + notes.map(note => '- ' + note).join('\n') + '\n';
  text += '\n这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。\n';
  return text;
}

function visibleUsageNotes(model, run) {
  return specialNotes[model.id] ? [specialNotes[model.id]] : run.limitations.filter(note => !/观察器|result.json|记录器|C\+\+ 日志|上游源码已|单一模型|GNU time/.test(note)).slice(0, 2);
}

export function technicalDetails({model, runs, environments, code, table, inline}) {
  if (!runs.length) return '';
  const selected = displayedRuns(runs);
  if (selected.length > 1) return selected.map(run => '\n**' + (run.variantLabel ?? run.variant) + '**\n' + technicalDetails({model, runs: [run], environments, code, table, inline})).join('');
  const run = runs[0];
  if (run.status !== 'passed') return '';
  const env = environments.get(run.environmentId);
  let text = '\n<details>\n<summary>查看样例环境与运行耗时</summary>\n\n';
  text += `环境：${env.label}。模型版本：${inline(run.revision)}。\n\n`;
  text += table(['组件', '版本或配置'], env.details.map(item => [item.name, item.value]));
  if (run.metrics.length) text += '\n' + table(['指标', '实测值', '计时或统计范围'], run.metrics.map(item => [item.name, item.value, item.scope]));
  const alreadyShown = new Set(run.scope === 'local-components' ? run.limitations : visibleUsageNotes(model, run));
  const remainingLimitations = run.limitations.filter(note => !alreadyShown.has(note));
  if (remainingLimitations.length) text += '\n适用范围：\n\n' + remainingLimitations.map(note => '- ' + note).join('\n') + '\n';
  return text + '\n</details>\n';
}
