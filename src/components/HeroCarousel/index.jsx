import React, {useEffect, useRef, useState} from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './styles.module.css';

const duration = 6000;
const slides = [
  {image: 'ax8850-hero.jpg', title: '边缘算力', eyebrow: 'EDGE AI ACCELERATOR', caption: '紧凑形态 · 专注边缘推理', alt: 'AX8850 红色 M.2 算力卡，展示芯片、板载存储和金手指接口'},
  {image: 'ax8850-vision.jpg', title: '视觉感知', eyebrow: 'COMPUTER VISION', caption: '检测 · 分割 · 姿态，让设备看懂世界', alt: 'AX8850 视觉应用示意：目标检测、图像分割与人体姿态'},
  {image: 'ax8850-multimodal.jpg', title: '端侧多模态', eyebrow: 'LOCAL MULTIMODAL AI', caption: '文本 · 图像 · 语音，在本地处理', alt: 'AX8850 本地多模态应用示意：图像、语音与文本'},
];

export default function HeroCarousel({className}) {
  const base = useBaseUrl('/img/home/');
  const root = useRef(null);
  const touch = useRef(null);
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [visible, setVisible] = useState(false);
  const [inView, setInView] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(true);

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotion = () => setReducedMotion(media.matches);
    const updateVisibility = () => setVisible(!document.hidden);
    updateMotion();
    updateVisibility();
    media.addEventListener('change', updateMotion);
    document.addEventListener('visibilitychange', updateVisibility);
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), {threshold: 0.15});
    observer.observe(root.current);
    return () => {
      media.removeEventListener('change', updateMotion);
      document.removeEventListener('visibilitychange', updateVisibility);
      observer.disconnect();
    };
  }, []);

  const playing = !paused && !hovered && visible && inView && !reducedMotion;
  useEffect(() => {
    if (!playing) return undefined;
    const timer = window.setTimeout(() => setActive(index => (index + 1) % slides.length), duration);
    return () => window.clearTimeout(timer);
  }, [active, playing]);

  const select = index => {
    setActive((index + slides.length) % slides.length);
    setPaused(true);
  };
  const swipe = event => {
    if (!touch.current) return;
    const dx = event.clientX - touch.current.x;
    const dy = event.clientY - touch.current.y;
    touch.current = null;
    if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.5) select(active + (dx < 0 ? 1 : -1));
  };

  return (
    <section ref={root} className={`${className} ${styles.carousel}`} role="region" aria-roledescription="轮播" aria-label="AX8850 算力卡与应用场景"
      data-playing={playing} style={{'--slide-duration': `${duration}ms`}}
      onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      onFocusCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) setPaused(true); }}
      onKeyDown={event => {
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
          event.preventDefault();
          select(active + (event.key === 'ArrowRight' ? 1 : -1));
        }
      }}>
      <div className={styles.heading}><span>AX8850</span><span>{slides[active].eyebrow}</span></div>
      <div className={styles.stage}
        onPointerDown={event => {
          if (event.pointerType === 'touch' && !event.target.closest('button')) {
            touch.current = {x: event.clientX, y: event.clientY};
            event.currentTarget.setPointerCapture(event.pointerId);
          }
        }}
        onPointerUp={swipe} onPointerCancel={() => { touch.current = null; }}>
        {slides.map((slide, index) => (
          <div key={slide.image} className={`${styles.slide} ${index === active ? styles.active : ''}`}
            role="group" aria-roledescription="幻灯片" aria-label={`${index + 1} / ${slides.length}：${slide.title}`} aria-hidden={index !== active}>
            <img src={`${base}${slide.image}`} alt={slide.alt} width="1672" height="941" draggable="false" decoding="async" fetchPriority={index === 0 ? 'high' : 'low'} />
          </div>
        ))}
        <div className={styles.arrows}>
          <button type="button" onClick={() => select(active - 1)} aria-label="上一张图片">‹</button>
          <button type="button" onClick={() => select(active + 1)} aria-label="下一张图片">›</button>
        </div>
        <span className={styles.counter} aria-hidden="true">0{active + 1}<span> / 0{slides.length}</span></span>
      </div>
      <div className={styles.caption} aria-live={playing ? 'off' : 'polite'} aria-atomic="true">{slides[active].caption}<span>产品与应用示意</span></div>
      <div className={styles.controls}>
        <div className={styles.selectors} role="group" aria-label="选择展示场景">
          {slides.map((slide, index) => (
            <button key={slide.image} type="button" className={styles.selector} aria-label={`显示${slide.title}`} aria-current={index === active ? 'true' : undefined} onClick={() => select(index)}>
              <span className={styles.track} aria-hidden="true"><span key={`${active}-${playing}`} className={index === active ? (playing ? styles.progress : styles.selected) : undefined} /></span>
              {slide.title}
            </button>
          ))}
        </div>
        <button type="button" className={styles.playButton} disabled={reducedMotion}
          aria-label={reducedMotion ? '系统已设置减少动态效果，自动播放已关闭' : paused ? '播放轮播' : '暂停轮播'}
          title={reducedMotion ? '已遵循系统减少动态效果设置' : paused ? '播放轮播' : '暂停轮播'}
          onClick={() => setPaused(value => !value)}>
          <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">{paused || reducedMotion ? <path d="M6 3.5 16 10 6 16.5Z" fill="currentColor" /> : <path d="M6 4v12M14 4v12" stroke="currentColor" strokeWidth="3" />}</svg>
        </button>
      </div>
    </section>
  );
}
