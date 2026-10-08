import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {displayedRuns, effectSection, technicalDetails} from './model-effects.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const records = JSON.parse(fs.readFileSync(path.join(root, 'src/data/modelDeployments.json'), 'utf8'));
const validationPath = path.join(root, 'src/data/modelValidationResults.json');
const validation = fs.existsSync(validationPath)
  ? JSON.parse(fs.readFileSync(validationPath, 'utf8'))
  : {schemaVersion: 1, environments: [], runs: []};
const environments = new Map(validation.environments.map(environment => [environment.id, environment]));
const validationRuns = (modelId) => validation.runs.map((run, index) => ({...run, index}))
  .filter(run => run.modelId === modelId)
  .sort((a, b) => b.date.localeCompare(a.date) || b.index - a.index);
const validationStatus = {passed: '通过', failed: '未通过', blocked: '受阻'};
const validationLevel = {basic: '基本运行', correctness: '结果正确性'};
const dest = path.join(root, 'docs/models/deploy');
fs.mkdirSync(dest, {recursive: true});
function writeGeneratedFile(destination, content) {
  if (fs.existsSync(destination) && fs.readFileSync(destination, 'utf8') === content) return;
  const temporary = `${destination}.${process.pid}.tmp`;
  try {
    fs.writeFileSync(temporary, content);
    for (let attempt = 0; ; attempt++) {
      try {
        fs.renameSync(temporary, destination);
        return;
      } catch (error) {
        if (attempt >= 3 || !['UNKNOWN', 'EBUSY', 'EPERM', 'EACCES'].includes(error.code)) throw error;
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100 * (attempt + 1));
      }
    }
  } finally {
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}
const code = (text, lang = 'bash') => `\n\`\`\`${lang}\n${text.trim()}\n\`\`\`\n`;
const inline = (text) => `\`${String(text).replaceAll('`', '')}\``;
// Emit readable Python literals instead of double-escaped JSON inside shell examples.
const pyString = value => String(value).includes('\n') && !String(value).includes('"""')
  ? '"""' + String(value).replaceAll('\\', '\\\\') + '"""'
  : JSON.stringify(String(value));
const link = (m, file) => `${m.huggingface}/blob/${m.sha}/${file.split('/').map(encodeURIComponent).join('/')}`;
const table = (header, rows) => `| ${header.join(' | ')} |\n| ${header.map(() => '---').join(' | ')} |\n${rows.map((r) => `| ${r.map((s) => String(s ?? '—').replaceAll('|', '\\|').replaceAll('\n', ' ')).join(' | ')} |`).join('\n')}\n`;
const role = (file) => /requirements/.test(file) ? 'Python 依赖清单' : /tokenizer.*\.py$/.test(file) ? '旧版分词服务入口' : /\.py$/.test(file) ? 'Python 程序 / 前后处理' : /\.sh$/.test(file) ? '启动或构建脚本' : /config.*\.json$/.test(file) ? '运行配置' : /\.axmodel$/.test(file) ? '编译模型；按目录区分芯片和规格' : /embed.*\.bin$/.test(file) ? 'Embedding 权重' : /tokenizer|vocab|tokens|lexicon|dict/.test(file) ? '分词器 / 字典，必须配套' : /\.(png|jpe?g|wav|mp3|ppm)$/.test(file) ? '示例输入' : '配套资源';

const checks = {
  detection: ['检查框坐标映射回原图后是否正确，类别名称与模型训练类别一一对应。', '分别测试有目标、无目标和多个目标的图片；固定置信度及 NMS 阈值，再比较漏检、误检和耗时。'],
  segmentation: ['检查掩码尺寸、类别或实例编号以及边缘与原图的对齐关系。', '同时保留原图、叠加图和原始掩码；不能只以检测框正确判定分割通过。'],
  pose: ['核对关键点数量、顺序、左右侧和骨架连线；点坐标需要映射回原图。', '测试遮挡与多人样本，记录低置信度点的过滤规则。'],
  depth: ['先确认输出是相对深度、视差还是公制深度；颜色图只用于观察。', '用有前后遮挡关系的场景检查近远顺序。需要测距时另用标定与实际距离验证。'],
  '3d': ['核对输出坐标系、尺度、视角顺序与相机参数。', '与参考几何或已知尺寸比较；保存中间结果，区分模型误差和坐标变换错误。'],
  classification: ['使用已知类别的输入，核对 Top-1 / Top-5 与标签索引。', '检查缩放、裁剪、通道顺序和归一化是否与模型版本一致。'],
  embedding: ['检查向量维度、有限数值及是否需要归一化；文本与图片使用配套编码器。', '用匹配对、不匹配对比较相似度排序，再建立小型索引；更换模型后重建索引。'],
  ocr: ['逐项检查文字区域、阅读顺序、字典映射和识别文本。', '至少包含中文、英文、数字及旋转文字；保留裁剪图以区分检测和识别问题。'],
  text: ['先测短问答，再测两轮上下文；翻译模型使用有参考译文的短句。', '记录首 token 延迟、生成速率和实际上下文长度，确认没有乱码、持续重复或异常提前结束。'],
  vlm: ['使用已知内容的单张图片提问，回答应包含可核对的图像细节。', '再测试多轮图片或短视频，记录抽帧和缩放规则；纯文本回复正确不能代替视觉编码器验证。'],
  asr: ['保存输入音频的采样率、通道数和参考转写，逐句比较漏词、错词和语言标记。', '流式模式还需检查分块边界和最终文本合并；分别记录端到端耗时与纯模型耗时。'],
  tts: ['回放生成音频，检查文字是否完整、读音、音色、停顿和尾部截断。', '记录采样率、音频时长、生成时间与 RTF；长文本、参考音色和多语言分别验证。'],
  audio: ['对比原始与处理后的音频，检查有效语音、噪声、失真和块边界。', '核对采样率、通道数与时长，检查循环状态或重叠相加是否正确。'],
  vad: ['同时测试目标语音、静音、噪声和相似唤醒词，分别记录漏检与误检。', '保存阈值、窗口长度、采样率和时间戳单位，检查连续输入的状态传递。'],
  diarization: ['使用有说话人标注的录音，检查时间边界、编号连续性和重叠发言。', '分别验证分段与转写；说话人 embedding 相似度不能代替分段准确率。'],
  punctuation: ['输入没有标点的短文，检查恢复后的断句和标点位置。', '分别测试数字、专有名词和长句，确认原始文字没有被删除或改写。'],
  enhance: ['比较处理前后的细节、颜色、噪声与边缘，核对输出分辨率。', '固定裁剪和缩放方式，用多张样图评估；仅生成一张图片不代表增强效果通过。'],
  generation: ['固定提示词、随机种子、步数和分辨率，检查图像内容和明显伪影。', '分别记录首图耗时、后续耗时与峰值内存，验证各阶段输出接口一致。'],
  video: ['检查帧序、帧率、尺寸、总时长和音画同步。', '先测试短视频，再测试连续处理；保存丢帧和时间戳日志。'],
  tracking: ['在首帧指定目标，检查后续帧中的目标身份和框位置是否连续。', '测试遮挡、离开画面与重新出现，记录失跟处理方式。'],
  open: ['核对文本特征与类别列表顺序，再用包含目标和不含目标的图片测试。', '分别测试同义词与不同提示词；词表或编码器变更后重新计算文本特征。'],
  pipeline: ['分别验证每个模型阶段的真实输入、输出和后端，再启动完整应用。', '检查服务地址、错误传播、超时与资源释放；某个子模型运行不代表整条链路完成。'],
  custom: ['按模型卡明确每个输入和输出的名称、shape、dtype 与业务含义。', '保留一组有参考答案的固定样本，分别验证模型加载、输出正确性和连续运行。'],
};

function prerequisites(m) {
  if (m.kind === 'multicard' && m.multiCardRuntime) {
    const runtime = m.multiCardRuntime;
    return `\n## 准备运行环境\n\n该固定版本的启动程序为 **${runtime.hostArchitecture} Linux** 可执行文件，原始脚本使用 **${runtime.deviceCount} 张算力卡**。准备可同时识别这些设备的主机，完成[驱动与设备检查](../../usage/device-check.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。\n\n运行前用 ${inline('axcl-smi')} 核对全部设备及其编号顺序。RK3576 属于 ARM64 主机，不能直接运行此仓库配套的 x86-64 程序；需要另行取得匹配的 ARM64 多卡入口并完成验证。\n\n`;
  }
  const runtime = m.kind === 'cv' ? '[编译 AXCL 视觉示例](../../usage/build-samples.md)' : m.kind === 'axllm' ? '[编译 AXCL 大模型运行时](../llm-runtime.md)' : m.kind === 'legacy' ? '[准备主机环境](../../getting-started/prepare.md)' : ['python','python-review'].includes(m.kind) || m.id === '3D-Speaker' || m.localGuide ? '[安装 PyAXEngine](../../usage/python.md)' : '[准备主机环境](../../getting-started/prepare.md)';
  const latest = validationRuns(m.id)[0];
  const sampleEnvironment = latest?.status === 'passed' ? environments.get(latest.environmentId) : null;
  const sampleLabels = [...new Set(displayedRuns(validationRuns(m.id)).filter(run => run.status === 'passed').map(run => environments.get(run.environmentId).label))];
  const sampleNote = sampleLabels.length > 1
    ? `本页包含 ${sampleLabels.map(label => `**${label}**`).join(' 与 ')} 的样例。按效果展示中的权重和容量对应使用，不同环境的结果不能互相替代。\n\n`
    : sampleEnvironment ? `本页效果展示使用 **${sampleEnvironment.label}**；其他容量或平台需重新确认模型能否加载并正确运行。\n\n` : '';
  return `\n## 准备运行环境\n\n${sampleNote}在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、${runtime}和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。\n\n后文使用设备 0，运行前用 ${inline('axcl-smi')} 确认设备可用。\n\n`;
}

function download(m) {
  const candidates = validationRuns(m.id).filter(run => run.downloadScope !== 'supplement' && run.evidence.some(item => item.path.endsWith('/download-manifest.json')));
  const manifests = displayedRuns(candidates).map(run => run.evidence.find(item => item.path.endsWith('/download-manifest.json')));
  const selected = manifests.length ? [...new Set(manifests.flatMap(manifest => JSON.parse(fs.readFileSync(path.join(root, 'static', manifest.path), 'utf8')).files.map(file => file.path)))] : (m.downloadFiles ?? []);
  if (m.downloadVariants?.length) {
    const shared = m.downloadSharedFiles;
    if (!Array.isArray(shared) || !shared.length || shared.some(f => !m.files.includes(f) || !/^[A-Za-z0-9._-]+$/.test(f))) throw new Error(`Invalid shared variant files: ${m.id}`);
    const values = new Set();
    const coverage = new Set();
    const variants = m.downloadVariants.map(v => {
      if (!/^[a-z0-9-]+$/.test(v.value) || values.has(v.value) || !/^[A-Za-z0-9._-]+$/.test(v.directory)) throw new Error(`Invalid download variant: ${m.id}`);
      values.add(v.value);
      const files = m.files.filter(f => f.startsWith(v.directory + '/') || shared.includes(f));
      if (files.length <= shared.length || !files.some(f => f.endsWith('.axmodel'))) throw new Error(`Empty download variant: ${m.id}`);
      files.forEach(f => coverage.add(f));
      return {...v, files};
    });
    if (coverage.size !== selected.length || selected.some(f => !coverage.has(f))) throw new Error(`Variant downloads differ from reviewed files: ${m.id}`);
    if (!Number.isFinite(m.downloadMinimumGiB) || m.downloadMinimumGiB <= 0) throw new Error(`Missing variant disk requirement: ${m.id}`);
    const choose = variants.map(v => `  ${v.value}) WEIGHTS=${JSON.stringify(v.directory)} ;;`).join('\n');
    const command = `set -e\nMODEL_DIR=~/edgeaccel/models/${m.slug}/${m.sha.slice(0,12)}\nVARIANT=${variants[0].value}\ncase "$VARIANT" in\n${choose}\n  *) echo "未知模型规格" >&2; exit 1 ;;\nesac\nmkdir -p "$MODEL_DIR"\ndf -h "$MODEL_DIR"\npython3 - "$MODEL_DIR" <<'PY'\nimport shutil, sys\nfree = shutil.disk_usage(sys.argv[1]).free / 1024**3\nassert free >= ${m.downloadMinimumGiB}, f"当前仅有 {free:.2f} GiB 可用，请先释放空间"\nPY\n~/edgeaccel/hf-env/bin/hf download ${m.repo} \\\n  --include "$WEIGHTS/*" ${shared.map(f => JSON.stringify(f)).join(' ')} \\\n  --revision ${m.sha} \\\n  --local-dir "$MODEL_DIR"\ncd "$MODEL_DIR"`;
    return `## 选择规格并下载模型\n\n本页分别验证以下规格。一次选择一组，下载对应权重与共用文件；切换规格前先停止模型服务。\n\n` +
      table(['VARIANT', '所选文件数'], variants.map(v => [inline(v.value), v.files.length])) +
      `\n以下默认选择第一组。执行前修改 ${inline('VARIANT')}，并确认主机内部模型目录所在分区至少有 ${m.downloadMinimumGiB} GiB 可用空间。空间不足时，先备份结果并清理已完成测试的权重目录，再下载下一组。\n` + code(command) +
      `\n保留同一终端的 ${inline('MODEL_DIR')}、${inline('VARIANT')} 变量，后续配置沿用所选目录与规格。下载受阻时见[下载方式与文件校验](../../usage/download-models.md)。\n`;
  }
  let filenames = selected.length ? '\\\n  ' + selected.map(file => JSON.stringify(file)).join(' \\\n  ') + ' ' : '';
  if (m.downloadPatterns?.length) {
    // Compact fixed-revision downloads only when patterns select the exact
    // reviewed manifest. An upstream file addition cannot silently widen scope.
    const matches = (file, pattern) => new RegExp('^' + pattern.split('*')
      .map(part => part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('.*') + '$').test(file);
    const expanded = m.files.filter(file => m.downloadPatterns.some(pattern => matches(file, pattern)));
    if (expanded.length !== selected.length || expanded.some(file => !selected.includes(file))) throw new Error(`Download patterns differ from reviewed files: ${m.id}`);
    filenames = '\\\n  --include ' + m.downloadPatterns.map(file => JSON.stringify(file)).join(' ') + ' ';
  }
  return `## 下载模型与样例\n\n本页使用 ${inline(m.repo)} 的固定版本。${selected.length ? `下面下载本页选用的 ${selected.length} 个文件。` : '仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。'}\n${code(`MODEL_DIR=~/edgeaccel/models/${m.slug}/${m.sha.slice(0,12)}\nmkdir -p "$MODEL_DIR"\n~/edgeaccel/hf-env/bin/hf download ${m.repo} ${filenames}\\\n  --revision ${m.sha} \\\n  --local-dir "$MODEL_DIR"\ncd "$MODEL_DIR"`)}\n保留当前终端中的 ${inline('MODEL_DIR')} 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。\n`;
}

function files(m) {
  const selected = m.keyFiles.length ? m.keyFiles : m.files.filter(f => f !== '.gitattributes').slice(0,8);
  return '\n<details>\n<summary>查看文件用途与版本信息</summary>\n\n' +
    table(['文件 / 目录内路径','用途'],selected.map(f=>[`[${inline(f)}](${link(m,f)})`,m.multiCardRuntime?.emptyRootConfig && f === 'config.json' ? '该提交为空文件；运行参数见启动脚本' : role(f)])) +
    `\n仓库提交：${inline(m.sha)}。${m.weightCount ? `仓库中的 ${m.weightCount} 个 ${inline('.axmodel')} 文件可能包括多个芯片、规格和分片。` : `该提交没有预编译 ${inline('.axmodel')} 文件。`}运行时使用本页指定的配套文件，完整列表见[固定版本目录](${m.huggingface}/tree/${m.sha})。\n\n</details>\n`;
}

function cv(m) {
  const r=m.recipe;
  return `\n## 执行图片推理\n\n本页使用 ${inline(r.binary)}，模型为 ${inline(r.model)}，输入为 ${inline(r.input)}。${inline('-g')} 参数顺序为高、宽。\n${code(`cd "$MODEL_DIR"\nSAMPLE=~/edgeaccel/src/axcl-samples/build/install/bin/${r.binary}\ntest -x "$SAMPLE"\ntest -s ${r.model}\ntest -s ${r.input}\nldd "$SAMPLE"\nset -o pipefail\n"$SAMPLE" -m ${r.model} -i ${r.input} -g ${r.size} -r 1 2>&1 | tee run.log`)}\n依赖中不能出现 ${inline('not found')}。程序退出码应为 0，日志不应有模型加载或设备错误。${r.output ? `检查本次产生的 ${inline(r.output)} 的修改时间与画面内容；仓库自带的旧结果图不能作为本次运行证据。` : '保存本次控制台输出及结果图片，并核对类别和坐标。'}\n\n示例源码：[axcl-samples 固定版本](https://github.com/AXERA-TECH/axcl-samples/tree/cbfa4c76891758983ca2b0c99c11d6621d59af39)。\n`;
}

function python(m) {
  const r=m.recipe;
  let text=`\n## 配置 Python 后端\n\n激活已安装 PyAXEngine 的主机虚拟环境。先检查可用 provider：\n${code('source ~/edgeaccel/python-env/bin/activate\npython -c "import axengine; print(axengine.get_available_providers())"')}\n必须包含 ${inline('AXCLRTExecutionProvider')}。保留已安装的 PyAXEngine，按下面命令安装本例依赖。\n`;
  if(r.pipPackages?.length)text+=`\n在已激活的环境中安装该入口直接使用的依赖；以下依赖用于本页的命令行示例：\n${code('python -m pip install '+r.pipPackages.join(' '))}\n`;
  if(r.providerEdits.length) {
    const patches = r.providerEdits.map(edit => `    {"path": ${pyString(edit.path ?? r.entry)}, "old": ${pyString(edit.old)}, "new": ${pyString(edit.new)}}`).join(",\n");
    const patchScript = `from pathlib import Path\nedits = [\n${patches}\n]\nfor edit in edits:\n    path = Path(edit.get("path", ${JSON.stringify(r.entry)}))\n    source = path.read_text(encoding="utf-8")\n    if edit["old"] not in source:\n        assert edit["new"] in source, f"补丁目标不匹配：{path}"\n        continue\n    backup = path.with_name(path.name + ".upstream")\n    if not backup.exists():\n        backup.write_text(source, encoding="utf-8")\n    path.write_text(source.replace(edit["old"], edit["new"]), encoding="utf-8")\n    print(f"已修改 {path}")`;
    text+=`\n按本页已核对的修改配置 AXCL 后端。脚本在首次修改前保留 ${inline('.upstream')} 备份；原表达式不匹配时停止，避免误改其他版本。${m.id === 'DeepLabv3Plus' ? '本例还将 CPU 后处理的 Torch argmax 改为 NumPy argmax，并保留同版本 VOC 调色板，从而无需安装 Torch/TorchVision；权重不变。' : ''}\n${code(`cd "$MODEL_DIR"\npython - <<'PY'\n${patchScript}\nPY`)}\n重新下载原始源码后，需要再次执行此修改。\n`;
  } else text+=`\n该脚本支持 ${inline('--providers')}，下面的命令已显式选择 AXCL。\n`;
  text+=`\n## 运行模型\n\n在模型根目录执行，输入与权重使用该提交的实际路径：\n${code(`cd "$MODEL_DIR"\ntest -s ${r.model}\ntest -s ${r.input}\nset -o pipefail\npython ${r.entry} ${r.args} 2>&1 | tee run.log`)}\n日志中的实际执行后端应为 ${inline('AXCLRTExecutionProvider')}。${r.output ? `检查 ${inline(r.output)} 是本次新生成的文件，内容与输入相符。` : '保留控制台输出，逐句核对实际转写内容。该入口不生成单独结果文件。'}使用仓库现成结果图或只检查程序退出码均不足以判断效果。\n\n参数依据：[${inline(r.entry)} 源码](${link(m,r.entry)})。\n`;
  return text;
}

function configTable(m) {
  const c=m.config;
  if(!c)return '';
  return `## 核对运行配置\n\n配置文件：${inline(c.config)}。\n\n`+table(['项目','当前配置'],[
    ['运行时模型名称',inline(c.modelName ?? m.repo)],['分词器类型（tokenizer_type）',inline(c.tokenizer)],['多模态类型（vlm_type）',c.vlm && c.vlm !== 'None' ? inline(c.vlm) : '不启用'],['Transformer 层数',c.layers],['分片命名模板',inline(c.layerPattern)],['Embedding 模式',c.embedding?'是，使用 /v1/embeddings':'否'],
  ])+'\n'+table(['配置字段','文件路径','同提交文件表'],c.references.map(r=>[inline(r.field),inline(r.path),r.exists?'已找到':'未找到，先解决配套关系']))+`\n逐层核对 ${c.layers} 个分片，不能用同系列其他版本补缺。${c.missingLayers.length ? `未找到：${c.missingLayers.slice(0,4).map(inline).join('、')}。` : '文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。'}\n`;
}

function axllm(m) {
  const c=m.config, vlm=!!c.vlm && c.vlm!=='None';
  const img=m.exampleImage ?? m.sampleInputs.find(f=>/\.(png|jpe?g)$/i.test(f));
  const imagePath=m.effectInput ? m.effectInput.directory+'/'+m.effectInput.file : img ? `~/edgeaccel/models/${m.slug}/${m.sha.slice(0,12)}/${img}` : '~/edgeaccel/inputs/test.jpg';
  const checksPy=`import json\nfrom pathlib import Path\np = Path(${JSON.stringify(c.folder || '.')})\nc = json.loads((p / "config.json").read_text())\nfiles = [c["template_filename_axmodel"] % i for i in range(c["axmodel_num"])]\nfiles += [c[k] for k in ${JSON.stringify(c.references.map(r=>r.field))} if c.get(k)]\nmissing = [str(p / f) for f in files if not (p / f).is_file()]\nassert not missing, missing\nprint("模型配套文件齐全")`;
  let text=configTable(m)+`\n## 检查完整模型包\n\n在模型根目录执行文件检查：\n${code(`cd "$MODEL_DIR"\npython3 - <<'PY'\n${checksPy}\nPY`)}\n此包按新 ${inline('axllm')} 配置接口核对。使用[本站编译的 AXCL 程序](../llm-runtime.md)，包内 ${inline('bin/axllm')} 可能是 AX650 板端程序，不能仅因同为 ARM64 就直接使用。\n\n## 启动单卡服务\n\n终端 1 执行，保持服务前台运行：\n${code(`AXLLM=~/edgeaccel/src/ax-llm/build-axcl/install/bin/axllm\n"$AXLLM" version\nAXLLM_DEVICES=0 "$AXLLM" serve "$MODEL_DIR${c.folder?'/'+c.folder:''}" --port 8000`)}\n版本输出必须显示 AXCL 后端。保留内存预检；若提示 CMM 不足，先缩小模型或使用较短上下文的独立编译包，不关闭内存预检强制运行。\n\n## 发送${c.embedding?'向量提取':vlm?'图片问答':'文本'}请求\n\n在同一主机终端 2 执行。先从 ${inline('/v1/models')} 获取实际模型名称。${vlm ? m.effectInput ? '先下载与下方效果展示相同的样例图，再发送请求。' : img ? `本例使用下载包内的 ${inline(img)}。` : `先把一张内容已知的图片保存到 ${inline('~/edgeaccel/inputs/test.jpg')}，再运行客户端。` : ''}\n`;
  if (vlm && m.effectInput) {
    const f=m.effectInput;
    text+=code(`mkdir -p ${f.directory}\n~/edgeaccel/hf-env/bin/hf download ${f.repo} ${f.file} \\\n  --revision ${f.revision} \\\n  --local-dir ${f.directory}\nprintf '%s  %s\\n' '${f.sha256}' ${f.directory}/${f.file} | sha256sum -c -`);
    text+='\n该图是下方问答实际使用的输入；校验输出应为 OK。\n';
  }
  let client=`import json, urllib.request${vlm?', base64':''}\n${vlm?'from pathlib import Path\n':''}base = "http://127.0.0.1:8000"\nwith urllib.request.urlopen(base + "/v1/models", timeout=30) as r:\n    model = json.load(r)["data"][0]["id"]\n`;
  if(c.embedding)client+=`payload = {"model": model, "input": ["A cat is sitting on the mat.", "A cat is sitting on the mat.", "There is a cat on the floor.", "The capital of France is Paris."], "encoding_format": "float"}\nendpoint = "/v1/embeddings"\n`;
  else if(vlm)client+=`image = Path(${JSON.stringify(imagePath)}).expanduser()\nmime = "image/png" if image.suffix.lower() == ".png" else "image/jpeg"\nencoded = base64.b64encode(image.read_bytes()).decode()\npayload = {"model": model, "messages": [{"role": "user", "content": [\n    {"type": "text", "text": ${JSON.stringify(m.examplePrompt ?? (m.id==='FastVLM-1.5B-GPTQ-Int4'?'Describe the image in one sentence.':m.profile==='ocr'?'识别图中的文字并按阅读顺序输出。':'描述图片中的主要对象。'))}},\n    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}\n]}], "max_tokens": 128, "temperature": 0}\nendpoint = "/v1/chat/completions"\n`;
  else client+=`payload = {"model": model, "messages": [{"role": "user", "content": ${JSON.stringify(m.examplePrompt ?? (m.task==='文本翻译'?'将下列中文翻译成英文：算力卡用于模型推理。':'请用一句话说明 PCIe 的用途。'))}}], "max_tokens": 128, "temperature": 0}\nendpoint = "/v1/chat/completions"\n`;
  if (m.id === 'Qwen3-0.6B' || m.requestOptions) client += 'payload.update(enable_thinking=False, stream=False)\n';
  client+=`request = urllib.request.Request(base + endpoint,\n    data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})\nwith urllib.request.urlopen(request, timeout=300) as r:\n    result = json.load(r)\n${c.embedding ? 'vectors = [item["embedding"] for item in result["data"]]\nprint("向量数量：", len(vectors))\nprint("各向量维度：", [len(vector) for vector in vectors])' : 'print(result["choices"][0]["message"]["content"])'}`;
  text+=code(`python3 - <<'PY'\n${client}\nPY`);
  text+=`\n${c.embedding?'检查 data 中向量数量与输入条数一致、维度固定，并且数值有限。Embedding 模型不使用交互式 run 或聊天接口。':'检查 choices 中的回复是否完整且与输入相关。替换 messages 中的提问文字，可复现下方其他问题；保持其余输入和生成参数一致。回复达到 max_tokens 上限时可能被截断，可先要求简短回答。HTTP 请求成功只说明接口可用，仍需按下节核对效果。'}\n\n运行时依据：[固定源码版本](https://github.com/AXERA-TECH/ax-llm/tree/8501c22b940f8c5804cb35044c5ffc136918b8f1)、[配置接口](https://github.com/AXERA-TECH/ax-llm/blob/8501c22b940f8c5804cb35044c5ffc136918b8f1/docs/configuration.md)。\n`;
  return text;
}

function legacy(m) {
  let text=`## 选择 AXCL 启动入口\n\n此包使用旧版专用程序，保留其脚本、分片和 tokenizer 服务组合。不能直接替换成新版 ${inline('axllm run')}。\n\n`;
  text+=table(['启动脚本','主机 / 模式'],m.scripts.map(s=>[`[${inline(s.path)}](${link(m,s.path)})`,`${s.path.includes('x86')?'x86_64':s.path.includes('aarch64')?'ARM64':'按程序架构确认'}${s.path.includes('api')?'，API 模式':''}${s.path.includes('video')?'，视频模式':''}`]));
  const s=m.selectedScript;
  if(!s)return text+'\n现有脚本仅覆盖服务或组合应用入口。先核对其全部服务依赖与参数，不在本文拼接一个未经核对的单模型命令。\n';
  const bin=s.binary[0];
  text+=`\n本页选择 ${inline(s.path)}。${s.path.includes('x86')?'该入口是 x86_64；RK3576 不能直接运行此二进制，需从同版本源码构建 ARM64 AXCL 程序。':'在 RK3576 上还需用 file 确认程序是 ARM64，并用 ldd 检查 AXCL 依赖。'}\n`;
  if(bin)text+=code(`cd "$MODEL_DIR"\nfile ${bin}\nldd ${bin}`);
  text+=`\n依赖中不能出现 ${inline('not found')}。${m.requirements.length?`Python 配套依赖文件：${m.requirements.map(inline).join('、')}。`:''}\n`;
  if(m.tokenizerService){
    const t=m.tokenizerService;
    text+=`\n## 启动配套分词服务\n\n在终端 1 激活安装本仓库依赖的 Python 环境，在模型根目录启动 ${inline(t.path)}：\n${code(`cd "$MODEL_DIR"\npython3 ${t.path} --host 127.0.0.1${t.port?' --port '+t.port:''}`)}\n${t.port?`保持该终端运行，在另一个终端用 ${inline('ss -ltnp')} 确认端口 ${t.port} 已监听。`:''}首次启动可能还需模型卡指定的 tokenizer 资源；不能用同系列另一个服务脚本替代。\n`;
  } else if(m.localTokenizerFiles?.length)text+=`\n## 核对本地分词器\n\n此脚本读取本地 tokenizer 文件：${m.localTokenizerFiles.map(inline).join('、')}，不启动旧版 HTTP 分词服务。确认这些文件与模型同 revision，保留脚本中的分词器参数名。\n`;
  else if(m.id==='ZipVoice.AXERA')text+='\n## 核对语音资源\n\n脚本读取 resources/zipvoice_hf/zipvoice/tokens.txt、模型目录、参考音频和 models/vocoder/vocos_full.axmodel。默认参考音频为 assets/moss_prompts/zh_1_4p5s.wav，参考文本必须与这段音频一致。\n';
  else text+='\n## 检查附加服务\n\n本页未核对到可独立启动的 HTTP tokenizer 命令。按所选脚本确认是否使用本地 tokenizer、音频前端或其他服务，完成这些依赖后再运行。\n';
  text+=`\n## 配置并运行本机脚本\n\n终端 2 在模型目录复制脚本，在副本中设置本机参数：\n${code(`cd "$MODEL_DIR"\ncp -n ${s.path} ${s.path}.local\nsed -n '1,220p' ${s.path}.local`)}\n`;
  const items=[];
  if(s.devices.length)items.push(`将 ${inline('--devices')} 的原值 ${s.devices.map(inline).join('、')} 改成实际设备列表；单卡编号为 0 时使用 ${inline('0')}，保留程序要求的参数格式。`);
  if(s.tokenizerUrls.length)items.push(`将 tokenizer URL 改为本机服务地址，并保留与服务一致的端口。地址 ${inline('0.0.0.0')} 用于监听，不作为客户端目标，客户端改用 ${inline('127.0.0.1')}。`);
  items.push('核对脚本中的模型目录、embedding、post 模型和输入文件全部存在。不要改变已编译的层数和上下文规格。');
  if(s.needsReview)items.push('该脚本含删除旧输出或修改文件权限的命令。删除副本中的清理命令，保留推理调用；使用独立结果文件保存本次输出。');
  text+=items.map(x=>`- ${x}`).join('\n')+'\n';
  text+=`\n确认架构、依赖、文件和附加服务均匹配后，在终端 2 执行：\n${code(`cd "$MODEL_DIR"\nset -o pipefail\nbash ${s.path}.local 2>&1 | tee run.log`)}\n${m.id==='ZipVoice.AXERA'?'默认脚本运行 distill、中文和 sentence 模式，输出 output_zh_distill_sentence.wav。':''}保存修改后的脚本和日志。设备初始化、tokenizer 连接或模型加载失败时停止，先解决对应依赖。\n`;
  return text;
}

function speaker(m) {
  let text = '\n## 补齐声纹程序依赖\n\n本页使用 ECAPA-TDNN 比较两段录音。当前固定仓库缺少程序导入的 `processor.py`，原始入口也尚需调整后端与短音频补齐逻辑。完成下列准备后才能运行，不能仅下载权重就执行。\n\n';
  text += table(['项目', '需要完成的操作'], [
    ['音频前端', '从模型配套源码补齐提供 FBank 的 processor.py；参数为 80 维、16 kHz、mean_nor=True，不能用同名的无关 pip 包代替。'],
    ['Python 依赖', '在 PyAXEngine 环境安装架构匹配、版本配套的 torch 和 torchaudio，并确认 numpy 可导入。'],
    ['执行后端', '将 run_axmodel_ecapa_tdnn.py 中会话的 AxEngineExecutionProvider 改为 AXCLRTExecutionProvider。'],
    ['短音频', '原入口在特征不足 360 帧时用全零张量覆盖原特征，需改为保留有效帧并仅补齐尾部；修正后与原始模型比较。'],
  ]);
  text += '\n权重使用 `ax650/ecapa-tdnn.axmodel`。三个示例 WAV 位于 `wavs/`，不要沿用 README 中缺少该目录的路径。\n';
  text += '\n## 比较两组录音\n\n**仅在上述依赖和处理逻辑修正完成后执行。** 在模型目录先比较同一说话人的两段录音：\n';
  text += code('cd "$MODEL_DIR"\nsource ~/edgeaccel/python-env/bin/activate\nset -o pipefail\npython run_axmodel_ecapa_tdnn.py \\\n  --model ax650/ecapa-tdnn.axmodel \\\n  --wavs wavs/speaker1_a_cn_16k.wav wavs/speaker1_b_cn_16k.wav \\\n  2>&1 | tee same-speaker.log');
  text += '\n再比较不同说话人的录音：\n';
  text += code('python run_axmodel_ecapa_tdnn.py \\\n  --model ax650/ecapa-tdnn.axmodel \\\n  --wavs wavs/speaker1_a_cn_16k.wav wavs/speaker2_a_cn_16k.wav \\\n  2>&1 | tee different-speaker.log');
  text += `\n检查日志中的实际 provider 为 AXCL，并找到 ${inline('The similarity score between two input wavs is')} 后面的分数。两份日志分别保留，按下节比较结果。上述命令参数已按[固定版本入口](${link(m,'run_axmodel_ecapa_tdnn.py')})核对，本机执行和修正后的数值仍待实测。\n`;
  return text;
}

function adaptation(m) {
  const intro={
    otherchip:'该仓库名称指定的芯片不是本指南的 AX650 / AX8850 系列卡目标。不能通过改文件名、换主机架构或调整 AXCL 参数使其变成当前卡的权重。',
    blocked:'上游 AX-LLM 已记录 Gemma-4 在 AXCL 后端的输出异常。本页保留版本、文件与验证条件，当前不提供面向业务使用的启动步骤。',
    multicard:'这是张量并行模型包。先按模型卡确认设备数量、设备编号顺序和各设备可用内存，单卡不能直接沿用多卡配置。',
    'config-review':'已找到运行配置，但仍有运行时类型或文件配套关系需要确认。先完成下列核对，不直接套用同系列聊天命令。',
    'python-review':'模型卡含 Python / AXCL 相关信息，但可用 provider 列表不等于本示例实际使用 AXCL。先核对下列入口与会话创建方式，再形成可执行的部署组合。',
    adapt:'该提交的模型文件或示例已收录，尚未核对到可直接用于此 M.2 卡的完整 AXCL 组合。下面给出此模型的接入文件与待完成项目，当前不作为已可运行教程。',
  };
  let text=`## 确认算力卡接入条件\n\n${intro[m.kind]}\n`;
  if(m.kind==='blocked')text+='\n缺陷依据：[AX-LLM AXCL 相关问题](https://github.com/AXERA-TECH/ax-llm/issues/39)。升级运行时后需固定新提交，用相同输入检查输出内容，再更新此页状态。\n';
  if(m.kind==='otherchip'){
    const family=m.id.replace(/[-_]?(?:AX637|AX630C|AX620E).*$/i,'').toLowerCase();
    const alternatives=records.filter(r=>r.id.toLowerCase().startsWith(family)&&r.id!==m.id&&r.kind!=='otherchip'&&r.kind!=='resource').slice(0,5);
    text+='\n先选择 AX650 / AX8850 的独立编译版本；没有相应权重时，按[转换自有模型](../custom-model.md)准备原始模型、量化数据和目标芯片配置。\n';
    if(alternatives.length)text+='\n可继续核对的同系列条目：'+alternatives.map(r=>`[${r.id}](${r.slug}.md)`).join('、')+'。具体上下文和任务是否等价，仍以各自页面为准。\n';
    return text;
  }
  text+=configTable(m);
  if(m.entryPoints.length){
    text+='\n### 核对本模型的程序入口\n\n'+table(['程序入口','接入条件'],m.entryPoints.map(e=>[`[${inline(e.path)}](${link(m,e.path)})`,!e.read?'仅文件清单已确认，调用方式待核对':e.providerFlag?`含 ${inline(e.providerFlag)} 参数，需确认参数传给实际会话` : e.boardProvider?'源码含板端 provider，需检查并替换对应会话':e.axclProvider?'源码含 AXCL provider，需确认实际执行分支':e.axengine?'使用 PyAXEngine，需显式选择 AXCL 并核对配套输入':'需要继续核对后端与依赖']));
    text+='\n修改前备份程序；只切换执行后端，保留本模型的输入处理、输出解码和资源释放。修改后保存源码版本或补丁。\n';
  }
  if(m.sampleInputs.length)text+=`\n### 准备本模型的输入\n\n本提交可核对的样本：${m.sampleInputs.map(inline).join('、')}。结合模型卡选择输入，结果图片不作为原始输入。\n`;
  if(m.kind==='multicard') {
    if (m.multiCardRuntime) {
      text+='\n### 核对多卡启动参数\n\n'+table(['官方启动脚本','程序','示例设备列表'],m.multiCardRuntime.launchers.map(s=>[
        `[${inline(s.path)}](${link(m,s.path)})`,inline(s.binary),inline(s.devices.join(',')),
      ]));
      text+='\n设备编号是原脚本的示例值。按主机实际编号配置，保留四个设备及分片顺序；每张卡的内存需求仍需按该包实际加载结果确认。\n';
      if (m.multiCardRuntime.emptyRootConfig) text+='\n此提交的 `config.json` 为 0 字节，不能作为有效 JSON 配置使用。原脚本通过命令行传入模型、分词器和设备参数。\n';
      text+=`\n语言层及 post 分片保存在 ${inline('.tar')} 包中；仅统计顶层 ${inline('.axmodel')} 文件不能代表完整权重数量。保留同提交的分片、embedding 和分词文件，不能用普通单卡包替换。\n`;
    }
    text+='\n核对分片到各卡的分配、主机到设备的数据传输及卡间依赖。先逐卡检查设备状态，不能仅将 devices 字段缩成一个编号。\n';
  }
  else if(m.kind!=='blocked')text+=`\n### 完成接入后再运行\n\n1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。${m.targetWeights.length?`本页列出的目标路径包括 ${m.targetWeights.slice(0,2).map(inline).join('、')}。`:''}\n2. Python 路径使用 ${inline('AXCLRTExecutionProvider')}；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 ${inline('/soc/lib')} 或芯片板端 runtime 的程序需移植或另行编译。\n3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。${m.profile==='pipeline'?'分别完成各子模型后，才能连接完整应用。':''}\n\n共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。\n`;
  return text;
}

const resourceActions={
  AXCL:'先确认主机是 ARM64 还是 x86_64，再选择对应的 AXCL 安装包、卡端 PAC 和文档版本。不要将 aarch64 板端程序包当作主机驱动安装。',
  Pulsar2:'用于在转换环境中将原始网络编译为 .axmodel。按模型转换章节配置容器、量化样本和芯片目标，生成后再复制到算力卡主机验证。',
  PyAXEngine:'用于给 Python 程序提供推理会话。安装后核对可用 provider，并用配套模型确认实际选择 AXCLRTExecutionProvider。',
  BoardImages:'先核对镜像对应的开发板。开发板系统镜像不是 M.2 卡的 PAC，也不是 RK3576 主机系统安装包。',
  lite_webui:'先在主机启动并测试模型 API，再配置页面中的服务地址和模型名称。界面启动成功不代表模型已加载。',
  AXERA_Benchmark:'选择与卡目标和运行时一致的测试文件，固定输入、重复次数和计时范围，再保存设备内存与延迟。',
  'AX620E-Community-Hub':'该资料属于 AX620E 平台，不能用于本 AX650 系列卡的固件或驱动安装。',
  'AX650-Community-Hub':'按目录区分板端 SDK、系统镜像与 AXCL 资料。M.2 卡主机安装仅使用相应 AXCL 组件。',
  'ppq-xs':'面向 AX520 / AX513 工具链，不作为本卡默认模型转换工具。AX650 目标按 Pulsar2 流程处理。',
  'frigate-resource':'先完成 Frigate 使用的主机视频输入与检测后端，再选择匹配的模型、标签与预处理配置。',
  'testdata-boxdemo':'下载所选演示需要的输入和配套资源，分别记录模型版本与测试数据版本。',
  'awesome-files':'按文件用途获取共享资料，先核对芯片、运行时和版本，再进入对应操作章节。',
};

for(const m of records){
  if(!/^[a-z0-9-]+$/.test(m.slug))throw new Error(`Invalid slug ${m.slug}`);
  const isResource=m.kind==='resource';
  const runs = validationRuns(m.id);
  const latest = runs[0];
  const verifiedLabel = latest?.scope === 'local-components' ? '本地媒体功能已实测，完整应用尚未验证' : latest ? (latest.status === 'passed' ? latest.level === 'correctness' ? '已实测，固定样例已核对' : '已实测，效果仍需评估' : '实测未完成') : m.pendingValidationNote ? '尚未通过本机部署验证' : '本机尚未实测';
  let body=`---\ntitle: ${JSON.stringify(m.id+(isResource?' 资源使用':' 部署指南'))}\nsidebar_label: ${JSON.stringify(m.id)}\ndescription: ${JSON.stringify(`${m.id} 的 M.2 算力卡部署步骤、配套文件与效果展示。`)}\n---\n\n# ${m.id}${isResource?' 资源使用':' 部署指南'}\n\n${isResource?'本仓库提供工具或配套资源。':`${m.id} 用于${m.task}。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。${m.recipe?.model ? `本页选择 ${inline(m.recipe.model)}。` : ''}`}\n\n> ${isResource?m.status:`${verifiedLabel}。${latest ? '[查看部署效果](#查看部署效果)。' : m.status+'。'}`}\n`;
  if(isResource){
    body+=`\n## 选择适用资源\n\n${resourceActions[m.id]}\n\n继续阅读[对应操作指南](../../${m.relatedGuide}.md)。本仓库固定参考提交为 ${inline(m.sha)}。\n\n`+files(m);
    body+='\n## 检查使用结果\n\n记录下载文件名、提交号、主机架构与安装组件版本。安装类资源先检查依赖和设备识别，模型类资源继续验证真实输入输出；界面和工具的启动结果分别记录。\n';
  }else if(m.compiledVariants){
    body+='\n## 准备运行环境\n\n本仓库提供 GPTQ 量化源权重，固定版本不含 `.axmodel`。在 M.2 算力卡上运行时，选择下表中的官方编译版本，并完成[驱动与设备检查](../../usage/device-check.md)和[AXCL 大模型运行时安装](../llm-runtime.md)。\n';
    body+='\n## 选择并下载编译版本\n\n进入所选版本的独立部署页，按其中的固定提交下载模型、分词器和配置。不同规格使用各自的完整文件，不混用目录。\n\n';
    const variants=m.compiledVariants.map(id=>{
      const variant=records.find(record=>record.id===id);
      if(!variant || !variant.weightCount)throw new Error(`Missing compiled variant: ${m.id}: ${id}`);
      return {model:variant,run:validationRuns(id)[0]};
    });
    body+=table(['编译版本 / 部署入口','固定提交','该版本实测范围'],variants.map(({model,run})=>[
      `[${model.id}](./${model.slug}.md)`,inline(model.sha),
      run?`${environments.get(run.environmentId).label}；${validationStatus[run.status]}（${validationLevel[run.level]}）`:'尚无实测记录',
    ]));
    body+='\n## 运行文本生成\n\n在所选部署页完成下载后，沿用该页的模型目录、运行时版本和配置启动服务，再执行页面给出的文本请求。收到完整回复后，核对回答内容及结束状态。\n\n量化源权重不能直接交给 `axcl_run_model`。需要自行转换模型时，另按[自定义模型接入](../custom-model.md)准备工具链，转换产物需单独验证。\n';
    body+='\n## 查看部署效果\n\n以下入口展示对应编译版本的实际请求、完整回复和耗时。源权重仓库本身尚无独立的算力卡运行记录，编译版本的结果仅适用于各页列出的硬件、模型提交和测试输入。\n\n';
    body+=variants.map(({model,run})=>`- [${model.id} 的部署效果](./${model.slug}.md#查看部署效果)：${run?.summary??'尚无实测结果。'}`).join('\n')+'\n';
    body+=`\n## 核对版本来源\n\n量化源权重固定提交为 ${inline(m.sha)}。两个编译仓库的模型卡均将本仓库列为转换来源；编译版本的提交与源权重提交独立管理。\n\n`;
    body+=variants.map(({model})=>`- [${model.id} 的固定版本模型卡](${link(model,model.readme)})。`).join('\n')+'\n';
  }else{
    if (!m.prerequisitesHandledByRecipe) body+=prerequisites(m);
    const hasSteps = ['cv','python','axllm','legacy'].includes(m.kind);
    if (!hasSteps && m.id !== '3D-Speaker' && !m.localGuide) body+=adaptation(m);
    if (m.downloadHandledByRecipe && !m.localGuide) throw new Error(`Missing download recipe: ${m.id}`);
    if(!['otherchip','blocked'].includes(m.kind) && !m.downloadHandledByRecipe)body+=download(m);
    if (m.localGuide) body+='\n'+fs.readFileSync(path.join(root,'scripts/model-recipes',m.localGuide),'utf8')+'\n';
    else if (m.id === '3D-Speaker') body+=speaker(m);
    else if (hasSteps) body+=m.kind==='cv'?cv(m):m.kind==='python'?python(m):m.kind==='axllm'?axllm(m):legacy(m);
    if (m.supplementGuide) body+='\n'+fs.readFileSync(path.join(root,'scripts/model-recipes',m.supplementGuide),'utf8')+'\n';
    body+=effectSection({root, model:m, runs, environments, checks:checks[m.profile]??checks.custom});
    body+=technicalDetails({model:m, runs, environments, code, table, inline});
    body+='\n遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。\n';
    body+=files(m);
    if(m.notes.length)body+='\n<details>\n<summary>补充说明与版本差异</summary>\n\n'+m.notes.map(n=>`- ${n}`).join('\n')+'\n\n</details>\n';
  }
  body+=`\n## 参考资料\n\n- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。\n- [固定版本文件表](${m.huggingface}/tree/${m.sha})。\n`;
  if(m.readme)body+=`- [模型卡 / 使用说明](${link(m,m.readme)})。\n`;
  if(m.entryPoints.length)body+=`- [主要程序入口：${m.entryPoints[0].path}](${link(m,m.entryPoints[0].path)})。\n`;
  if(!['cv','axllm','python','resource'].includes(m.kind)&&m.projects.length)body+=m.projects.slice(0,3).map(url=>`- [配套项目：${new URL(url).pathname.split('/').slice(1,3).join('/')}](${url})。\n`).join('');
  if(m.modelscope)body+=`- [ModelScope 对应资源](${m.modelscope})。不同平台的 revision 不通用，另行记录版本。\n`;
  body+=`\n返回[完整模型目录](../catalog.mdx)。\n`;
  const destination = path.join(dest,m.slug+'.md');
  writeGeneratedFile(destination, body);
}
const sidebarPath = path.join(root, 'src/data/modelSidebar.json');
const sidebarContent = JSON.stringify([...new Set(records.map(m=>m.group))].map(group=>({type:'category',label:group,collapsed:true,items:records.filter(m=>m.group===group).map(m=>m.guide)})),null,2)+'\n';
writeGeneratedFile(sidebarPath, sidebarContent);
console.log(`Generated ${records.length} individual guides.`);
