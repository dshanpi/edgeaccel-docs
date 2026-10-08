import React from 'react';
import Link from '@docusaurus/Link';
import styles from './styles.module.css';

export function GuideHero({label, title, description, facts = []}) {
  return <div className={styles.hero}>
    <span className={styles.label}>{label}</span>
    <p className={styles.title}>{title}</p>
    <p className={styles.description}>{description}</p>
    {facts.length > 0 && <dl className={styles.facts}>{facts.map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>}
  </div>;
}

export function GuideNext({items}) {
  return <nav className={styles.next} aria-label="相关部署指南">{items.map(({to, title, text}) =>
    <Link key={to} to={to}><strong>{title}<span aria-hidden="true"> →</span></strong><span>{text}</span></Link>
  )}</nav>;
}
