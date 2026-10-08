import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';

// Recompute the complete, fixed cohort from retained per-frame outputs.
export function checkWakeWordNoise({root, run, record, variants}) {
  assert.equal(run.modelId, 'OpenWakeWord.AXERA');
  assert.equal(record.modelRevision, run.revision);
  assert.equal(record.provider, 'AXCLRTExecutionProvider');
  assert.equal(record.completed, true);
  assert.equal(record.threshold, 0.5);
  assert.equal(record.snrDb, 10);
  assert.equal(record.cpuMel, true);
  assert.equal(record.actualCapacity, '16GB');
  assert.equal(record.qualityTaskComplete, false);
  assert.equal(record.dataset.speechRevision, '84919190fb1891bf0936dcb577d9268e467f876f');
  assert.equal(record.dataset.noiseSource, 'https://zenodo.org/records/1227121');
  assert.equal(record.dataset.derivedAudioPublished, false);
  assert.equal(record.dataset.liveMicrophoneTested, false);
  const clean = variants.find(v => v.record.inferenceEvidence === 'axcl-real-recording-wake-word-scores')?.record;
  assert(clean && clean.samples.length === 329);
  const baseline = new Map(clean.samples.map(row => [`alexa-${path.basename(row.sourcePath, '.flac')}`, row]));
  assert.deepEqual({clips: record.clean.clips, detected: record.clean.detected, missed: record.clean.missed},
    {clips: 329, detected: clean.alexaDetected, missed: clean.alexaMissed});
  const md5 = new Map([
    ['DKITCHEN_16k.zip', 'md5:7ffbf52d7f4699f96927846103dc8788'],
    ['DLIVING_16k.zip', 'md5:46741384d9e434a0bd8b3ec1830b6052'],
    ['DWASHING_16k.zip', 'md5:7e5ee9437ce9409c5f9a779b6212a240'],
  ]);
  assert.equal(record.dataset.noiseArchives.length, 3);
  for (const file of record.dataset.noiseArchives) {
    assert.equal(file.upstreamMd5, md5.get(file.file));
    assert(/^[a-f0-9]{64}$/.test(file.sha256));
  }
  const classifiers = ['alexa_v0.1', 'hey_jarvis_v0.1', 'hey_mycroft_v0.1', 'hey_rhasspy_v0.1', 'timer_v0.1', 'weather_v0.1'];
  assert.equal(record.samples.length, 990);
  assert.equal(new Set(record.samples.map(r => r.id)).size, 990);
  assert.equal(record.silenceControls.length, 21);
  assert.equal(new Set(record.silenceControls.map(r => r.shard)).size, 21);
  const rows = [];
  let frames = 0;
  for (const row of [...record.samples, ...record.silenceControls]) {
    assert.equal(row.sample_rate, 16000);
    assert.equal(row.repeatExact, true);
    assert.equal(row.sample_count, Math.ceil(Math.round(row.durationSeconds * 16000) / 1280) * 1280);
    assert.equal(row.frame_count, row.sample_count / 1280);
    assert.deepEqual(Object.keys(row.frame_scores).sort(), [...classifiers].sort());
    assert(Number.isFinite(row.pipelineSeconds) && row.pipelineSeconds > 0);
    assert(Math.abs(row.realTimeFactor - row.pipelineSeconds / row.durationSeconds) < 1e-9);
    const peaks = Object.fromEntries(classifiers.map(key => {
      const scores = row.frame_scores[key];
      assert.equal(scores.length, row.frame_count);
      assert(scores.every(values => values.length === (key === 'timer_v0.1' ? 7 : 1) && values.every(Number.isFinite)));
      return [key, Math.max(...scores.flatMap(values => key === 'timer_v0.1' ? values.slice(1) : values))];
    }));
    const triggered = classifiers.filter(key => peaks[key] >= record.threshold);
    assert.deepEqual([...row.triggeredModels].sort(), [...triggered].sort());
    frames += row.frame_count;
    if (row.audio === 'silence-4s.wav') {
      assert.equal(row.sample_count, 64000);
      assert.equal(triggered.length, 0);
      continue;
    }
    assert(/^[a-f0-9]{64}$/.test(row.audioSha256));
    if (row.kind === 'noisy-positive') {
      const old = baseline.get(row.cleanId); assert(old);
      assert.equal(old.audioSha256, row.cleanWavSha256);
      assert.equal(row.durationSeconds, old.durationSeconds);
      assert.equal(row.cleanDetected, old.expectedClassifierDetected);
      assert.equal(row.cleanPeak, Math.max(...old.frame_scores['alexa_v0.1'].flat()));
      assert.equal(row.id, `${row.condition}-${row.cleanId}`);
      assert(Math.abs(row.achievedSnrDb - 10) < 0.02);
      assert(row.commonGain > 0 && row.commonGain <= 1 && row.noiseGain > 0);
      assert(Number.isSafeInteger(row.noiseStartSample) && row.noiseStartSample >= 0);
      rows.push({...row, detected: triggered.includes('alexa_v0.1'), other: triggered.filter(k => k !== 'alexa_v0.1')});
    } else {
      assert.equal(row.kind, 'unannotated-ambient-control');
      assert.equal(row.negativeLabelVerified, false);
      const source = record.dataset.noiseChannels.find(item => item.condition === row.condition);
      assert(source && row.audioSha256 === source.sha256);
      assert.equal(row.durationSeconds, source.durationSeconds);
      const summary = record.ambientControls.find(item => item.condition === row.condition);
      assert(summary && summary.negativeLabelVerified === false);
      assert.equal(summary.wavSha256, row.audioSha256);
      assert.equal(summary.inputSeconds, row.durationSeconds);
      assert.deepEqual(summary.peaks, peaks);
      assert.deepEqual([...summary.triggeredModels].sort(), [...triggered].sort());
    }
  }
  assert.equal(rows.length, 987);
  assert.equal(record.ambientControls.length, 3);
  assert.deepEqual(new Set(record.ambientControls.map(r => r.condition)), new Set(['dkitchen', 'dliving', 'dwashing']));
  assert.equal(record.conditions.length, 3);
  assert.deepEqual(record.conditions.map(r => r.condition), ['dkitchen', 'dliving', 'dwashing']);
  for (const summary of record.conditions) {
    const selected = rows.filter(r => r.condition === summary.condition);
    assert.equal(selected.length, 329);
    assert.deepEqual(new Set(selected.map(r => r.cleanId)), new Set(baseline.keys()));
    const detected = selected.filter(r => r.detected).length;
    const pairs = {}, others = {};
    for (const r of selected) {
      const key = `clean-${r.cleanDetected ? 'hit' : 'miss'}/noisy-${r.detected ? 'hit' : 'miss'}`;
      pairs[key] = (pairs[key] ?? 0) + 1;
      for (const key of r.other) others[key] = (others[key] ?? 0) + 1;
    }
    assert.equal(summary.clips, 329);
    assert.equal(summary.alexaDetected, detected);
    assert.equal(summary.alexaMissed, 329 - detected);
    assert.equal(summary.detectionFraction, detected / 329);
    assert.equal(summary.clipsWithOtherClassActivations, selected.filter(r => r.other.length).length);
    assert.deepEqual(summary.pairedOutcomes, pairs);
    assert.deepEqual(summary.otherActivationCounts, others);
    assert.deepEqual(new Set(summary.missedIds), new Set(selected.filter(r => !r.detected).map(r => r.cleanId)));
  }
  const manifestItem = run.evidence.find(item => item.path.endsWith('/download-manifest.json'));
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'static', manifestItem.path), 'utf8'));
  const hashes = new Map(manifest.files.map(f => [f.path, f.verifiedHashes.sha256]));
  assert.equal(record.sessions.length, 7);
  assert.deepEqual(new Set(record.sessions.map(s => s.model)), new Set(run.testedWeightFiles));
  for (const session of record.sessions) {
    assert.equal(session.modelSha256, hashes.get(session.model));
    assert.equal(session.runMilliseconds.length, frames * 2);
    assert.equal(session.loadSecondsByShard.length, 21);
    assert.equal(session.allFinite, true);
  }
  assert.equal(record.nativeCalls, frames * 2 * 7);
  const runtime = fs.readFileSync(path.join(root, 'static/examples/openwakeword_card.py'));
  assert.equal(createHash('sha256').update(runtime).digest('hex'), record.runtimeSha256);
}
