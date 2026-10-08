const {test} = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
process.env.PAGES_ATTACHMENT_REVISION = 'a'.repeat(40);
const {externalAttachment, attachmentUrl} = require('./pages-attachments.cjs');
const doc = path.resolve(__dirname, '../docs/models/deploy/model.md');
const prefix = `https://raw.githubusercontent.com/dshanpi/edgeaccel-docs/${'a'.repeat(40)}/static/`;

test('immutable archive and evidence URLs support all document link forms', () => {
  for (const url of ['/examples/test.zip', '../../../static/examples/test.zip', '@site/static/examples/test.zip']) {
    assert.equal(attachmentUrl(url, doc), prefix + 'examples/test.zip');
  }
  assert.equal(attachmentUrl('/validation/effects/test/result.json#output', doc), prefix + 'validation/effects/test/result.json#output');
  assert.equal(attachmentUrl('/examples/测试.tar.gz', doc), prefix + 'examples/' + encodeURIComponent('测试.tar.gz'));
});
test('media, scripts, links and escaped paths remain local or unchanged', () => {
  for (const url of ['/validation/effects/test/image.png', '/examples/test.py', 'https://example.com/test.zip', '../guide.md', '#output']) {
    assert.equal(attachmentUrl(url, doc), null);
  }
  assert.equal(externalAttachment('../examples/test.zip'), null);
});
test('local builds retain attachments; invalid revisions fail closed', () => {
  const run = revision => spawnSync(process.execPath, ['-e', "console.log(require('./scripts/pages-attachments.cjs').externalAttachment('examples/test.zip'))"], {
    cwd: path.resolve(__dirname, '..'), env: {...process.env, PAGES_ATTACHMENT_REVISION: revision}, encoding: 'utf8',
  });
  assert.equal(run('').stdout.trim(), 'null');
  assert.notEqual(run('main').status, 0);
});
