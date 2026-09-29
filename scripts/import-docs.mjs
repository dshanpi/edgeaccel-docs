import {generateOriginalFiles} from './generate-original-files.mjs';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = path.resolve(process.argv[2] || 'F:/AX/AX650N_card/doc');
const walk = (dir) => fs.readdirSync(dir, {withFileTypes: true}).flatMap((entry) =>
  entry.isDirectory() ? walk(path.join(dir, entry.name)) : [path.join(dir, entry.name)]);
const relative = (file) => path.relative(source, file).replaceAll('\\', '/');
const write = (file, value) => {
  const target = path.join(root, file);
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.writeFileSync(target, value);
};
// Imported pages become editable user guides. Re-importing refreshes source
// assets and audit data, but must not replace authored pages or navigation.
const writeNew = (file, value) => {
  if (!fs.existsSync(path.join(root, file))) write(file, value);
};
const files = walk(source).sort();
const streamRoot = 'aarch64/AX8850六路AI推流/';
const active = [
  ['AX650算力卡用户指南.md', 'user-guide', 'AX650 算力卡用户指南', 'guide'],
  ['aarch64/AX8850算力卡快速上手_aarch64.md', 'quick-start/arm64', 'ARM64 快速上手', 'platform'],
  ['Linux_x86/AX8850算力卡快速上手_Linux_x86_64.md', 'quick-start/linux-x86', 'Linux x86_64 快速上手', 'platform'],
  ['windows/AX8850算力卡快速上手_Windows.md', 'quick-start/windows', 'Windows 快速上手', 'platform'],
  [streamRoot + '使用说明.md', 'applications/six-streams/usage', '六路 AI 视频推流', 'streams'],
  [streamRoot + '实施说明.md', 'applications/six-streams/implementation', '实施说明', 'streams'],
  [streamRoot + '验证结果.md', 'applications/six-streams/validation', '验证结果', 'streams'],
  [streamRoot + '帧率优化说明.md', 'applications/six-streams/frame-rate', '帧率优化说明', 'streams'],
  [streamRoot + '推理优化说明.md', 'applications/six-streams/inference', '推理优化说明', 'streams'],
  [streamRoot + '第四路替换与本地预览.md', 'applications/six-streams/local-preview', '第四路替换与本地预览', 'streams'],
  [streamRoot + 'VLC断流排查_20260918.md', 'applications/six-streams/vlc-troubleshooting', 'VLC 断流排查', 'streams'],
  ['Qwen3-VL-8B/部署与使用.md', 'applications/qwen3-vl/usage', 'Qwen3-VL-8B 部署与使用', 'qwen'],
  ['Qwen3-VL-8B/验证记录.md', 'applications/qwen3-vl/validation', 'Qwen3-VL-8B 验证记录', 'qwen'],
  ['aarch64/tmp/AX8850-RK3576-Headers-20260916/安装说明.md', 'reference/kernel-headers/install', 'RK3576 内核头安装说明', 'headers'],
  ['aarch64/tmp/AX8850-RK3576-Headers-20260916/验证记录/修复说明.md', 'reference/kernel-headers/fixes', '内核头修复与验证', 'headers'],
];
const docs = files.filter((file) => file.endsWith('.md')).map((file) => {
  const original = relative(file);
  const match = active.find(([name]) => name === original);
  const title = match?.[2] || `${path.posix.basename(path.posix.dirname(original))} · ${path.basename(file, '.md')}`;
  const slug = match?.[1] || `archive/${crypto.createHash('sha256').update(original).digest('hex').slice(0, 12)}`;
  return {source: original, id: `ax650n/${slug}`, title, group: match?.[3] || 'archive'};
});
const fixes = [];
for (const file of files) {
  const target = path.join(root, 'static/resources/ax650n', relative(file));
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.copyFileSync(file, target);
}
for (const doc of docs) {
  let body = fs.readFileSync(path.join(source, doc.source), 'utf8').replace(/^\uFEFF/, '');
  body = body.replace(/(!?\[[^\]]*\])\(([^)]+)\)/g, (whole, label, url) => {
    if (/^(?:[a-z]+:|\/|#)/i.test(url)) return whole;
    const [local, anchor] = url.split('#');
    let resolved = path.posix.normalize(path.posix.join(path.posix.dirname(doc.source), decodeURI(local)));
    if (!fs.existsSync(path.join(source, resolved))) {
      const fallback = path.posix.join(streamRoot, decodeURI(local));
      if (!doc.source.includes('/历史版本/') || !fs.existsSync(path.join(source, fallback))) {
        throw new Error(`Missing resource: ${doc.source} -> ${url}`);
      }
      fixes.push({document: doc.source, original: url, resolved: fallback});
      resolved = fallback;
    }
    const targetDoc = docs.find((item) => item.source === resolved);
    const target = targetDoc ? `/docs/${targetDoc.id}` : `/resources/ax650n/${resolved}`;
    return `${label}(${encodeURI(target)}${anchor ? '#' + anchor : ''})`;
  });
  const note = doc.group === 'archive'
    ? '> **历史版本**：保留原始操作和验证记录，仅供追溯。缺失的共享图片和文档链接已指向现有资料，可能与该历史版本不同；当前操作请参阅[六路 AI 视频推流](/docs/ax650n/applications/six-streams/usage)。\n\n'
    : '';
  const frontmatter = `---\ntitle: ${JSON.stringify(doc.title)}\nsidebar_label: ${JSON.stringify(doc.title)}\nslug: /${doc.id}\n---\n\n`;
  writeNew(`docs/${doc.id}.md`, frontmatter + note + body);
}
const ordered = [...active.map(([name]) => docs.find((item) => item.source === name)), ...docs.filter((item) => item.group === 'archive')];
write('src/data/documents.json', JSON.stringify(ordered, null, 2) + '\n');
write('migration-manifest.json', JSON.stringify({source, documents: docs.length, files: files.map((file) => ({path: relative(file), bytes: fs.statSync(file).size, sha256: crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')})), repairedLinks: fixes}, null, 2) + '\n');
const groups = [['guide', '用户指南'], ['platform', '平台快速上手'], ['streams', '六路 AI 视频推流'], ['qwen', 'Qwen3-VL-8B'], ['headers', 'RK3576 内核头'], ['archive', '历史版本归档']];
const sidebar = ['overview', 'ax650n/roadmap', ...groups.map(([group, label]) => ({type: 'category', label, collapsed: group !== 'platform', items: ordered.filter((item) => item.group === group).map((item) => item.id)})), 'downloads'];
writeNew('sidebars.js', `// Initial sidebar generated by scripts/import-docs.mjs.\nexport default ${JSON.stringify({docsSidebar: sidebar}, null, 2)};\n`);
generateOriginalFiles();
console.log(`Imported ${docs.length} documents and ${files.length} original files; repaired ${fixes.length} historical links.`);
