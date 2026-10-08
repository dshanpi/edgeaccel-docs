// Preload for a complete production build. Keep static attachments out of
// the bundler's in-memory asset collection; copy and hash every file after emit.
const fs = require('node:fs');
const fsp = fs.promises;
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {externalAttachment} = require('./pages-attachments.cjs');
const {pipeline} = require('node:stream/promises');
const site = path.resolve(__dirname, '..');

async function hash(file) {
  const digest = crypto.createHash('sha256');
  await pipeline(fs.createReadStream(file), digest);
  return digest.digest('hex');
}

const staticModule = require(path.join(site, 'node_modules/@docusaurus/core/lib/webpack/plugins/StaticDirectoriesCopyPlugin.js'));
staticModule.createStaticDirectoriesCopyPlugin = async function ({props}) {
  assert.equal(path.resolve(props.siteDir), site);
  assert.deepEqual(props.siteConfig.staticDirectories, ['static']);
  const source = path.join(site, 'static');
  const destination = path.resolve(props.outDir);
  assert.notEqual(destination, source);
  assert(!destination.startsWith(source + path.sep));
  return {
    apply(compiler) {
      assert.equal(compiler.options.mode, 'production');
      compiler.hooks.afterEmit.tapPromise('VerifiedStaticCopy', async () => {
        const files = [];
        async function copy(directory, relative = '') {
          for (const entry of await fsp.readdir(directory, {withFileTypes: true})) {
            const name = path.join(relative, entry.name);
            const from = path.join(source, name);
            const to = path.join(destination, name);
            assert(!entry.isSymbolicLink(), `Review static symlink before building: ${from}`);
            if (entry.isDirectory()) {
              await fsp.mkdir(to, {recursive: true});
              await copy(from, name);
            } else {
              assert(entry.isFile(), `Unsupported static entry: ${from}`);
              await fsp.mkdir(path.dirname(to), {recursive: true});
              const before = await hash(from);
              const downloadUrl = externalAttachment(name);
              if (downloadUrl) {
                files.push({path: name.split(path.sep).join('/'), bytes: (await fsp.stat(from)).size, sha256: before, downloadUrl});
                continue;
              }
              try {
                await fsp.copyFile(from, to, fs.constants.COPYFILE_EXCL);
              } catch (error) {
                if (error.code !== 'EEXIST') throw error;
                // Never silently overwrite a generated bundle or page.
              }
              assert.equal(await hash(to), before, `Static copy/collision mismatch: ${name}`);
              assert.equal(await hash(from), before, `Static source changed during build: ${name}`);
              files.push({path: name.split(path.sep).join('/'), bytes: (await fsp.stat(to)).size, sha256: before});
            }
          }
        }
        await copy(source);
        const report = {verified: true, count: files.length, bytes: files.reduce((n, f) => n + f.bytes, 0), files};
        assert(process.env.EDGEACCEL_STATIC_COPY_REPORT, 'An external evidence path is required');
        await fsp.writeFile(process.env.EDGEACCEL_STATIC_COPY_REPORT, JSON.stringify(report, null, 2) + '\n');
        process.stderr.write(`[site-build] static files copied and SHA256 verified: ${report.count}, bytes: ${report.bytes}\n`);
      });
    },
  };
};

const compiler = require(path.join(site, 'node_modules/@docusaurus/bundler/lib/compiler.js'));
const originalCompile = compiler.compile;
compiler.compile = function (options) {
  assert(['webpack', 'rspack'].includes(options.currentBundler.name));
  assert.deepEqual(options.configs.map(c => c.name).sort(), ['client', 'server']);
  options.configs.parallelism = 1;
  for (const config of options.configs) {
    if (options.currentBundler.name === 'webpack') config.parallelism = 1;
    for (const plugin of config.optimization?.minimizer ?? []) {
      if (['CssMinimizerPlugin', 'TerserPlugin'].includes(plugin.constructor.name)) plugin.options.parallel = false;
    }
  }
  process.stderr.write(`[site-build] bundler=${options.currentBundler.name}; client/server parallelism=1; verified static copy outside asset collection\n`);
  return originalCompile(options);
};
