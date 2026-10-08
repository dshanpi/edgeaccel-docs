import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';

export function checkWakeWordRecordings({root, run, record}) {
  assert.equal(run.modelId, 'OpenWakeWord.AXERA');
  assert.equal(record.dataset.repository, 'Picovoice/wake-word-benchmark');
  assert.equal(record.dataset.revision, '84919190fb1891bf0936dcb577d9268e467f876f');
  assert.equal(record.threshold, 0.5);
  assert.equal(record.cpuMel, true);
  assert.equal(record.qualityTaskComplete, false);
  assert.equal(record.actualCapacity, '16GB');
  const manifestItem = run.evidence.find(item => item.path.endsWith('/download-manifest.json'));
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'static', manifestItem.path), 'utf8'));
  const modelHashes = new Map(manifest.files.map(file => [file.path, file.verifiedHashes.sha256]));
  const runtime = fs.readFileSync(path.join(root, 'static/examples/openwakeword_card.py'));
  assert.equal(createHash('sha256').update(runtime).digest('hex'), record.runtimeSha256);
  assert.equal(record.samples.length, 329);
  assert.deepEqual(new Set(record.samples.map(sample => sample.sourcePath)), new Set(Array.from({length: 329}, (_, i) => `audio/alexa/${i}.flac`)));
  assert.equal(record.silenceControls.length, 6);
  let detected = 0, other = 0, frames = 0;
  const classifiers = ['alexa_v0.1', 'hey_jarvis_v0.1', 'hey_mycroft_v0.1', 'hey_rhasspy_v0.1', 'timer_v0.1', 'weather_v0.1'];
  for (const sample of [...record.samples, ...record.silenceControls]) {
    assert.equal(sample.repeatExact, true);
    assert.equal(sample.sample_rate, 16000);
    assert.equal(sample.frame_count, Math.ceil(sample.sample_count / 1280));
    assert.deepEqual(Object.keys(sample.frame_scores).sort(), [...classifiers].sort());
    const triggered = [];
    for (const key of classifiers) {
      const scores = sample.frame_scores[key];
      assert.equal(scores.length, sample.frame_count);
      assert(scores.every(values => values.length === (key === 'timer_v0.1' ? 7 : 1) && values.every(Number.isFinite)));
      const peak = Math.max(...scores.flatMap(values => key === 'timer_v0.1' ? values.slice(1) : values));
      if (peak >= record.threshold) triggered.push(key);
    }
    assert.deepEqual([...sample.triggeredModels].sort(), triggered.sort());
    frames += sample.frame_count;
    if (sample.audio === 'silence-4s.wav') {
      assert.equal(sample.sample_count, 64000);
      assert.equal(triggered.length, 0);
    } else {
      assert(/^[a-f0-9]{64}$/.test(sample.sourceSha256) && /^[a-f0-9]{64}$/.test(sample.audioSha256));
      assert.equal(sample.streamInfoPcmMd5Matched, true);
      const wavSamples = Math.round(sample.speechSeconds * 16000) + 32000;
      assert.equal(Math.round(sample.durationSeconds * 16000), wavSamples);
      // The official infer_clip pads the final 80 ms chunk before reporting sample_count.
      assert.equal(sample.sample_count, Math.ceil(wavSamples / 1280) * 1280);
      assert.equal(sample.expectedClassifierDetected, triggered.includes('alexa_v0.1'));
      if (sample.expectedClassifierDetected) detected++;
      if (triggered.some(key => key !== 'alexa_v0.1')) other++;
    }
  }
  assert.equal(record.alexaDetected, detected);
  assert.equal(record.alexaMissed, 329 - detected);
  assert.equal(record.clipsWithOtherClassActivations, other);
  assert.equal(record.sessions.length, 7);
  assert.deepEqual(new Set(record.sessions.map(session => session.model)), new Set(run.testedWeightFiles));
  for (const session of record.sessions) {
    assert.equal(session.modelSha256, modelHashes.get(session.model));
    assert.equal(session.runMilliseconds.length, frames * 2);
    assert.equal(session.allFinite, true);
  }
  assert.equal(record.nativeCalls, frames * 2 * 7);
}
