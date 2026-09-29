import React from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import useBaseUrl from '@docusaurus/useBaseUrl';
import stats from '@site/src/data/siteStats.json';
import HeroCarousel from '@site/src/components/HeroCarousel';
import styles from './index.module.css';

const stages = [
  {
    "number": "01",
    "title": "安装与首次推理",
    "description": "确认主机架构和卡容量，安装 AXCL，运行第一张图片。",
    "href": "/docs/ax650n/user-guide",
    "tone": "purple",
    "status": "阅读指南"
  },
  {
    "number": "02",
    "title": "视觉模型",
    "description": "检测、分割、姿态与深度估计，附配套程序及结果检查。",
    "href": "/docs/models/detection",
    "tone": "orange",
    "status": "阅读指南"
  },
  {
    "number": "03",
    "title": "文本与多模态",
    "description": "使用 AXCL 运行时完成文本对话、图像问答与服务接入。",
    "href": "/docs/models/llm-runtime",
    "tone": "teal",
    "status": "阅读指南"
  },
  {
    "number": "04",
    "title": "语音与扩展",
    "description": "语音识别、语音合成、OCR 和检索，按适配状态选择。",
    "href": "/docs/models/catalog",
    "tone": "slate",
    "status": "阅读指南"
  }
];

const outcomes = [
  [
    "按平台选择",
    "安装包由主机架构和系统决定，配套 PAC 需匹配随卡配置。"
  ],
  [
    "部署后查看效果",
    "每个模型按操作顺序部署，运行后直接对照图片、文本或音频结果。"
  ],
  [
    "保留配套资料",
    "PDF、Word、示例源码、视频与历史验证记录集中查阅。"
  ]
];

function StageCard({stage}) {
  const content = (
    <>
      <div className={styles.stageTopline}>
        <span className={`${styles.stageNumber} ${styles[stage.tone]}`}>
          {stage.number}
        </span>
        <span className={styles.stageStatus}>
          {stage.status ?? (stage.href ? '已开放' : '规划中')}
        </span>
      </div>
      <h3>{stage.title}</h3>
      <p>{stage.description}</p>
      {stage.href && <span className={styles.stageLink}>进入章节 →</span>}
    </>
  );

  return stage.href ? (
    <Link className={styles.stageCard} to={stage.href}>
      {content}
    </Link>
  ) : (
    <article className={`${styles.stageCard} ${styles.stageCardPlanned}`}>
      {content}
    </article>
  );
}

export default function Home() {
  return (
    <Layout
      title="M.2 算力卡使用指南"
      description="M.2 算力卡使用指南：AXCL 安装、视觉模型、文本与多模态、语音、应用接入与验证。">
      <header className={styles.hero}>
        <div className={`container ${styles.heroGrid}`}>
          <div className={styles.heroCopy}>
            <div className={styles.eyebrow}>
              <span className={styles.eyebrowDot} />
              100ASK · EDGE AI DOCUMENTATION
            </div>
            <h1>把 AI 算力，<br /><span className={styles.heroAccent}>带到设备端。</span></h1>
            <p className={styles.heroLead}>
              一张 M.2 算力卡，通过 PCIe 为主机扩展边缘 AI。
              从视觉感知到文本与多模态，用 AXCL 将模型接入本地应用。
            </p>
            <div className={styles.featureTags}><span>M.2 算力卡</span><span>PCIe 主机扩展</span><span>本地模型推理</span></div>
            <div className={styles.heroActions}>
              <Link
                className="button button--primary button--lg"
                to="/docs/ax650n/user-guide">
                开始使用算力卡
              </Link>
              <Link
                className="button button--secondary button--lg"
                to="/docs/models/catalog">
                选择部署模型
              </Link>
            </div>
            <dl className={styles.heroStats}>
              <div>
                <dt>{stats.documents}</dt>
                <dd>篇技术文档</dd>
              </div>
              <div>
                <dt>{stats.models}</dt>
                <dd>个模型与应用条目</dd>
              </div>
              <div>
                <dt>{stats.modelGroups}</dt>
                <dd>类模型任务</dd>
              </div>
            </dl>
          </div>

          <HeroCarousel className={styles.heroVisual} />
        </div>
      </header>

      <main>
        <section className={styles.capabilities} aria-labelledby="capabilities-title">
          <div className="container">
            <div className={styles.sectionHeading}>
              <div><span className={styles.sectionKicker}>ON-DEVICE INTELLIGENCE</span><h2 id="capabilities-title">一张卡，连接多种 AI 能力</h2></div>
              <p>主机负责系统与业务，算力卡负责模型推理。按任务选择模型，查看对应环境下的部署步骤与实际效果。</p>
            </div>
            <div className={styles.capabilityGrid}>
              <Link className={styles.capabilityCard} to="/docs/models/detection">
                <img src={useBaseUrl('/img/home/ax8850-vision.jpg')} width="1672" height="941" loading="lazy" decoding="async" alt="AX8850 视觉应用示意：目标检测、图像分割与人体姿态" />
                <div className={styles.capabilityCopy}><span className={styles.capabilityKicker}>COMPUTER VISION</span><h3>让设备看懂眼前的世界</h3><p>目标检测、分割、姿态与深度估计，连接图片和视频应用。</p><span className={styles.capabilityLink}>探索视觉模型 <span aria-hidden="true">↗</span></span></div>
              </Link>
              <Link className={styles.capabilityCard} to="/docs/models/vision-language">
                <img src={useBaseUrl('/img/home/ax8850-multimodal.jpg')} width="1672" height="941" loading="lazy" decoding="async" alt="AX8850 本地多模态应用示意：图像、语音与文本" />
                <div className={styles.capabilityCopy}><span className={styles.capabilityKicker}>LLM · VLM · AUDIO</span><h3>在本地，理解更多种输入</h3><p>文本对话、图像问答与语音处理，让模型能力走进端侧应用。</p><span className={styles.capabilityLink}>探索多模态模型 <span aria-hidden="true">↗</span></span></div>
              </Link>
            </div>
            <p className={styles.visualNote}>图片为产品与应用场景示意；模型支持范围、卡容量要求及实测结果见各部署文档。</p>
          </div>
        </section>
        <section className={styles.pathSection}>
          <div className="container">
            <div className={styles.sectionHeading}>
              <div>
                <span className={styles.sectionKicker}>DOCUMENTATION</span>
                <h2>按任务阅读部署步骤</h2>
              </div>
              <p>已收录 {stats.hardwareValidatedInThisEdition} 个模型的实际部署效果，图片、问答和音频结果随部署步骤展示。<Link to="/docs/models/catalog">选择模型并查看效果</Link></p>
            </div>
            <div className={styles.stageGrid}>
              {stages.map((stage) => (
                <StageCard key={stage.title} stage={stage} />
              ))}
            </div>
          </div>
        </section>

        <section className={styles.outcomesSection}>
          <div className={`container ${styles.outcomesGrid}`}>
            <div className={styles.outcomesIntro}>
              <span className={styles.sectionKicker}>PRACTICAL GUIDES</span>
              <h2>检查输入、输出与运行状态</h2>
              <p>
                安装、模型正确性、性能和稳定性分别记录。使用统一模板保存版本、输入、输出与日志。
              </p>
              <Link className={styles.textLink} to="/docs/">
                浏览完整文档总览 →
              </Link>
            </div>
            <div className={styles.outcomeList}>
              {outcomes.map(([title, description], index) => (
                <article className={styles.outcomeItem} key={title}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <div>
                    <h3>{title}</h3>
                    <p>{description}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
