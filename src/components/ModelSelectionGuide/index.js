import React, {useState} from 'react';
import Link from '@docusaurus/Link';
import stats from '@site/src/data/siteStats.json';
import styles from './styles.module.css';

const tasks = [
  {title: '识别目标与位置', tag: '视觉检测', output: '输出类别、置信度和检测框，用于识别人、车或指定物体。', model: 'YOLO11', slug: 'yolo11', route: 'detection', more: '比较检测模型'},
  {title: '提取图片中的文字', tag: 'OCR', output: '输出文字区域和识别文本，适合图片、标牌与文档文字提取。', model: 'PPOCR_v5', slug: 'ppocr-v5', route: 'extensions', more: '比较 OCR 与扩展模型'},
  {title: '完成文本问答', tag: '文本生成', output: '接收文本提示并生成回复，核对内容、格式与响应时间。', model: 'Qwen3-0.6B', slug: 'qwen3-0-6b', route: 'text-generation', more: '比较文本模型'},
  {title: '理解图片内容', tag: '多模态', output: '结合图片与问题生成描述。视频输入按具体部署页确认。', model: 'SmolVLM2-500M-Video-Instruct', slug: 'smolvlm2-500m-video-instruct', route: 'vision-language', more: '比较图像问答模型'},
  {title: '将语音转为文字', tag: '语音识别', output: '接收音频文件并输出转写文本，先核对语言、采样率与切分方式。', model: 'Whisper', slug: 'whisper', route: 'speech-recognition', more: '比较语音与声纹模型'},
  {title: '将文字合成为语音', tag: '语音合成', output: '生成可播放音频，按目标语言、音色与参考语音方式选择。', model: 'MeloTTS', slug: 'melotts', route: 'speech-synthesis', more: '比较语音合成模型'},
  {title: '观察场景深度层次', tag: '深度估计', output: '生成深度图。实际距离测量还需核对模型尺度和相机标定。', model: 'Depth-Anything-3', slug: 'depth-anything-3', route: 'depth', more: '比较深度模型'},
  {title: '建立文本检索', tag: '向量检索', output: '将文本编码为向量，用于相似度检索；回答生成另配语言模型。', model: 'Qwen3-Embedding-0.6B', slug: 'qwen3-embedding-0-6b', route: 'extensions', more: '比较检索与扩展模型'},
];

function statusLabel(result) {
  if (!result) return '尚无本机实测记录';
  if (result.status === 'passed') return result.level === 'correctness' ? '固定样例已核对' : '已运行，效果待评估';
  return result.status === 'blocked' ? '实测受阻' : result.status === 'failed' ? '实测未通过' : '查看当前实测记录';
}

export function SelectionIntro() {
  return <div className={styles.intro}>
    <span className={styles.eyebrow}>M.2 算力卡 · 模型选型</span>
    <p className={styles.lead}>让业务输出决定模型，<br />让实测配置决定部署。</p>
    <p className={styles.introText}>从一组可复现的输入开始，确认效果与资源占用，再扩展到自己的数据和应用。</p>
    <ol className={styles.steps} aria-label="模型选型顺序">
      {['明确输出', '匹配容量', '对照效果', '接入应用'].map((text, i) => <li key={text}><span aria-hidden="true">0{i + 1}</span>{text}</li>)}
    </ol>
  </div>;
}

export function TaskChoices() {
  return <div className={styles.tasks}>
    {tasks.map(task => {
      const result = stats.modelValidationSummaries?.[task.model];
      const route = `/docs/models/deploy/${task.slug}`;
      return <article className={styles.task} key={task.model}>
        <span className={styles.tag}>{task.tag}</span>
        <h3>{task.title}</h3>
        <p>{task.output}</p>
        <Link className={styles.modelLink} to={route}>{task.model}<span aria-hidden="true"> ↗</span></Link>
        <div className={styles.evidence}>
          <Link to={result ? `${route}#查看部署效果` : route}>{statusLabel(result)}</Link>
          {result && <small>{result.environment}</small>}
        </div>
        <Link className={styles.more} to={`/docs/models/${task.route}`}>{task.more}<span aria-hidden="true"> →</span></Link>
      </article>;
    })}
  </div>;
}

const plans = {
  '8': {
    title: '先建立单模型运行基线',
    text: '从有对应 8GB 实测记录的权重与配置开始，先跑通一组固定输入，再测自己的业务数据。',
    rows: [
      ['输入规模', '先使用部署页的固定尺寸、短音频或单张图片。'],
      ['文本长度', '从短提示和单轮问答开始，核对模型编译时的上下文规格。'],
      ['运行方式', '先单请求、单模型；记录加载后和推理中的 CMM 占用。'],
      ['扩展顺序', '每次只增加一个变量：输入规模、上下文或并发数，重新测量峰值。'],
    ],
  },
  '16': {
    title: '在已验证基线上逐项扩展',
    text: '更多容量为较大权重、较长上下文或组合应用提供评估空间；可运行范围仍由具体配置与峰值占用决定。',
    rows: [
      ['输入规模', '先复现页面输入，再逐步增加图片数量、视频采样帧或音频长度。'],
      ['文本长度', '检查预填充、上下文和生成上限，测量目标长度下的实际占用。'],
      ['运行方式', '先测每个模型独立运行，再评估同时驻留和并发请求。'],
      ['扩展顺序', '分别记录各阶段峰值与延迟，按完整工作流检查资源释放和持续运行。'],
    ],
  },
};

export function CapacityPlanner() {
  const [capacity, setCapacity] = useState('8');
  const plan = plans[capacity];
  return <section className={styles.capacity} aria-label="按算力卡容量规划验证顺序">
    <fieldset className={styles.switcher}>
      <legend>选择实际使用的算力卡</legend>
      <div className={styles.options}>{['8', '16'].map(value => <label key={value} className={capacity === value ? styles.selected : ''}>
        <input type="radio" name="card-capacity" value={value} checked={capacity === value} onChange={() => setCapacity(value)} />
        {value} GB
      </label>)}</div>
    </fieldset>
    <div className={styles.capacityBody} aria-live="polite" aria-atomic="true">
      <h3>{plan.title}</h3><p>{plan.text}</p>
      <dl>{plan.rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    </div>
    <p className={styles.capacityNote}>此处切换的是验证顺序，不会筛选上方模型，也不表示容量适配已经通过。以部署页标注的卡容量、权重与输入范围为准。</p>
  </section>;
}
