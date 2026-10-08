import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';

export function checkNativeCvVariants({root, run, record, variant}) {
  const file = url => path.join(root, 'static', url);
  const read = url => JSON.parse(fs.readFileSync(file(url), 'utf8'));
  const sha = url => createHash('sha256').update(fs.readFileSync(file(url))).digest('hex');
  assert(['YOLO11', 'YOLO11-Seg', 'yolo26'].includes(run.modelId));
  assert.equal(run.level, 'basic');
  assert.equal(record.modelId, run.modelId);
  assert.equal(record.revision, run.revision);
  assert.equal(record.actualCapacity, '16GB');
  assert.equal(record.provider, 'AXCL C++');
  assert.equal(record.rawTensorsCaptured, false);
  assert.equal(record.qualityAccepted, false);
  assert(record.originalFilesUnchanged);
  const manifest = read(run.evidence.find(e => e.path.endsWith('/download-manifest.json')).path);
  const runtime = read(run.evidence.find(e => e.path.endsWith('/deployment-result.json')).path).runtime;
  assert.equal(manifest.revision, run.revision);
  assert.equal(runtime.sourceRevision, 'cbfa4c76891758983ca2b0c99c11d6621d59af39');
  assert.equal(runtime.architecture, 'aarch64');
  assert.equal(runtime.nativeMockChecksPassed, 4);
  assert.equal(runtime.sourceFiles.length, 51);
  assert.equal(record.runtimeSourceRevision, runtime.sourceRevision);
  assert.equal(runtime.binaries.find(b => b.file === `bin/${record.binary}`)?.sha256, record.binarySha256);
  assert.equal(manifest.files.find(f => f.path === record.inputFile)?.verifiedHashes.sha256, record.inputSha256);
  assert.equal(sha(record.inputPath), record.inputSha256);
  assert.equal(sha(record.outputPath), record.outputSha256);
  assert(variant.previews.some(p => p.path === record.outputPath));
  assert.equal(record.sessions.length, 1);
  const session = record.sessions[0];
  assert.equal(manifest.files.find(f => f.path === session.model)?.verifiedHashes.sha256, session.sha256);
  assert.equal(session.allFinite, undefined, 'Native samples did not capture raw tensors');
  assert.equal(record.processes.length, 2);
  assert.deepEqual(record.metadata.inputs.map(i => [i.shape, i.dtype]), [[[1, 640, 640, 3], 'uint8']]);
  assert(record.metadata.outputs.length > 0);
  for (const process of record.processes) {
    assert.equal(process.exitCode, 0);
    assert.equal(process.warmupCalls, 5);
    assert.equal(process.timedCalls, 10);
    assert.equal(process.imageSha256, record.outputSha256);
    assert(process.apiEvents.length > 15 && process.apiEvents.every(e => e.returnCode === 0));
    const calls = process.apiEvents.filter(e => e.api === 'axclrtEngineExecute');
    assert.equal(calls.length, 15);
    assert(calls.every(e => Number.isFinite(e.milliseconds) && e.milliseconds >= 0));
    assert(process.apiEvents.some(e => e.api === 'axclrtMemcpy' && e.bytes > 0));
    assert(process.bootUnchanged && process.cardBootUnchanged && process.cardReturnedToIdle);
    assert.deepEqual(process.objects, record.processes[0].objects);
  }
  assert.deepEqual(session.runMilliseconds, record.processes.flatMap(p => p.apiEvents.filter(e => e.api === 'axclrtEngineExecute').map(e => e.milliseconds)));
  const counts = new Map();
  for (const object of record.processes[0].objects) {
    assert(Number.isInteger(object.classId) && object.classId >= 0 && object.classId < 80);
    assert(object.box.length === 4 && object.box.every(Number.isFinite));
    assert(object.percentRounded >= 0 && object.percentRounded <= 100);
    counts.set(object.label, (counts.get(object.label) ?? 0) + 1);
  }
  const countText = [...counts].sort((a, b) => a[0].localeCompare(b[0])).map(([label, n]) => `${label}: ${n}`).join('；');
  assert.deepEqual(variant.tables[0].rows, [[path.posix.basename(session.model), record.processes[0].objects.length, countText]]);
}
