import fs from 'node:fs';
import path from 'node:path';

const asset = item => '../../../static' + item.path.split('/').map(encodeURIComponent).join('/');
const label = text => text.replaceAll('[', '\\[').replaceAll(']', '\\]');
const code = text => {
  const fence = '`'.repeat(Math.max(2, ...(text.match(/`+/g) ?? []).map(value => value.length)) + 1);
  return `\n${fence}text\n${text.trim()}\n${fence}\n`;
};
const tableCell = value => String(value ?? '—').replaceAll('|', '\\|').replaceAll('\n', ' ');
const table = (headers, rows) => `| ${headers.map(tableCell).join(' | ')} |\n| ${headers.map(() => '---').join(' | ')} |\n${rows.map(row => '| ' + row.map(tableCell).join(' | ') + ' |').join('\n')}\n`;

const summaries = {
  'Qwen3-0.6B': '下面展示实际 API 回复。中文问答内容完整；数学题数值正确，但没有遵循“只输出数字”的格式要求。',
  'Qwen3-Embedding-0.6B': '每批 4 条英文短句得到 4 个 1024 维向量。相同文本的余弦相似度为 1，近义句的相似度高于无关句；两次请求的向量一致。',
  'FastVLM-1.5B-GPTQ-Int4': '输入图中有 3 名穿白色宇航服的人站在树林里。模型的一句描述与画面相符，但人数问答附带了“黑白图像”“漂浮”等不可靠细节。',
  Whisper: '使用 tiny 模型转写下方 4.204 秒中文音频。三次运行的文本一致，开头“擅职”与上游参考“甚至”不同，尚未通过识别质量核对。',
};

const specialNotes = {
  'Qwen3-0.6B': '样例使用 temperature=0、enable_thinking=false、stream=false、max_tokens=128；未测试长上下文、多轮对话或并发。',
  'Qwen3-Embedding-0.6B': '只检查了 3 种短英文文本及其中一条重复输入，尚未评估中文、长文本或检索召回率。',
  'FastVLM-1.5B-GPTQ-Int4': '这是一张图片的 3 次请求；尚未测试多图、视频、OCR 或中文视觉问答。',
  Whisper: '参考文本来自同版本模型卡，未独立听写，未计算 CER/WER。文件转写尚不包含麦克风采集、长音频分段或流式识别。',
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
    const split = sample.output.indexOf('</think>');
    const hasFinal = split >= 0 && sample.output.slice(split + 8).trim().length > 0;
    const reply = hasFinal ? sample.output.slice(split + 8) : sample.output;
    const original = hasFinal ? `\n模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。\n\n<details>\n<summary>查看模型原始完整回复</summary>\n${code(sample.output)}\n</details>\n` : '';
    const imageTiming = Number.isFinite(sample.nativeImageEncodeMs) ? `图像编码：${sample.nativeImageEncodeMs.toFixed(2)} ms；` : '';
    const timings = Number.isFinite(sample.nativeTtftMs) ? `\n${imageTiming}程序内部首 token 耗时：${sample.nativeTtftMs.toFixed(2)} ms；含模型加载的完整进程：${sample.processSeconds.toFixed(3)} s。内部计时不等同于客户端端到端首字延迟。\n` : '';
    return `\n**示例 ${i + 1}：输入**\n${picture}${code(sample.input)}\n**实际回复${hasFinal ? '的最终回答部分' : ''}**\n${code(reply)}\n${sample.observation}\n${timings}${original}`;
  }).join('');
  const conversations = (result.conversations ?? []).map((conversation, index) => {
    const turns = conversation.turns.map((turn, i) =>
      `\n**第 ${i + 1} 轮：输入**\n${code(turn.input)}\n**实际回复**\n${code(turn.output)}\n${turn.observation}\n` +
      (Number.isFinite(turn.nativeTtftMs) ? `\n本轮程序内部首 token 耗时：${turn.nativeTtftMs.toFixed(2)} ms。\n` : '')
    ).join('');
    return `\n**连续对话 ${index + 1}**\n\n以下各轮使用同一个进程和会话，保留上一轮上下文。\n${turns}\n整个对话进程：${conversation.processSeconds.toFixed(3)} s，包含一次模型加载、全部轮次和退出；不代表单轮推理耗时。内部首 token 计时不含模型加载。\n`;
  }).join('');
  return singles + conversations;
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

function qrExamples(root, run) {
  const item = run.evidence.find(e => e.path.endsWith('/qrcode-result.json'));
  if (!item) return '';
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', item.path), 'utf8'));
  let text = '\n以下 9 个 AX650 权重分别处理同版本仓库内的 48 张图片。统计“至少解码出一个结果”的图片数量，不能解释为检测准确率；一张图可能含多个二维码。\n\n';
  text += table(['编译模型', '完成图片', '检测到区域的图片', '成功解码的图片'], result.variants.map(v => [v.weight.split('/').pop().replace('.axmodel',''), v.batchSummary.images, v.batchSummary.detectedImages, v.batchSummary.decodedImages]));
  text += '\n下面用同一张 640×640 测试二维码复测全部 9 个变体。二维码原文为 `EdgeAccel AX8850 M.2 - deployment test 2026-09-23`。其中 8 个模型完成检测与解码；NanoDet 没有检测到区域，下方保留实际空结果。\n';
  for (const variant of result.variants) {
    const sample = variant.samples.find(s => s.file === 'edgeaccel-qr.png');
    const preview = run.evidence.find(e => e.path.endsWith('/outputs/' + variant.weight.split('/').pop().replace('.axmodel','.jpg')));
    text += '\n**' + variant.weight.split('/').pop().replace('.axmodel','') + ' · edgeaccel-qr.png**\n';
    if (preview) text += `\n[![${label('实际检测框 · ' + variant.weight.split('/').pop())}](${asset(preview)})](${asset(preview)})\n`;
    text += '\n实际解码文字：\n' + code(sample.decoded.length ? sample.decoded.map(x => x.data).join('\n') : '本次未解码出文字。');
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
    text += '\n**' + variant.label + '**\n\n' + variant.observation + '\n';
    text += '\n<div className="model-effect-gallery">\n';
    for (const preview of variant.previews) {
      const evidence = run.evidence.find(e => e.path === preview.path);
      text += `\n<figure>\n\n[![${label(preview.caption)}](${asset(evidence)})](${asset(evidence)})\n\n<figcaption>${preview.caption}</figcaption>\n</figure>\n`;
    }
    text += '\n</div>\n';
  }
  return text;
}

function deploymentExamples(root, run) {
  const item = run.evidence.find(e => e.path.endsWith('/deployment-result.json'));
  if (!item) return '';
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', item.path), 'utf8'));
  let text = '';
  for (const variant of result.variants) {
    text += `\n**${variant.label}**\n\n${variant.observation}\n`;
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
    text += '\n**卡端实际声纹分数**\n\n' + table(['模型', '输出维度', '同组录音相似度', '不同组录音相似度'], result.models.map(m => [m.model, m.embeddings[0].length, m.sameSpeaker.toFixed(6), m.differentSpeaker.toFixed(6)]));
    text += '\n**使用相同前处理与配套 CPU ONNX 对照**\n\n' + table(['模型', 'AXCL / ONNX 向量相似度（3 段）', 'ONNX 同组 / 不同组'], result.models.map(m => [m.model, m.onnxComparison.embeddingCosine.map(v => v.toFixed(6)).join(' / '), `${m.onnxComparison.sameSpeaker.toFixed(6)} / ${m.onnxComparison.differentSpeaker.toFixed(6)}`]));
    return text + '\n余弦分数越大表示向量越接近，不是准确率。卡端与 ONNX 的差异按实际值保留，不能把两套模型的分数直接套用到同一个业务阈值。\n';
  }
  if (model.id === 'SenseVoice') {
    const languages = {zh: '中文', en: '英文', yue: '粤语', ja: '日语', ko: '韩语'};
    return '\n以下为五段官方样例的实际转写。可播放原音频逐句核对；本次没有独立人工标注稿，未计算字错率或词错率。\n' + result.samples.map(sample => `\n**${languages[sample.language]} · ${sample.audioSeconds.toFixed(3)} 秒**\n` + audioPlayer(find(sample.file), 'SenseVoice ' + languages[sample.language] + '输入') + '\n实际转写：\n' + code(sample.text)).join('') + '\n' + table(['输入', '文件转写耗时', '实时率（RTF）'], result.samples.map(s => [s.file, s.wallSeconds.toFixed(3) + ' s', s.wallRTF.toFixed(3)])) + '\nRTF 为处理时间除以音频时长，小于 1 表示处理速度快于音频播放速度。耗时包含文件加载、音频前处理、推理与文字后处理；第一次请求包含音频库初始化，不单独解释为 NPU 性能。\n';
  }
  const hasTranscripts = result.samples.some(sample => sample.asrText);
  return '\n下面三段 WAV 均由本次中文输入生成，可直接试听。采样率为 44.1 kHz，单声道，speed=0.8。\n' + result.samples.map((sample, i) => `\n**示例 ${i + 1}：输入文本**\n` + code(sample.text) + `\n生成音频：${sample.seconds.toFixed(3)} 秒。\n` + audioPlayer(find(sample.file), 'MeloTTS 合成结果 ' + (i + 1)) + (sample.asrText ? '\nSenseVoice 自动回转写：\n' + code(sample.asrText) : '')).join('') + (hasTranscripts ? '\n回转写用于发现明显内容差异，仍包含语音识别模型自身的误差；不能代替人工听音、自然度评分或长文本测试。\n' : '\n本次保留原始合成音频，尚未完成人工听音或自然度评分。\n');
}

export function displayedRuns(runs) {
  const latest = runs[0];
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
  text += `\n**${state}** · ${latest.date} · ${environments.get(latest.environmentId).label}。以下输入与输出来自本页固定版本的实际运行。\n\n${summaries[m.id] ?? latest.summary}\n`;
  if (!latest.evidence.some(e => /\/(enhancement|deployment)-result\.json$/.test(e.path))) {
    const textResult = latest.evidence.find(e => e.path.endsWith('/text-result.json'));
    const embedded = new Set(textResult ? JSON.parse(fs.readFileSync(path.join(root, 'static', textResult.path), 'utf8')).samples.map(s => s.imagePath).filter(Boolean) : []);
    text += media({...latest, evidence: latest.evidence.filter(e => !embedded.has(e.path) && (m.id !== 'QRCode-axera' || !e.path.includes('/outputs/')))});
  }
  text += apiExamples(root, latest);
  text += textExamples(root, latest);
  text += audioExamples(root, m, latest);
  text += pythonExamples(root, latest);
  text += qrExamples(root, latest);
  text += decisionExamples(root, latest);
  text += enhancementExamples(root, latest);
  text += deploymentExamples(root, latest);
  if (m.id === 'Whisper') {
    const wav = latest.evidence.find(item => item.path.endsWith('/demo.wav'));
    // Markdown pages use HTML audio; keep the URL compatible with project subpath hosting.
    const audioUrl = (process.env.BASE_URL || '/').replace(/\/?$/, '/') + wav.path.slice(1);
    text += `\n**输入音频：16 kHz / 单声道 / PCM16**\n\n<audio controls preload="metadata" src="${audioUrl}" aria-label="Whisper 实测输入音频"></audio>\n\n[下载输入音频](${asset(wav)})\n\n**实际转写**\n${code('擅职出现交易几乎停止的情况')}\n**上游参考文本**\n${code('甚至出现交易几乎停止的情况')}`;
  }
  if (m.id === 'Plate-axera') text += '\n控制台识别内容：\n' + code('车牌：川A2E7V7\n颜色：blue\n识别分数：0.9991') + '\n结果图中的省份汉字可能显示为问号，以控制台文字核对。\n';
  if (m.id === 'PPOCR_v5' || m.id === 'PPOCR_v6') text += '\n识别内容节选：\n' + code('纯臻营养护发素\nYM-X-3011\n220ml');
  const notes = specialNotes[m.id] ? [specialNotes[m.id]] : latest.limitations.filter(note => !/观察器|result.json|记录器|C\+\+ 日志|上游源码已|单一模型|GNU time/.test(note)).slice(0, 2);
  if (notes.length) text += '\n**使用时注意：**\n\n' + notes.map(note => '- ' + note).join('\n') + '\n';
  text += '\n这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。\n';
  return text;
}

export function technicalDetails({model, runs, environments, code, table, inline}) {
  if (!runs.length) return '';
  const selected = displayedRuns(runs);
  if (selected.length > 1) return selected.map(run => '\n**' + (run.variantLabel ?? run.variant) + '**\n' + technicalDetails({model, runs: [run], environments, code, table, inline})).join('');
  const run = runs[0];
  if (run.status !== 'passed') return '';
  const env = environments.get(run.environmentId);
  let text = '\n<details>\n<summary>查看样例环境与运行耗时</summary>\n\n';
  text += `环境：${env.label}。日期：${run.date}。模型版本：${inline(run.revision)}。\n\n`;
  text += table(['组件', '版本或配置'], env.details.map(item => [item.name, item.value]));
  if (run.metrics.length) text += '\n' + table(['指标', '实测值', '计时或统计范围'], run.metrics.map(item => [item.name, item.value, item.scope]));
  if (run.limitations.length) text += '\n适用范围：\n\n' + run.limitations.map(note => '- ' + note).join('\n') + '\n';
  return text + '\n</details>\n';
}
