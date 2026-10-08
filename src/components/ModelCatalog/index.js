import React, {useMemo, useState} from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import models from '@site/src/data/models.json';
import stats from '@site/src/data/siteStats.json';
import styles from './styles.module.css';
const pageSize = 30;
const groups = [...new Set(models.map(m=>m.group))];
const statuses = [...new Set(models.map(m=>m.status))];
const validations = stats.modelValidationSummaries ?? {};
const validationLabels = {pending: '本机尚未实测', basic: '已运行，效果待评估', correctness: '固定样例已核对', failed: '实测未通过', blocked: '实测受阻', resource: '工具或配套资料'};
const validationKey = model => model.kind === 'resource' ? 'resource' : !validations[model.id] ? 'pending' : validations[model.id].status === 'passed' ? validations[model.id].level : validations[model.id].status;
export default function ModelCatalog() {
  const [query,setQuery] = useState('');
  const [group,setGroup] = useState('');
  const [status,setStatus] = useState('');
  const [validation,setValidation] = useState('');
  const [page,setPage] = useState(0);
  const base = useBaseUrl('/docs/');
  const filtered = useMemo(()=>models.filter(m=>(!group||m.group===group)&&(!status||m.status===status)&&(!validation||validationKey(m)===validation)&&`${m.id} ${m.task} ${m.group}`.toLowerCase().includes(query.trim().toLowerCase())),[query,group,status,validation]);
  const pages = Math.max(1,Math.ceil(filtered.length/pageSize));
  const current = Math.min(page,pages-1);
  const shown = filtered.slice(current*pageSize,(current+1)*pageSize);
  const change = setter => event => {setter(event.target.value);setPage(0);};
  return <section className={styles.catalog} aria-label="独立模型文档查询">
    <div className={styles.filters}>
      <label>型号或用途<input type="search" placeholder="例如 Qwen3、YOLO、语音" value={query} onChange={change(setQuery)} /></label>
      <label>任务类别<select value={group} onChange={change(setGroup)}><option value="">全部类别</option>{groups.map(g=><option key={g}>{g}</option>)}</select></label>
      <label>AXCL 资料状态<select value={status} onChange={change(setStatus)}><option value="">全部状态</option>{statuses.map(s=><option key={s}>{s}</option>)}</select></label>
      <label>本机部署效果<select value={validation} onChange={change(setValidation)}><option value="">全部效果状态</option>{Object.entries(validationLabels).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
    </div>
    <div className={styles.summary}><span role="status" aria-live="polite">找到 {filtered.length} 个条目 · 每个条目对应独立文档</span>{(query||group||status||validation)&&<button type="button" onClick={()=>{setQuery('');setGroup('');setStatus('');setValidation('');setPage(0);}}>清除筛选</button>}</div>
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead><tr><th>模型 / 仓库</th><th>用途</th><th>资料状态</th><th>本机部署效果</th></tr></thead>
        <tbody>{shown.map(m=>{const result=validations[m.id];const key=validationKey(m);return <tr key={m.id}>
          <td><Link className={styles.model} to={`${base}${m.guide}`}>{m.id}</Link><div className={styles.links}><Link to={`${base}${m.guide}`}>{m.kind==='resource'?'资源使用说明':'独立部署文档'} →</Link><a href={m.huggingface} target="_blank" rel="noopener noreferrer">Hugging Face ↗</a></div></td>
          <td>{m.task}</td><td><span className={styles.badge} data-ready={['cv','axllm','python','legacy'].includes(m.kind)}>{m.status}</span></td>
          <td><span className={styles.validationBadge} data-status={result?.status ?? key}>{validationLabels[key]}</span>{result&&<><div className={styles.validation}>{result.environment}<br />{result.level==='correctness'?'固定样例':'基本运行'}检查</div><Link className={styles.evidenceLink} to={`${base}${m.guide}#查看部署效果`}>查看部署效果 →</Link></>}</td>
        </tr>;})}</tbody>
      </table>
      {!shown.length&&<p className={styles.empty}>没有匹配的条目。可缩短型号关键词，或清除任务和状态筛选。</p>}
    </div>
    <nav className={styles.pagination} aria-label="模型目录分页"><button type="button" disabled={current===0} onClick={()=>setPage(current-1)}>上一页</button><span>第 {current+1} / {pages} 页</span><button type="button" disabled={current+1>=pages} onClick={()=>setPage(current+1)}>下一页</button></nav>
    <details className={styles.fullIndex}><summary>展开全部 {models.length} 个文档链接</summary><ul>{models.map(m=><li key={m.id}><Link to={`${base}${m.guide}`}>{m.id}</Link></li>)}</ul></details>
  </section>;
}
