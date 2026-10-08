import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';

export function checkNhwcVision({root, run, record, variant}) {
  const digest = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  assert.equal(record.modelId, run.modelId);
  assert.equal(record.revision, run.revision);
  assert.equal(record.actualCapacity, '16GB');
  assert.equal(record.inputLayout, 'NHWC');
  assert.equal(record.independentRuns, 3);
  assert(record.originalFilesUnchanged && record.rawOutputsExact && record.visualizationsExact && record.customerCommandVerified);
  assert.equal(record.sessions.length, 1);
  const session = record.sessions[0];
  assert.equal(session.runMilliseconds.length, 3);
  assert.equal(record.calls.length, 3);
  assert.deepEqual(record.calls.map(c => c.milliseconds), session.runMilliseconds);
  assert.equal(new Set(record.calls.map(c => c.inputSha256)).size, 1);
  assert(record.calls.every(c => /^[a-f0-9]{64}$/.test(c.inputSha256) && /^[a-f0-9]{64}$/.test(c.outputSha256)));
  const manifestItem = run.evidence.find(e => e.path.endsWith('/download-manifest.json'));
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'static', manifestItem.path), 'utf8'));
  assert.equal(manifest.revision, record.revision);
  const find = name => manifest.files.find(f => f.path === name);
  assert.equal(find(session.model)?.verifiedHashes.sha256, session.sha256);
  assert.equal(find(record.sourceScript)?.verifiedHashes.sha256, record.sourceScriptSha256);
  assert.equal(find(record.inputFile)?.verifiedHashes.sha256, record.inputSha256);
  assert.equal(digest(path.join(root, 'static', record.inputPath)), record.inputSha256);
  assert.deepEqual(record.inputShape.length, 4);
  assert.equal(record.inputShape.at(-1), 3);
  assert.equal(record.adapterSha256, record.customerBundleFiles['_vision_nhwc_runtime.py']);
  for (const output of record.outputs) {
    const previews = variant.previews.filter(p => p.path.includes('/outputs/'));
    assert(previews.some(p => digest(path.join(root, 'static', p.path)) === output.sha256));
  }
  if (record.case === 'plate-recognition') {
    assert.equal(record.outputs.length, 0);
    assert.equal(record.consoleText, 'Plate: [苏A8A68Y], score: 0.9997, color: [blue], score:1.0000');
    assert.deepEqual(variant.tables[0].rows, [['苏A8A68Y', '0.9997', 'blue', '1.0000']]);
  } else assert(record.outputs.length > 0);
  if (record.case === 'person-car-max') assert(record.colorOrder.includes('BGR'));
}
