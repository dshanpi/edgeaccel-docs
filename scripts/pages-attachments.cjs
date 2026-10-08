// Keep large downloadable evidence and program archives in the source commit.
// Local builds retain every static file; Pages builds opt in with an immutable SHA.
const path = require('node:path');
const revision = process.env.PAGES_ATTACHMENT_REVISION;
if (revision && !/^[a-f0-9]{40}$/.test(revision)) {
  throw new Error('PAGES_ATTACHMENT_REVISION must be a full Git commit SHA');
}
const staticRoot = path.resolve(__dirname, '../static');

function externalAttachment(relative) {
  const name = relative.split(path.sep).join('/').replace(/^\//, '');
  if (!revision || name.split('/').includes('..')) return null;
  const eligible = (name.startsWith('validation/effects/') && name.endsWith('.json'))
    || (name.startsWith('examples/') && /\.(zip|tar\.gz)$/.test(name));
  return eligible
    ? `https://raw.githubusercontent.com/dshanpi/edgeaccel-docs/${revision}/static/${name.split('/').map(encodeURIComponent).join('/')}`
    : null;
}

function attachmentUrl(url, documentPath) {
  if (!revision || typeof url !== 'string' || /^(?:https?:|data:|#)/.test(url)) return null;
  const [pathname, suffix = ''] = url.split(/(?=[?#])/s, 2);
  let resolved;
  if (pathname.startsWith('@site/static/')) resolved = path.join(staticRoot, decodeURIComponent(pathname.slice(13)));
  else if (pathname.startsWith('/')) resolved = path.join(staticRoot, decodeURIComponent(pathname.slice(1)));
  else resolved = path.resolve(path.dirname(documentPath), decodeURIComponent(pathname));
  const relative = path.relative(staticRoot, resolved);
  const target = externalAttachment(relative);
  return target ? target + suffix : null;
}

module.exports = {externalAttachment, attachmentUrl};
