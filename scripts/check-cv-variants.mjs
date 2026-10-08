import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';

export function checkCvVariants({root, run, record, variant}) {
  const digest = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  const asset = file => path.join(root, 'static', file);
  assert.equal(record.modelId, run.modelId);
  assert.equal(record.revision, run.revision);
  assert.equal(record.actualCapacity, '16GB');
  assert([2, 3].includes(record.runsPerWeight));
  assert.equal(record.qualityAccepted, false);
  assert.equal(run.level, 'basic', 'Reproducible detections with observed misses cannot become a quality pass');
  assert(record.originalFilesUnchanged && record.weightResults.length === record.sessions.length);
  const manifestItem = run.evidence.find(e => e.path.endsWith('/download-manifest.json'));
  const manifest = JSON.parse(fs.readFileSync(asset(manifestItem.path), 'utf8'));
  assert.equal(manifest.revision, record.revision);
  const find = name => manifest.files.find(f => f.path === name);
  assert.equal(find(record.sourceScript)?.verifiedHashes.sha256, record.sourceScriptSha256);
  assert.equal(find(record.inputFile)?.verifiedHashes.sha256, record.inputSha256);
  assert.equal(digest(asset(record.inputPath)), record.inputSha256);
  assert.equal(digest(asset(record.outputPath)), record.outputSha256);
  assert(variant.previews.some(p => p.path === record.outputPath));
  for (const session of record.sessions) {
    const result = record.weightResults.find(r => r.weight === session.model);
    assert.equal(find(session.model)?.verifiedHashes.sha256, session.sha256);
    assert.equal(result.independentProcesses, record.runsPerWeight);
    assert(result.rawOutputsExact);
    assert.equal(result.imageSha256, record.outputSha256);
    assert.equal(session.runMilliseconds.length, record.runsPerWeight * (result.callsPerProcess ?? 1));
    assert.equal(result.metadata.length, 1);
    assert(result.metadata[0].inputs.length > 0 && result.metadata[0].outputs.length > 0);
    if (result.detectionObjects) {
      assert.equal(run.modelId, 'YOLOv8');
      assert.equal(record.runsPerWeight, 2);
      assert(result.postprocessReplayInputExact && result.postprocessReplayImageExact);
      const counts = new Map();
      for (const object of result.detectionObjects) {
        assert.equal(object.box.length, 4);
        assert(object.box.every(Number.isFinite));
        assert(object.confidence >= 0 && object.confidence <= 1);
        assert(Number.isInteger(object.classId) && object.classId >= 0 && object.classId < 80);
        assert(typeof object.label === 'string' && object.label.length > 0);
        const current = counts.get(object.classId) ?? {label: object.label, count: 0};
        assert.equal(current.label, object.label);
        current.count++;
        counts.set(object.classId, current);
      }
      const countText = [...counts.entries()].sort((a, b) => a[0] - b[0]).map(([, item]) => `${item.label}: ${item.count}`).join('；');
      const tableRow = variant.tables[0].rows.find(row => row[0] === path.posix.basename(session.model));
      assert.deepEqual(tableRow?.slice(1), [result.detectionObjects.length, countText]);
    } else if (result.segmentationObjects) {
      assert(['yolo26-seg', 'YOLOv8-Seg'].includes(run.modelId));
      assert.equal(record.runsPerWeight, 2);
      assert(result.postprocessReplayInputExact && result.postprocessReplayImageExact);
      assert.match(result.maskSha256, /^[a-f0-9]{64}$/);
      assert.equal(result.maskPath, undefined, 'Raw mask arrays remain in the internal evidence archive');
      assert.equal(result.maskShape[0], result.segmentationObjects.length);
      assert.deepEqual(result.maskShape.slice(1), [1080, 810]);
      for (const object of result.segmentationObjects) {
        assert.equal(object.box.length, 4);
        assert(object.box.every(Number.isFinite));
        assert(object.confidence >= 0 && object.confidence <= 1);
        if (run.modelId === 'yolo26-seg') assert([0, 5].includes(object.classId));
        else {
          assert(Number.isInteger(object.classId) && object.classId >= 0 && object.classId < 80);
          assert(typeof object.label === 'string' && object.label.length > 0);
        }
        assert(Number.isInteger(object.maskPixels) && object.maskPixels > 0 && object.maskPixels <= 1080 * 810);
        assert.equal(object.maskBounds.length, 4);
        const [x1, y1, x2, y2] = object.maskBounds;
        assert(x1 >= 0 && y1 >= 0 && x2 > x1 && y2 > y1 && x2 <= 810 && y2 <= 1080);
      }
      const tableRow = variant.tables[0].rows.find(row => row[0] === path.posix.basename(session.model));
      if (run.modelId === 'yolo26-seg') {
        assert.deepEqual(tableRow?.slice(1), [result.segmentationObjects.filter(o => o.classId === 0).length, result.segmentationObjects.filter(o => o.classId === 5).length]);
      } else {
        const counts = new Map();
        for (const object of result.segmentationObjects) {
          const current = counts.get(object.classId) ?? {label: object.label, count: 0};
          assert.equal(current.label, object.label);
          current.count++;
          counts.set(object.classId, current);
        }
        const countText = [...counts.entries()].sort((a, b) => a[0] - b[0]).map(([, item]) => `${item.label}: ${item.count}`).join('；');
        assert.deepEqual(tableRow?.slice(1), [result.segmentationObjects.length, countText]);
      }
    } else if (result.posePersons) {
      assert(['yolo26-pose', 'YOLOv8-Pose'].includes(run.modelId));
      assert.equal(record.runsPerWeight, 2);
      assert(result.postprocessReplayInputExact && result.postprocessReplayImageExact);
      assert(result.posePersons.length > 0);
      for (const person of result.posePersons) {
        assert.equal(person.box.length, 4);
        assert(person.box.every(Number.isFinite));
        assert(person.confidence >= 0 && person.confidence <= 1);
        assert.equal(person.keypoints.length, 17);
        assert(person.keypoints.every(k => k.length === 3 && k.every(Number.isFinite) && k[2] >= 0 && k[2] <= 1));
        assert.equal(person.drawnKeypointsAboveHalf, person.keypoints.filter(k => k[2] > 0.5).length);
      }
      const tableRow = variant.tables[0].rows.find(row => row[0] === path.posix.basename(session.model));
      const leftToRight = [...result.posePersons].sort((a, b) => a.box[0] - b.box[0]);
      assert.deepEqual(tableRow?.slice(1), [result.posePersons.length, leftToRight.map(p => p.drawnKeypointsAboveHalf).join(' / ')]);
    } else if (result.detectedBoxes) {
      assert(Object.values(result.detectedBoxes).every(n => Number.isInteger(n) && n >= 0));
      const tableRow = variant.tables[0].rows.find(row => row[0] === path.posix.basename(session.model));
      assert.deepEqual(tableRow?.slice(1), [result.detectedBoxes.ship, result.detectedBoxes.harbor]);
    } else {
      assert(['Drone-axera', 'RTMPose'].includes(run.modelId));
      assert.equal(record.runsPerWeight, 3);
      assert(record.customerCommandVerified);
      assert.equal(result.callsPerProcess, run.modelId === 'RTMPose' ? 13 : 1);
    }
  }
}
