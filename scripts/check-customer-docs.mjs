import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const walk = dir => fs.readdirSync(dir, {withFileTypes: true}).flatMap(entry =>
  entry.isDirectory() ? walk(path.join(dir, entry.name)) : [path.join(dir, entry.name)]);
// Preserve original filenames, URLs, dependency versions and evidence timestamps.
// This check targets calendar annotations presented in customer documentation.
for (const file of walk(path.join(root, 'docs')).filter(file => /\.mdx?$/.test(file))) {
  const source = fs.readFileSync(file, 'utf8');
  const prose = source.replace(/\]\([^)]*\)/g, ']')
    .replace(/(?:src|href|poster)="[^"]*"/g, '');
  assert(!/\b20\d{2}-\d{2}-\d{2}\b|20\d{2}年\d{1,2}月\d{1,2}日/.test(prose),
    `Customer-facing calendar date: ${path.relative(root, file)}`);
}
for (const name of ['ModelCatalog', 'ModelSelectionGuide']) {
  const source = fs.readFileSync(path.join(root, 'src/components', name, 'index.js'), 'utf8');
  assert(!/\{result\.date\}/.test(source), `Validation date rendered by ${name}`);
}
const video = fs.readFileSync(path.join(root, 'docs/usage/video.md'), 'utf8');
assert(!/开发版或演示版/.test(video), 'Stale six-stream project entry');
const sidebar = fs.readFileSync(path.join(root, 'sidebars.js'), 'utf8');
assert(!sidebar.includes('ax650n/applications/qwen3-vl/'), 'Historical Qwen pages must stay out of navigation');
for (const name of ['usage', 'validation']) {
  const source = fs.readFileSync(path.join(root, `docs/ax650n/applications/qwen3-vl/${name}.md`), 'utf8');
  assert(/^unlisted: true$/m.test(source), `Historical Qwen page must be unlisted: ${name}`);
}
console.log('Customer documentation audit passed: date presentation and current navigation.');
