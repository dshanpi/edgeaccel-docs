import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const safe = text => text.replaceAll('[', '\\[').replaceAll(']', '\\]').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const size = bytes => bytes < 1048576 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1048576).toFixed(1)} MB`;

export function generateOriginalFiles() {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'migration-manifest.json'), 'utf8'));
  const documents = JSON.parse(fs.readFileSync(path.join(root, 'src/data/documents.json'), 'utf8'));
  const groups = new Map();
  for (const file of manifest.files) {
    const folder = path.posix.dirname(file.path);
    const group = folder === '.' ? '用户指南' : folder;
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group).push(file);
  }
  let body = `---\ntitle: 原始附件目录\nunlisted: true\npagination_prev: null\npagination_next: null\n---\n\n# 原始附件目录\n\n共 ${manifest.files.length} 个原始文件，按项目目录整理。文件保留原始版本；历史日志中的地址、路径和配置仅适用于原测试环境。\n\n日常安装与模型部署请从[资料下载](../downloads.md)进入。需要追溯旧版本时，再展开下方目录。\n`;
  for (const [folder, files] of groups) {
    body += `\n<details>\n<summary>${safe(folder)}（${files.length} 个文件）</summary>\n\n`;
    for (const file of files) {
      const document = documents.find(item => item.source === file.path);
      // Keep download assets in Docusaurus's asset pipeline; document links use stable IDs.
      const url = document ? `/docs/${document.id}` : `@site/static/resources/ax650n/${file.path}`;
      body += `- [${safe(path.posix.basename(file.path))}](${encodeURI(url)}) · ${size(file.bytes)}${document ? ' · 在线阅读' : ''}\n`;
    }
    body += '\n</details>\n';
  }
  fs.writeFileSync(path.join(root, 'docs/reference/original-files.md'), body);
  console.log(`Generated attachment index: ${manifest.files.length} files in ${groups.size} folders.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) generateOriginalFiles();
