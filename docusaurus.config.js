import {themes as prismThemes} from 'prism-react-renderer';
import remarkPagesAttachments from './scripts/remark-pages-attachments.mjs';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'EdgeAccel 文档',
  tagline: '算力卡安装、模型部署与边缘 AI 应用实践',
  favicon: 'img/edgeaccel.svg',
  titleDelimiter: '·',
  future: {v4: true},
  url: process.env.SITE_URL || 'https://dshanpi.github.io',
  baseUrl: process.env.BASE_URL || '/',
  organizationName: 'dshanpi',
  projectName: 'edgeaccel-docs',
  onBrokenLinks: 'throw',
  i18n: {defaultLocale: 'zh-Hans', locales: ['zh-Hans']},
  presets: [['classic', {
    docs: {sidebarPath: './sidebars.js', editUrl: 'https://github.com/dshanpi/edgeaccel-docs/tree/main/', beforeDefaultRemarkPlugins: [remarkPagesAttachments]},
    blog: false,
    theme: {customCss: './src/css/custom.css'},
  }]],
  themeConfig: {
    colorMode: {respectPrefersColorScheme: true},
    docs: {sidebar: {autoCollapseCategories: true, hideable: true}},
    navbar: {
      title: 'EdgeAccel',
      hideOnScroll: true,
      logo: {alt: '', src: 'img/edgeaccel.svg', href: '/'},
      items: [
        {type: 'docSidebar', sidebarId: 'docsSidebar', label: 'AX8850', position: 'left'},
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {title: '开始使用', items: [{label: '文档总览', to: '/docs/'}, {label: '算力卡用户指南', to: '/docs/ax650n/user-guide'}, {label: '上手路线', to: '/docs/ax650n/roadmap'}]},
        {title: '应用与资料', items: [{label: '输出检查方法', to: '/docs/reference/validation'}, {label: '模型目录', to: '/docs/models/catalog'}, {label: '资料下载', to: '/docs/downloads'}]},
        {title: '项目', items: [{label: 'GitHub', href: 'https://github.com/dshanpi/edgeaccel-docs'}]},
      ],
      copyright: `Copyright © ${new Date().getFullYear()} 100askTeam. Built with Docusaurus.`,
    },
    prism: {theme: prismThemes.github, darkTheme: prismThemes.dracula, additionalLanguages: ['bash', 'powershell', 'json', 'cpp']},
  },
  markdown: {
    format: 'detect',
    mermaid: true,
    mdx1Compat: {comments: true, admonitions: true, headingIds: true},
    hooks: {onBrokenMarkdownLinks: 'throw', onBrokenMarkdownImages: 'throw'},
  },
  themes: ['@docusaurus/theme-mermaid'],
  plugins: [['@easyops-cn/docusaurus-search-local', {hashed: true, indexBlog: false, language: ['en', 'zh'], ignoreFiles: ['docs/reference/original-files']}]],
};
export default config;
