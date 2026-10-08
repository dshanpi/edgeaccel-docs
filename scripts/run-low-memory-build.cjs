const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const reportDir = path.join(root, '.cache-docs', 'low-memory-builds', new Date().toISOString().replace(/[:.]/g, '-'));
fs.mkdirSync(reportDir, {recursive: true});
const result = spawnSync(process.execPath, [
  '--require', path.join(__dirname, 'build-low-memory.cjs'),
  path.join(root, 'node_modules/@docusaurus/core/bin/docusaurus.mjs'),
  'build', '--config', path.join(root, 'docusaurus.low-memory.config.js'),
  ...process.argv.slice(2),
], {
  cwd: root, stdio: 'inherit',
  env: {
    ...process.env,
    NODE_OPTIONS: '--max-old-space-size=3072',
    DOCUSAURUS_NO_PERSISTENT_CACHE: 'true',
    TERSER_PARALLEL: 'false',
    DOCUSAURUS_SSR_CONCURRENCY: '1',
    DOCUSAURUS_SSG_WORKER_THREAD_COUNT: '1',
    RAYON_NUM_THREADS: '1', TOKIO_WORKER_THREADS: '1', RSPACK_BLOCKING_THREADS: '2',
    EDGEACCEL_STATIC_COPY_REPORT: path.join(reportDir, 'static-copy-manifest.json'),
  },
});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
