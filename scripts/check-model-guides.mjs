import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {displayedRuns} from './model-effects.mjs';
import {checkCompiledEmbedding} from './check-compiled-embedding.mjs';
import {checkWakeWordRecordings} from './check-wake-word-recordings.mjs';
import {checkWakeWordNoise} from './check-wake-word-noise.mjs';
import {checkNhwcVision} from './check-nhwc-vision.mjs';
import {checkCvVariants} from './check-cv-variants.mjs';
import {checkNativeCvVariants} from './check-native-cv-variants.mjs';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = file => JSON.parse(fs.readFileSync(path.join(root,file),'utf8'));
const source = read('src/data/modelSourceSnapshot.json');
const facts = read('src/data/modelDeployments.json');
const catalog = read('src/data/models.json');
const validation = fs.existsSync(path.join(root, 'src/data/modelValidationResults.json'))
  ? read('src/data/modelValidationResults.json')
  : {schemaVersion: 1, environments: [], runs: []};
assert.equal(validation.schemaVersion, 1, 'Unsupported validation schema');
assert(Array.isArray(validation.environments), 'Validation environments must be an array');
assert(Array.isArray(validation.runs), 'Validation runs must be an array');
const modelFacts = new Map(facts.map(model => [model.id, model]));
const environments = new Map(validation.environments.map(environment => [environment.id, environment]));
assert.equal(environments.size, validation.environments.length, 'Duplicate validation environment IDs');
const nonempty = value => typeof value === 'string' && value.trim().length > 0;
for (const environment of validation.environments) {
  assert(nonempty(environment.id) && nonempty(environment.label), 'Validation environment needs an ID and label');
  assert(Array.isArray(environment.details) && environment.details.length, `Missing environment details: ${environment.id}`);
  for (const detail of environment.details) assert(nonempty(detail.name) && String(detail.value ?? '').trim(), `Invalid environment detail: ${environment.id}`);
}
assert.equal(new Set(validation.runs.map(run => run.id)).size, validation.runs.length, 'Duplicate validation run IDs');
for (const run of validation.runs) {
  const model = modelFacts.get(run.modelId);
  assert(nonempty(run.id), 'Validation run needs an ID');
  assert(model && model.kind !== 'resource', `Validation refers to unknown model or resource: ${run.modelId}`);
  assert(environments.has(run.environmentId), `Unknown environment in ${run.id}`);
  assert(['passed', 'failed', 'blocked'].includes(run.status), `Invalid validation status: ${run.id}`);
  assert(['basic', 'correctness'].includes(run.level), `Invalid validation level: ${run.id}`);
  if (run.scope === 'local-components') {
    assert(run.modelId === 'openclaw-ax8850-qqbot-media' && run.status === 'blocked' && run.level === 'basic', `Partial components cannot count as a passed application: ${run.id}`);
    assert(run.wholeApplicationAccepted === false && run.qualityAccepted === false, `Partial application scope differs: ${run.id}`);
    assert(run.evidence.some(e => e.path.endsWith('/deployment-result.json')), `Missing component evidence: ${run.id}`);
  }
  assert(typeof run.date === 'string' && /^\d{4}-\d{2}-\d{2}(?:T.*)?$/.test(run.date) && !Number.isNaN(Date.parse(run.date)), `Invalid validation date: ${run.id}`);
  assert.equal(run.revision, model.sha, `Test revision differs from documented model revision: ${run.id}`);
  if (run.downloadScope) {
    assert.equal(run.downloadScope, 'supplement', `Unknown optional download scope: ${run.id}`);
    assert(model.supplementGuide && run.testedWeightFiles?.length, `Optional weights need their own deployment steps: ${run.id}`);
    const guide = fs.readFileSync(path.join(root, 'scripts/model-recipes', model.supplementGuide), 'utf8');
    for (const weight of run.testedWeightFiles) assert(guide.includes(weight), `Optional weight missing from download steps: ${run.id}: ${weight}`);
  }
  if (run.testedDerivedWeights) checkCompiledEmbedding({root, model, run});
  if (run.testedWeightFiles) {
    assert(Array.isArray(run.testedWeightFiles) && run.testedWeightFiles.length, `Empty tested file list: ${run.id}`);
    assert(run.testedWeightFiles.every(file => model.files.includes(file) && file.endsWith('.axmodel')), `Tested weight absent from source: ${run.id}`);
  }
  if (run.testedCompanionWeights) {
    assert(Array.isArray(run.testedCompanionWeights) && run.testedCompanionWeights.length, `Empty companion weights: ${run.id}`);
    const keys = new Set();
    for (const weight of run.testedCompanionWeights) {
      const companion = facts.find(m => m.repo === weight.repo);
      assert(companion && companion.sha === weight.revision && companion.files.includes(weight.file) && weight.file.endsWith('.axmodel'), `Unknown companion weight: ${run.id}`);
      assert(/^[a-f0-9]{64}$/.test(weight.sha256), `Missing companion SHA-256: ${run.id}`);
      const key = `${weight.repo}:${weight.revision}:${weight.file}`;
      assert(!keys.has(key), `Duplicate companion weight: ${run.id}`);
      keys.add(key);
    }
  }
  assert(nonempty(run.summary), `Missing effect summary: ${run.id}`);
  assert(!run.command, `Internal test command must not be published: ${run.id}`);
  assert(Array.isArray(run.metrics), `Missing metrics array: ${run.id}`);
  for (const metric of run.metrics) assert(nonempty(metric.name) && String(metric.value ?? '').trim() && nonempty(metric.scope), `Invalid test metric: ${run.id}`);
  assert(Array.isArray(run.limitations) && run.limitations.every(nonempty), `Invalid test limitations: ${run.id}`);
  assert(Array.isArray(run.evidence) && run.evidence.length, `No evidence recorded: ${run.id}`);
  for (const evidence of run.evidence) {
    assert(nonempty(evidence.label) && typeof evidence.path === 'string' && evidence.path.startsWith('/validation/'), `Invalid evidence reference: ${run.id}`);
    assert(evidence.path.startsWith('/validation/effects/'), `Internal diagnostic asset must not be published: ${run.id}`);
    const reviewedMimoReply = run.modelId === 'Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4' && /\/(description|count|video)-full-response\.txt$/.test(evidence.path);
    const reviewedEmbeddingQuality = run.modelId === 'Qwen3-Embedding-0.6B-GPTQ-Int8'
      && ['/validation/effects/qwen3-embedding-int8-20261004/bilingual-input.json', '/validation/effects/qwen3-embedding-int8-20261004/retrieval-quality.json', '/validation/effects/qwen3-embedding-int8-20261004/external-retrieval.json'].includes(evidence.path);
    assert(reviewedMimoReply || reviewedEmbeddingQuality || /\.(png|jpe?g|webp|gif|wav|mp3|mp4)$/i.test(evidence.path) || ['api.json', 'download-manifest.json', 'media-manifest.json', 'speaker-result.json', 'sensevoice-result.json', 'tts-result.json', 'classification-result.json', 'bird-result.json', 'punctuation-result.json', 'qrcode-result.json', 'decision-result.json', 'enhancement-result.json', 'deployment-result.json', 'text-result.json', 'embedding-result.json'].includes(path.basename(evidence.path)), `Unexpected customer attachment: ${evidence.path}`);
    assert(!/[\\?#]/.test(evidence.path) && !evidence.path.split('/').includes('..'), `Unsafe evidence path: ${run.id}`);
    const evidencePath = path.resolve(root, 'static', '.' + evidence.path);
    const evidenceRoot = path.resolve(root, 'static', 'validation') + path.sep;
    assert(evidencePath.startsWith(evidenceRoot), `Evidence escapes validation directory: ${run.id}`);
    assert(fs.existsSync(evidencePath) && fs.statSync(evidencePath).isFile(), `Evidence file missing: ${evidence.path}`);
    assert(fs.statSync(evidencePath).size > 0, `Evidence file is empty: ${evidence.path}`);
    if (path.basename(evidence.path) === 'bird-result.json') {
      const result = JSON.parse(fs.readFileSync(evidencePath, 'utf8'));
      assert.equal(result.kind, 'bird-classification');
      assert.equal(result.modelId, run.modelId);
      assert.equal(result.revision, run.revision);
      assert.equal(result.date, run.date);
      assert.equal(result.classCount, 1486);
      assert.equal(result.top5.length, 5);
      assert.equal(new Set(result.top5.map(row => row.classIndex)).size, 5);
      for (const [i, row] of result.top5.entries()) {
        assert.equal(row.rank, i + 1);
        assert(Number.isInteger(row.classIndex) && row.classIndex >= 0 && row.classIndex < result.classCount);
        assert(/^\d{5}_/.test(row.className) && /^0\.\d{4}$/.test(row.reportedScore));
      }
      const manifest = read('static' + run.evidence.find(item => item.path.endsWith('/download-manifest.json')).path);
      assert.equal(result.labelSourceSha256, manifest.files.find(file => file.path === 'class_name.txt').verifiedHashes.sha256);
      const input = run.evidence.find(item => item.path.includes('/inputs/') && /\.jpg$/.test(item.path));
      assert.equal(result.inputSha256, createHash('sha256').update(fs.readFileSync(path.join(root, 'static', input.path))).digest('hex'));
      assert(nonempty(result.scorePrecision) && nonempty(result.preprocessing) && result.limitations.length > 0);
    }
    if (path.basename(evidence.path) === 'api.json') {
      const api = JSON.parse(fs.readFileSync(evidencePath, 'utf8'));
      if (api.conversations) {
        assert.equal(api.modelId, run.modelId, `API model mismatch: ${run.id}`);
        assert.equal(api.revision, run.revision, `API revision mismatch: ${run.id}`);
        assert(api.completed === true && api.provider === 'AXCL C++', `Incomplete card API result: ${run.id}`);
        assert(Number.isFinite(api.startupSeconds) && api.startupSeconds > 0, `Invalid startup duration: ${run.id}`);
        for (const item of api.requests) {
          assert(item.endpoint === '/v1/chat/completions' && item.httpStatus === 200, `Invalid API response: ${run.id}`);
          assert(Number.isFinite(item.requestSeconds) && item.requestSeconds > 0, `Invalid request duration: ${run.id}`);
          assert(nonempty(item.observation) && nonempty(item.response.choices[0].message.content), `Missing API reply assessment: ${run.id}`);
          assert(item.response.choices[0].finish_reason === 'stop', `Incomplete API reply: ${run.id}`);
        }
        for (const conversation of api.conversations) {
          assert(nonempty(conversation.observation) && conversation.requestIndices.length >= 2, `Missing API conversation: ${run.id}`);
          let history = [];
          for (const index of conversation.requestIndices) {
            assert(Number.isInteger(index) && index >= 0 && index < api.requests.length, `Invalid conversation reference: ${run.id}`);
            const item = api.requests[index];
            const messages = item.request.messages;
            assert.equal(messages.length, history.length + 1, `Conversation history length differs: ${run.id}`);
            assert.deepEqual(messages.slice(0, -1), history, `Conversation history differs: ${run.id}`);
            assert(messages.at(-1).role === 'user' && nonempty(messages.at(-1).content), `Missing user turn: ${run.id}`);
            history = [...messages, {role: 'assistant', content: item.response.choices[0].message.content}];
          }
        }
      }
    }
    if (path.basename(evidence.path) === 'text-result.json') {
      const result = JSON.parse(fs.readFileSync(evidencePath, 'utf8'));
      assert.equal(result.modelId, run.modelId, `Text result model mismatch: ${run.id}`);
      assert.equal(result.revision, run.revision, `Text result revision mismatch: ${run.id}`);
      const pythonText = result.kind === 'python-text' && result.provider === 'AXCLRTExecutionProvider';
      assert(result.completed === true && (result.provider === 'AXCL C++' || pythonText), `Incomplete card text result: ${run.id}`);
      assert(result.samples?.length > 0, `Missing text samples: ${run.id}`);
      for (const sample of result.samples) {
        assert(nonempty(sample.input) && nonempty(sample.output) && nonempty(sample.observation), `Missing text or assessment: ${run.id}`);
        if (sample.variantLabel !== undefined) assert(nonempty(sample.variantLabel), `Invalid text variant label: ${run.id}`);
        assert(sample.exitCode === 0 && Number.isFinite(sample.processSeconds) && sample.processSeconds > 0, `Invalid text process result: ${run.id}`);
        if (sample.requestSeconds !== undefined) assert(Number.isFinite(sample.requestSeconds) && sample.requestSeconds > 0, `Invalid text request duration: ${run.id}`);
        if (sample.framePaths) {
          assert(Array.isArray(sample.framePaths) && sample.framePaths.length > 1 && new Set(sample.framePaths).size === sample.framePaths.length, `Invalid input frame sequence: ${run.id}`);
          for (const frame of sample.framePaths) assert(run.evidence.some(item => item.path === frame && /\.(png|jpe?g)$/i.test(frame)), `Input frame missing from evidence: ${run.id}`);
        }
        if (pythonText) {
          assert(sample.eosReached === true, `Python text did not reach EOS: ${run.id}`);
          assert(Array.isArray(sample.sessions) && sample.sessions.length === run.testedWeightFiles.length, `Missing Python text sessions: ${run.id}`);
          assert.deepEqual(sample.sessions.map(session => session.model).sort(), [...run.testedWeightFiles].sort(), `Python text weight mapping mismatch: ${run.id}`);
          for (const session of sample.sessions) {
            assert(session.providerActual === 'AXCLRTExecutionProvider' && session.allFinite === true, `Invalid Python text backend or output: ${run.id}`);
            assert(Object.values(session.shapeGroupCalls ?? {}).some(count => Number.isInteger(count) && count > 0), `Python text session was not executed: ${run.id}`);
          }
        }
      }
      for (const conversation of result.conversations ?? []) {
        assert(conversation.exitCode === 0 && conversation.sameSession === true, `Invalid conversation session: ${run.id}`);
        assert(Number.isFinite(conversation.processSeconds) && conversation.processSeconds > 0, `Invalid conversation duration: ${run.id}`);
        assert(Array.isArray(conversation.turns) && conversation.turns.length >= 2, `Missing conversation turns: ${run.id}`);
        for (const turn of conversation.turns) {
          assert(nonempty(turn.input) && nonempty(turn.output) && nonempty(turn.observation), `Missing conversation text: ${run.id}`);
          assert(Number.isFinite(turn.nativeTtftMs) && turn.nativeTtftMs >= 0, `Missing conversation timing: ${run.id}`);
        }
      }
    }
    if (path.basename(evidence.path) === 'deployment-result.json') {
      const result = JSON.parse(fs.readFileSync(evidencePath, 'utf8'));
      assert.equal(result.modelId, run.modelId, `Result model mismatch: ${run.id}`);
      assert.equal(result.revision, run.revision, `Result revision mismatch: ${run.id}`);
      assert(result.variants?.length, `Result has no variants: ${run.id}`);
      for (const variant of result.variants) {
        if (variant.record?.inferenceEvidence === 'fixed-nhwc-vision-samples') checkNhwcVision({root, run, record: variant.record, variant});
        if (variant.record?.inferenceEvidence === 'original-cv-variant-samples') checkCvVariants({root, run, record: variant.record, variant});
        assert(nonempty(variant.label) && nonempty(variant.observation), `Missing variant explanation: ${run.id}`);
        assert(variant.record?.completed === true, `Incomplete deployment result: ${run.id}`);
        assert(['AXCLRTExecutionProvider', 'AXCL C++', 'AXCL C API'].includes(variant.record.provider), `Non-card result: ${run.id}`);
        if (variant.record.inferenceEvidence === 'axcl-real-recording-wake-word-scores') {
          checkWakeWordRecordings({root, run, record: variant.record});
        }
        if (variant.record.inferenceEvidence === 'axcl-noisy-real-recording-wake-word-scores') {
          checkWakeWordNoise({root, run, record: variant.record, variants: result.variants});
        }
        const nativeCv = variant.record.inferenceEvidence === 'original-native-cv-variants';
        if (nativeCv) checkNativeCvVariants({root, run, record: variant.record, variant});
        const nativeApplication = variant.record.inferenceEvidence === 'native-return-codes-and-application-output';
        const nativeSpeech = variant.record.inferenceEvidence === 'native-return-codes-and-synthesized-audio';
        const nativeVoiceDesign = nativeSpeech && run.modelId === 'Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650';
        const nativeEmbeddings = variant.record.inferenceEvidence === 'native-return-codes-and-http-embeddings';
        const nativeCliVision = variant.record.inferenceEvidence === 'native-return-codes-and-cli-vision';
        const nativeQwen25 = variant.record.inferenceEvidence === 'qwen25-native-cli-and-http-tokenizer';
        const nativeMimo = variant.record.inferenceEvidence === 'mimo-official-cli-and-http-tokenizer';
        const nativeQwen3Fixed = variant.record.inferenceEvidence === 'qwen3-native-cli-with-verified-cache-and-eos';
        const nativeChat = variant.record.inferenceEvidence === 'native-return-codes-and-http-chat';
        const nativeReconstruction = variant.record.inferenceEvidence === 'native-return-codes-and-reconstruction-output';
        const nativeVoice = variant.record.inferenceEvidence === 'voice-websocket-and-native-axcl';
        const nativeVideoAgent = variant.record.inferenceEvidence === 'videoagent-ui-index-query-and-native-axcl';
        const nativeOpenClaw = variant.record.inferenceEvidence === 'openclaw-local-media-and-native-axcl';
        if (nativeOpenClaw) {
          const record = variant.record;
          assert(run.scope === 'local-components' && record.customerPackageTested && record.cleanShutdown && record.wholeApplicationAccepted === false && record.qualityAccepted === false && record.actual8GBTested === false, `Invalid local media scope: ${run.id}`);
          assert.deepEqual(result.variants.map(v => v.record.component).sort(), ['asr', 'image', 'native-video', 'tts']);
          const manifest = read('static' + run.evidence.find(e => e.path.endsWith('/download-manifest.json')).path);
          assert.equal(manifest.files.length, 874);
          assert.equal(record.verifiedModelFiles, 874);
          assert.equal(record.pipelineSessions.length, 43);
          assert.deepEqual(record.pipelineSessions.map(s => s.model).sort(), [...run.testedWeightFiles].sort());
          for (const session of record.pipelineSessions) {
            const file = manifest.files.find(f => f.path === session.model);
            assert(file && file.verifiedHashes.sha256 === session.sha256 && session.hostTransferSha256 === session.sha256, `Local media model bytes differ: ${run.id}`);
            assert(session.allReturnCodesZero && session.calls > 0 && session.loads === session.unloads && session.loads > 0, `Local media lifecycle incomplete: ${run.id}`);
          }
          assert.equal(record.totalCalls, record.pipelineSessions.reduce((n, s) => n + s.calls, 0));
          assert.equal(createHash('sha256').update(fs.readFileSync(path.join(root, 'static/examples/openclaw-media-axcl-20261004.zip'))).digest('hex'), record.packageSha256);
          for (const media of record.mediaFiles) {
            assert(run.evidence.some(e => e.path === media.path), `Missing local media file: ${run.id}`);
            assert.equal(createHash('sha256').update(fs.readFileSync(path.join(root, 'static', media.path))).digest('hex'), media.sha256);
          }
          for (const request of record.requests) {
            assert(request.exitCode === 0 && request.httpStatus === 200 && request.visionExecutions === (request.mode === 'image' ? 1 : 2), `Local vision request incomplete: ${run.id}`);
            assert(request.postExecutions > 0 && request.postExecutions < request.maxTokens && request.finishReason === 'stop', `Local vision reply truncated: ${run.id}`);
            assert(request.inputType === (request.mode === 'image' ? 'image_url' : 'video_url'), `Wrong native media type: ${run.id}`);
          }
          for (const sample of variant.textSamples ?? []) assert(nonempty(sample.input) && nonempty(sample.output) && nonempty(sample.observation) && record.outputs.includes(sample.output), `Displayed media output differs: ${run.id}`);
          for (const audio of record.audioOutputs) {
            const bytes = fs.readFileSync(path.join(root, 'static', audio.path));
            assert(bytes.subarray(0, 4).toString() === 'RIFF' && bytes.subarray(8, 12).toString() === 'WAVE');
            assert(audio.sampleRate === 24000 && audio.channels === 1 && audio.frames > 0 && audio.seconds === audio.frames / 24000);
            const chunks = new Map();
            for (let offset = 12; offset + 8 <= bytes.length;) {
              const size = bytes.readUInt32LE(offset + 4);
              assert(offset + 8 + size <= bytes.length);
              chunks.set(bytes.subarray(offset, offset + 4).toString(), bytes.subarray(offset + 8, offset + 8 + size));
              offset += 8 + size + (size % 2);
            }
            const fmt = chunks.get('fmt '), pcm = chunks.get('data');
            assert(fmt && pcm && fmt.readUInt16LE(0) === 1 && fmt.readUInt16LE(2) === 1 && fmt.readUInt32LE(4) === 24000 && fmt.readUInt16LE(14) === 16);
            assert(pcm.length === audio.frames * 2 && pcm.some(value => value !== 0), `Truncated or silent local speech: ${run.id}`);
          }
        } else if (nativeVideoAgent) {
          const record = variant.record;
          assert(run.modelId === 'VideoAgent-AX650N' && record.customerPackageTested && record.freshIndex && record.cleanShutdown && record.actual8GBTested === false, 'Incomplete VideoAgent application check: ' + run.id);
          const manifest = read('static' + run.evidence.find(e => e.path.endsWith('/download-manifest.json')).path);
          assert(manifest.files.length === 105 && record.filesBefore.length === 105 && record.filesAfter.length === 105, 'Incomplete VideoAgent file coverage: ' + run.id);
          assert.deepEqual(record.filesBefore, record.filesAfter, 'VideoAgent files changed: ' + run.id);
          for (const file of record.filesBefore) {
            const sourceFile = manifest.files.find(f => f.path === file.role + '/' + file.path);
            assert(sourceFile && sourceFile.verifiedHashes.sha256 === file.sha256, 'VideoAgent file hash differs: ' + run.id);
          }
          const expectedWeights = manifest.files.filter(f => f.path.endsWith('.axmodel'));
          assert(expectedWeights.length === 90 && record.pipelineSessions.length === 90, 'Missing VideoAgent companion models: ' + run.id);
          assert.deepEqual(record.pipelineSessions.map(s => s.model).sort(), expectedWeights.map(f => f.path).sort(), 'VideoAgent execution coverage differs: ' + run.id);
          for (const session of record.pipelineSessions) {
            assert(expectedWeights.find(f => f.path === session.model)?.verifiedHashes.sha256 === session.sha256 && session.calls > 0 && session.released && session.allReturnCodesZero, 'Unverified VideoAgent execution: ' + run.id);
          }
          assert(record.totalCalls === record.pipelineSessions.reduce((n, s) => n + s.calls, 0), 'VideoAgent execution total differs: ' + run.id);
          assert(record.httpRequests.length === 71 && record.httpRequests.every(r => r.status === 200 && /^[a-f0-9]{64}$/.test(r.requestSha256) && /^[a-f0-9]{64}$/.test(r.responseSha256)), 'Incomplete VideoAgent HTTP evidence: ' + run.id);
          assert(record.asrHttpRequests === 18 && record.asrNativeExecutions === 19 && record.normalizedInputSamples === 2902400 && record.allUploadedPcmReachedNpuChunksBitExactly, 'Incomplete VideoAgent audio coverage: ' + run.id);
          assert(record.captionRequests === 19 && record.captions.length === 19 && record.captions.every(c => c.postExecutions > 0 && c.postExecutions < c.maxTokens), 'Truncated VideoAgent caption: ' + run.id);
          assert(record.embeddingRequests === 25 && record.indexedVideoVectors === 18 && record.indexedTextVectors === 5 && record.vectorDimension === 2048 && record.savedVectorsMatchResponses && record.embeddingVectorsFiniteUnitNorm, 'Invalid VideoAgent index: ' + run.id);
          assert(record.llmReplies.length === 2 && record.llmReplies.every(r => r.postExecutions > 0 && r.postExecutions < r.maxTokens && nonempty(r.rawText)), 'Incomplete VideoAgent answer: ' + run.id);
          assert(record.llmReplies.at(-1).rawText.includes(record.answer.trim()) && variant.textSamples.length === 1 && variant.textSamples[0].input === record.question && variant.textSamples[0].output === record.answer, 'VideoAgent displayed answer differs: ' + run.id);
          assert(record.browserPlayback.ended && record.browserPlayback.currentTime === 10 && record.browserPlayback.duration === 10 && record.browserPlayback.error === null, 'VideoAgent clip was not played: ' + run.id);
          assert(record.clip.duration === 10 && record.clip.decodedFrames === 50 && record.qualityAccepted === false && nonempty(variant.textSamples[0].observation), 'Missing VideoAgent effect scope: ' + run.id);
          for (const media of record.mediaFiles) {
            assert(run.evidence.some(e => e.path === media.path), 'Missing VideoAgent media: ' + run.id);
            assert.equal(createHash('sha256').update(fs.readFileSync(path.join(root, 'static', media.path))).digest('hex'), media.sha256, 'VideoAgent media bytes differ: ' + run.id);
          }
          const packageFile = path.join(root, 'static/examples/videoagent-axcl-20261004.zip');
          assert.equal(createHash('sha256').update(fs.readFileSync(packageFile)).digest('hex'), record.packageSha256, 'VideoAgent customer package differs: ' + run.id);
          assert(record.packageSha256 === manifest.runnerSha256 && /^[a-f0-9]{64}$/.test(record.packageSha256), 'VideoAgent package provenance missing: ' + run.id);
        }
        if (nativeVoice) {
          const record = variant.record;
          assert(run.modelId === 'Voice_Assistant.AXERA' && record.customerEntryPassed && record.freshPythonEnvironment && record.cleanShutdown, `Incomplete voice application check: ${run.id}`);
          assert(record.rawIntermediateTensorsCaptured === false && record.physicalMicrophoneSpeakerTested === false, `Voice test scope missing: ${run.id}`);
          assert(record.pipelineSessions.length === 28 && record.loads === 29 && record.unloads === 29, `Incomplete voice weight lifecycle: ${run.id}`);
          const manifestItem = run.evidence.find(e => e.path.endsWith('/download-manifest.json'));
          const manifest = read('static' + manifestItem.path);
          for (const session of record.pipelineSessions) {
            const file = manifest.files.find(f => f.path === session.model);
            assert(file && file.verifiedHashes.sha256 === session.sha256 && session.calls > 0 && session.released && session.allReturnCodesZero, `Unverified voice model: ${run.id}`);
            assert(session.runMilliseconds.length === session.calls && session.runMilliseconds.every(t => Number.isFinite(t) && t >= 0), `Invalid voice execution timing: ${run.id}`);
          }
          assert(record.totalCalls === record.pipelineSessions.reduce((sum, s) => sum + s.calls, 0), `Voice execution total differs: ${run.id}`);
          assert(record.filesBefore.length === 117 && record.filesBefore.length === record.filesAfter.length, `Missing voice file checks: ${run.id}`);
          assert.deepEqual(record.filesBefore, record.filesAfter, `Voice files changed: ${run.id}`);
          for (const file of record.filesBefore) assert(/^[a-f0-9]{64}$/.test(file.sha256), `Invalid voice file hash: ${run.id}`);
          assert(variant.textSamples.length === 1 && variant.textSamples[0].input === record.asrText && variant.textSamples[0].output === record.answer, `Voice display differs from actual output: ${run.id}`);
          for (const audio of record.audioFiles) {
            assert(variant.audio.some(x => x.path === audio.path), `Missing voice audio attachment: ${run.id}`);
            assert.equal(createHash('sha256').update(fs.readFileSync(path.join(root, 'static', audio.path))).digest('hex'), audio.sha256, `Voice audio hash differs: ${run.id}`);
          }
          assert(record.audioFiles.length === 2 && record.outputSeconds > 0 && /^[a-f0-9]{64}$/.test(record.packageSha256), `Missing voice result: ${run.id}`);
        }
        if (nativeReconstruction) {
          const record = variant.record;
          const frames = record.frames;
          assert(record.provider === 'AXCL C API' && record.rawOutputChecks?.allFinite === true, `Missing reconstruction checks: ${run.id}`);
          assert(Array.isArray(frames) && frames.length > 1 && frames.length === record.rawOutputChecks.frames && frames.length === record.video.expectedSampledFrames, `Invalid reconstructed frame count: ${run.id}`);
          assert(record.rawOutputChecks.confidenceMin >= 0 && record.rawOutputChecks.confidenceMax <= 1 && record.rawOutputChecks.confidenceMin <= record.rawOutputChecks.confidenceMax, `Invalid reconstruction confidence: ${run.id}`);
          assert(Number.isFinite(record.rawOutputChecks.orthogonalityMaxError) && record.rawOutputChecks.orthogonalityMaxError < 1e-3, `Invalid reconstructed rotations: ${run.id}`);
          assert(record.sessions.length === 3 && record.nativeCalls?.length === 3 * frames.length && record.totalCalls === record.nativeCalls.length, `Missing reconstruction model calls: ${run.id}`);
          for (const [index, call] of record.nativeCalls.entries()) {
            assert(call.index === index && call.status === 0 && run.testedWeightFiles.includes(call.model), `Invalid reconstruction call: ${run.id}`);
            assert(Number.isFinite(call.milliseconds) && call.milliseconds >= 0, `Invalid reconstruction timing: ${run.id}`);
          }
          for (const session of record.sessions) {
            const calls = record.nativeCalls.filter(c => c.model === session.model);
            assert(session.allReturnCodesZero === true && session.rawOutputTensorsCaptured === false && session.calls === frames.length && calls.length === frames.length, `Incomplete reconstruction calls: ${run.id}`);
            assert.deepEqual(session.runMilliseconds, calls.map(c => c.milliseconds), `Reconstruction call timings differ: ${run.id}`);
          }
          for (const [index, frame] of frames.entries()) {
            assert(frame.index === index && frame.presentValid > 0 && frame.presentValid <= 11, `Invalid reconstruction cache progression: ${run.id}`);
            assert.deepEqual(Object.keys(frame.headsOutputs).sort(), ['camera_features', 'confidence', 'local_points'], `Missing reconstruction head outputs: ${run.id}`);
            for (const tensor of Object.values(frame.headsOutputs)) {
              assert(tensor.allFinite === true && tensor.dtype === 'float32' && /^[a-f0-9]{64}$/.test(tensor.sha256), `Unchecked reconstruction output: ${run.id}`);
              assert(Array.isArray(tensor.shape) && tensor.shape.length && tensor.shape.every(n => Number.isInteger(n) && n > 0), `Invalid reconstruction output shape: ${run.id}`);
            }
          }
          assert(record.pipelineMeta.frames === frames.length && record.pipelineMeta.cloud_points > 0 && record.pipelineMeta.splats > 0, `Missing reconstruction products: ${run.id}`);
        }
        if (nativeApplication || nativeSpeech || nativeEmbeddings || nativeChat || nativeCliVision || nativeQwen25 || nativeQwen3Fixed || nativeMimo) {
          const record = variant.record;
          assert(record.provider === 'AXCL C API' && ((nativeEmbeddings || nativeChat || nativeCliVision || nativeQwen25 || nativeQwen3Fixed || nativeMimo) ? record.serviceExitCode : record.cliExitCode) === 0 && record.rawOutputTensorsCaptured === false, `Invalid native application result: ${run.id}`);
          assert(Array.isArray(record.nativeEvents) && record.nativeEvents.length, `Missing native execution events: ${run.id}`);
          const active = new Map();
          const calls = new Map();
          for (const [eventIndex, event] of record.nativeEvents.entries()) {
            const mappedNativeWeight = run.testedWeightFiles?.includes(event.model) || (nativeVoiceDesign && run.testedCompanionWeights?.some(w => w.repo === event.sourceRepo && w.revision === event.sourceRevision && w.file === event.model));
            assert(event.status === 0 && mappedNativeWeight, `Invalid native event: ${run.id}`);
            if (event.event === 'load') {
              if (active.has(event.modelId)) {
                const previous = record.nativeEvents[eventIndex - 1];
                assert((nativeQwen3Fixed || nativeVoiceDesign) && !event.method && previous?.event === 'load' && previous.method === 'memory' && previous.modelId === event.modelId && previous.model === event.model && active.get(event.modelId) === event.model, `Duplicate live native model: ${run.id}`);
              }
              active.set(event.modelId, event.model);
            } else {
              assert.equal(active.get(event.modelId), event.model, `Unknown native model: ${run.id}`);
              if (event.event === 'unload') active.delete(event.modelId);
              else {
                assert.equal(event.event, 'execute', `Unknown native event: ${run.id}`);
                assert(Number.isFinite(event.milliseconds) && event.milliseconds >= 0, `Invalid native execution timing: ${run.id}`);
                if (!calls.has(event.model)) calls.set(event.model, []);
                calls.get(event.model).push(event.milliseconds);
              }
            }
          }
          assert.equal(active.size, 0, `Native models not unloaded: ${run.id}`);
          assert.deepEqual([...calls.keys()].sort(), record.sessions.map(s => s.model).sort(), `Native execution mapping differs: ${run.id}`);
          for (const session of record.sessions) {
            assert(session.allReturnCodesZero === true && session.rawOutputTensorsCaptured === false && session.calls > 0, `Missing native call checks: ${run.id}`);
            assert.equal(session.calls, calls.get(session.model).length, `Native call count differs: ${run.id}`);
            assert.deepEqual(session.runMilliseconds, calls.get(session.model), `Native call timings differ: ${run.id}`);
          }
          if (nativeMimo) {
            assert(record.modelId === 'Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4' && record.revision === '839273460d343a02f2e88a0cfe059f8ec78a50ea', `Unknown MiMo revision: ${run.id}`);
            assert.deepEqual(result.variants.map(v => v.record.sampleId).sort(), ['count', 'description', 'video'], `Missing MiMo cases: ${run.id}`);
            const video = record.sampleId === 'video';
            assert(record.mode === (video ? 'video' : 'image') && record.sessions.length === 38, `Invalid MiMo mode/weights: ${run.id}`);
            const manifest = read('static' + run.evidence.find(e => e.path.endsWith('/download-manifest.json')).path);
            assert(manifest.files.length === 75 && manifest.runnerSha256 === record.customerPackageSha256, `MiMo package or files differ: ${run.id}`);
            assert(record.customerPackageSha256 === '38990441ac608c2c32dcd6eb5f26315f17c9b22f166f3b0c81d4a31489ee9197' && record.customerPreparationVerified && record.customerCommandEquivalentToActualRun, `Missing MiMo preparation: ${run.id}`);
            assert(record.originalBinarySha256 === '14a18915cc18ed06c58265a3ca78a04430ae5538bced459531cd58866eb1cfa3' && record.postConfigSha256 === '7cd05fda186c94658893a58b9cb4f18f4747e932ecd52f8f449ae862265078e0', `MiMo executable/config differs: ${run.id}`);
            assert.deepEqual(record.postConfig, {enable_temperature: false, temperature: 1, enable_repetition_penalty: false, repetition_penalty: 1, penalty_window: 20, enable_top_p_sampling: false, top_p: 1, enable_top_k_sampling: false, top_k: 1}, `MiMo sampling differs: ${run.id}`);
            assert(record.filesBefore.length === 75 && record.filesBefore.every(f => f.matched), `Missing MiMo file checks: ${run.id}`);
            assert.deepEqual(record.filesBefore, record.filesAfter, `MiMo files changed: ${run.id}`);
            for (const f of record.filesBefore) {
              const original = manifest.files.find(m => m.path === f.path);
              assert(original && original.size === f.size && original.verifiedHashes.sha256 === f.sha256, `MiMo source hash differs: ${run.id}`);
            }
            const tokenizer = manifest.files.find(f => f.path === `tokenizer_${record.mode}.py`);
            assert(record.tokenizerSource.path === tokenizer.path && record.tokenizerSource.sha256 === tokenizer.verifiedHashes.sha256, `MiMo tokenizer differs: ${run.id}`);
            const prefix = 'Xiaomi-MiMo-VL-Miloco-7B-AX650-c128-p1280-ctx2047-Int4/';
            const models = [...Array.from({length: 36}, (_, i) => `${prefix}qwen2_5_vl_text_p128_l${i}_together.axmodel`), `${prefix}qwen2_5_vl_text_post.axmodel`, `${prefix}Xiaomi-MiMo-VL-Miloco-7B_vision.axmodel`];
            assert.deepEqual(record.sessions.map(s => s.model).sort(), models.sort(), `MiMo model mapping differs: ${run.id}`);
            for (const e of record.nativeEvents.filter(e => e.event === 'load')) {
              const original = manifest.files.find(f => f.path === e.model);
              assert(e.method === 'memory' && e.size === original.size && e.hostTransferSha256 === original.verifiedHashes.sha256, `MiMo transferred weights differ: ${run.id}`);
            }
            assert(record.visualFields.img_prompt && record.visualFields.num_img === (video ? 4 : 1) && record.visualFields.img_token_num === 196 && record.visualFields.text === record.input, `MiMo visual request differs: ${run.id}`);
            assert(record.inputTokenIds.filter(x => x === (video ? 151656 : 151655)).length === (video ? 784 : 196), `MiMo visual tokens differ: ${run.id}`);
            assert(record.inputTokenIds.filter(x => x === 151652).length === 1 && record.inputTokenIds.filter(x => x === 151653).length === 1, `MiMo visual boundaries differ: ${run.id}`);
            assert.deepEqual(record.streamedTokenIds, record.finalTokenIds, `MiMo stream/final output differs: ${run.id}`);
            assert(record.outputTokens === record.finalTokenIds.length && record.outputTokens > 0 && record.inputTokenIds.length <= 1280 && record.contextCapacity === 2047 && record.outputTokens + record.inputTokenIds.length < record.contextCapacity, `MiMo incomplete/limit output: ${run.id}`);
            assert(record.originalProgramReportsEos && record.cleanExit && record.allNativeReleased && nonempty(record.stopConditionLimitation), `MiMo termination evidence missing: ${run.id}`);
            const executions = record.nativeEvents.filter(e => e.event === 'execute');
            assert(executions.length === record.totalCalls && record.totalCalls === record.sessions.reduce((sum, s) => sum + s.calls, 0), `MiMo native call count differs: ${run.id}`);
            assert(executions.filter(e => e.model.endsWith('/Xiaomi-MiMo-VL-Miloco-7B_vision.axmodel')).length === (video ? 4 : 1), `MiMo vision calls differ: ${run.id}`);
            assert.deepEqual(executions.filter(e => e.model.endsWith('/qwen2_5_vl_text_post.axmodel')).map(e => e.group), Array(record.outputTokens + 1).fill(0), `MiMo output call count differs: ${run.id}`);
            const expectedGroups = [...Array.from({length: Math.ceil(record.inputTokenIds.length / 128)}, (_, i) => i + 1), ...Array(record.outputTokens).fill(0)];
            for (let i = 0; i < 36; i++) assert.deepEqual(executions.filter(e => e.model === `${prefix}qwen2_5_vl_text_p128_l${i}_together.axmodel`).map(e => e.group), expectedGroups, `MiMo layer calls differ: ${run.id}`);
            assert(record.fullText.startsWith('<think>') && record.fullText.includes('</think>') && record.fullText.split('</think>').length === 2, `MiMo incomplete text sections: ${run.id}`);
            assert.equal(record.finalAnswer, record.fullText.slice(record.fullText.indexOf('</think>') + 8).trim(), `MiMo final answer altered: ${run.id}`);
            const fullText = fs.readFileSync(path.join(root, 'static', record.fullTextPath), 'utf8');
            assert(fullText === record.fullText && createHash('sha256').update(fullText, 'utf8').digest('hex') === record.fullTextSha256 && run.evidence.some(e => e.path === record.fullTextPath), `MiMo complete reply file differs: ${run.id}`);
            assert(variant.textSamples.length === 1 && variant.textSamples[0].input === record.input && variant.textSamples[0].output === record.finalAnswer && variant.textSamples[0].outputSource === 'response-after-thinking' && nonempty(variant.textSamples[0].observation), `MiMo displayed answer differs: ${run.id}`);
            assert(record.inputFiles.length === (video ? 8 : 1) && variant.previews.length === record.inputFiles.length, `Missing MiMo input media: ${run.id}`);
            for (const [i, f] of record.inputFiles.entries()) {
              assert(f.sourcePath === (video ? `video/frame_${String(i * 8).padStart(4, '0')}.jpg` : 'image/ssd_car.jpg'), `MiMo frame order differs: ${run.id}`);
              assert(manifest.files.some(m => m.path === f.sourcePath && m.verifiedHashes.sha256 === f.sha256) && variant.previews[i].path === f.path, `MiMo input provenance differs: ${run.id}`);
              assert.equal(createHash('sha256').update(fs.readFileSync(path.join(root, 'static', f.path))).digest('hex'), f.sha256, `MiMo image changed: ${run.id}`);
            }
            assert(record.qualityAccepted === false && record.freshInstallationAccepted === false && record.processSeconds > 0 && record.logTtftMilliseconds > 0 && record.logTokensPerSecond > 0, `MiMo scope or metrics invalid: ${run.id}`);
          } else if (nativeQwen25) {
            const profiles = {
              'Qwen2.5-VL-3B-Instruct-GPTQ-Int4': {revision: '3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e', binary: '255430072183943d0356a3979bd968527bc257d5807ec2ac21838a99a06fa9e8', files: 56, imageSamples: 2, videoSamples: 1, imageVision: 'Qwen2.5-VL-3B-Instruct_vision_image_392.axmodel', videoVision: 'Qwen2.5-VL-3B-Instruct_vision_image_392.axmodel'},
              'Qwen2.5-VL-3B-Instruct': {revision: 'd967363ac68ee8c46a46110b8ee92f0f0cb332cb', binary: 'b6d3cdbe0b4d9d47cb8f901a8f576cd82e7c0723fc9500cb12fae1b34f91a235', files: 80, imageSamples: 3, videoSamples: 2, imageVision: 'Qwen2.5-VL-3B-Instruct_vision_nchw448.axmodel', videoVision: 'Qwen2.5-VL-3B-Instruct_vision_nhwc.axmodel'},
              'Qwen2.5-VL-7B-Instruct': {revision: 'd6ded77c295c220efe50d4894ff0d5820f01b3b1', binary: '27ada2f4e0351b37336308054fd2741a296406dac4690d5a8ffa0f1450a36b70', files: 67, layers: 28, mmap: true, imageSamples: 2, videoSamples: 2, imageVision: 'Qwen2.5-VL-7B-Instruct_vision.axmodel', videoVision: 'Qwen2.5-VL-7B-Instruct_vision_video.axmodel'},
            };
            const profile = profiles[record.modelId];
            assert(profile && record.runtimeSourceCommit === '9c2921cca383b38d4c00c51fd19eb6459a9be925', `Unknown Qwen2.5 companion: ${run.id}`);
            assert(record.revision === profile.revision && record.binarySha256 === profile.binary, `Qwen2.5 runtime differs: ${run.id}`);
            const visionFile = record.mode === 'image' ? profile.imageVision : profile.videoVision;
            const expected = [...Array.from({length: profile.layers ?? 36}, (_, i) => `qwen2_5_vl_p128_l${i}_together.axmodel`), 'qwen2_5_vl_post.axmodel', visionFile];
            assert.deepEqual(record.sessions.map(s => s.model.split('/').at(-1)).sort(), expected.sort(), `Qwen2.5 weight coverage differs: ${run.id}`);
            assert(['image', 'video'].includes(record.mode) && record.samples.length === (record.mode === 'image' ? profile.imageSamples : profile.videoSamples) && record.samples.length === variant.textSamples.length, `Qwen2.5 sample coverage differs: ${run.id}`);
            assert(record.filesBefore.length === profile.files && record.filesBefore.every(f => f.matched), `Missing Qwen2.5 file checks: ${run.id}`);
            assert.deepEqual(record.filesBefore, record.filesAfter, `Qwen2.5 files changed: ${run.id}`);
            assert.deepEqual(record.runtimeBefore, record.runtimeAfter, `Qwen2.5 companion changed: ${run.id}`);
            const is7B = record.modelId === 'Qwen2.5-VL-7B-Instruct';
            assert(record.mmapEmbedding === (profile.mmap ?? false) && nonempty(record.stopConditionLimitation), `Missing Qwen2.5 execution scope: ${run.id}`);
            if (is7B) {
              assert(record.customerPackageChecked && record.embeddingMmapCheck?.allTokenRowsCompared === 152064 && record.embeddingMmapCheck.elementsPerRow === 3584 && record.embeddingMmapCheck.cpuChecksPassed, `Missing 7B package or ARM64 mmap checks: ${run.id}`);
              assert(record.threadEnvironment?.OMP_NUM_THREADS === '1' && record.threadEnvironment.OMP_THREAD_LIMIT === '1', `Unexpected 7B loading configuration: ${run.id}`);
            }
            let total = 0;
            for (const [i, sample] of record.samples.entries()) {
              assert(sample.exitCode === 0 && sample.nativeReleased && sample.hitEos && sample.processSeconds > 0, `Incomplete Qwen2.5 request: ${run.id}`);
              if (record.modelId === 'Qwen2.5-VL-3B-Instruct' || is7B) {
                assert(sample.terminationReason === 'eos' && sample.lastToken === 151645 && sample.emittedTokens > 0, `Qwen2.5 stop reason not verified: ${run.id}`);
                assert(record.rawRequestLogs[i].includes(`termination_reason=eos last_token=151645 emitted_tokens=${sample.emittedTokens}`), `Missing Qwen2.5 termination log: ${run.id}`);
                const cache = sample.decodeCacheCheck;
                assert((is7B ? record.customerPackageChecked : record.customerEntry) && cache.matchedInputLength && cache.steps === sample.emittedTokens && cache.firstCacheIndex > cache.firstRotaryIndex && cache.lastCacheIndex < cache.capacity, `Invalid Qwen2.5 cache progression: ${run.id}`);
                assert.equal(cache.lastCacheIndex, cache.firstCacheIndex + cache.steps - 1, `Qwen2.5 cache offset differs: ${run.id}`);
                const steps = [...record.rawRequestLogs[i].matchAll(/decode_step cache_index=(\d+) rotary_index=(\d+)/g)].map(m => [Number(m[1]), Number(m[2])]);
                assert.deepEqual(steps, Array.from({length: cache.steps}, (_, n) => [cache.firstCacheIndex + n, cache.firstRotaryIndex + n]), `Qwen2.5 raw cache offsets differ: ${run.id}`);

                assert(record.rawRequestLogs[i].includes('load config:') && !record.rawRequestLogs[i].includes('load postprocess config('), `Qwen2.5 configuration not loaded: ${run.id}`);
                if (is7B) {
                  assert(sample.postConfigLoaded.enable_temperature === true && sample.postConfigLoaded.temperature === 0.1 && sample.postConfigLoaded.enable_top_k_sampling === true && sample.postConfigLoaded.top_k === 10 && sample.postConfigLoaded.enable_repetition_penalty === false && sample.postConfigLoaded.enable_top_p_sampling === false, `Qwen2.5 official 7B sampling differs: ${run.id}`);
                  assert(record.rawRequestLogs[i].includes('LLaMaEmbedSelector use mmap'), `Missing 7B mmap execution log: ${run.id}`);
                } else {
                  assert(sample.postConfigLoaded.enable_temperature === false && sample.postConfigLoaded.enable_repetition_penalty === false && sample.postConfigLoaded.enable_top_p_sampling === false && sample.postConfigLoaded.enable_top_k_sampling === false, `Qwen2.5 expected greedy settings differ: ${run.id}`);
                }
              }
              assert.equal(variant.textSamples[i].input, sample.input, `Qwen2.5 question differs: ${run.id}`);
              assert.equal(variant.textSamples[i].output, sample.output, `Qwen2.5 answer differs: ${run.id}`);
              assert(nonempty(variant.textSamples[i].observation) && record.rawRequestLogs[i].includes(sample.output), `Missing Qwen2.5 raw reply: ${run.id}`);
              const events = record.nativeEvents.filter(e => e.requestIndex === i && e.event === 'execute');
              assert.equal(events.length, sample.nativeCalls, `Qwen2.5 request calls differ: ${run.id}`);
              assert.deepEqual([...new Set(events.map(e => e.model))].sort(), record.sessions.map(s => s.model).sort(), `Qwen2.5 request weight mapping differs: ${run.id}`);
              assert.equal(events.filter(e => e.model.endsWith('/' + visionFile)).length, record.mode === 'image' ? (is7B ? [4, 1][i] : 1) : 4, `Qwen2.5 vision groups differ: ${run.id}`);
              total += events.length;
            }
            assert.equal(total, record.totalCalls, `Qwen2.5 total calls differ: ${run.id}`);
          } else if (nativeQwen3Fixed) {
            const profiles = {
              'Qwen3-VL-2B-Instruct': {revision: 'b88b51a9b583a5480717de7955a7b10a28dde9d4', chunk: 128, files: 72, inputLimit: 1152},
              'Qwen3-VL-2B-Instruct-GPTQ-Int4-C512-P3584-CTX4095': {revision: 'ced30de327fcd7580ac26ebd6d18a7fc6a2bb028', chunk: 512, files: 34, inputLimit: 3584},
              'Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047': {revision: 'cf4b904ba59e66fefd17668af196fc9c199ab70f', chunk: 128, files: 75, inputLimit: 1536},
              'Qwen3-VL-4B-Instruct': {revision: '052d3999478f8974b736f8663072e9a72aaabbf5', chunk: 128, files: 48, inputLimit: 1152},
              'Qwen3-VL-8B-Instruct': {revision: 'f3c9f23de6de9aa5c78b5cc9177094e1be7d913f', chunk: 128, files: 83, inputLimit: 1152},
              'Qwen3-VL-8B-Instruct-GPTQ-Int4': {revision: 'e9e73ad656bd299aedd92c9dad85cf0b308c77fd', chunk: 128, files: 76, inputLimit: 1152},
            };
            const profile = profiles[record.modelId];
            assert(profile && record.revision === profile.revision, `Unknown fixed Qwen3 profile: ${run.id}`);
            const isC512 = profile.chunk === 512;
            const isP1536 = profile.files === 75;
            const is4B = record.modelId === 'Qwen3-VL-4B-Instruct';
            const is8BInt4 = record.modelId === 'Qwen3-VL-8B-Instruct-GPTQ-Int4';
            const is8B = record.modelId === 'Qwen3-VL-8B-Instruct' || is8BInt4;
            const resolution = (isC512 || isP1536) ? record.resolution : 384;
            const frameCount = (isP1536 || is4B || is8B) ? record.frameCount : 8;
            assert([384, 640].includes(resolution), `Invalid Qwen3 image size: ${run.id}`);
            if (isC512) {
              assert(record.companionSource?.completed && record.companionSource.companionRepo === 'AXERA-TECH/Qwen3-VL-2B-Instruct' && record.companionSource.companionRevision === 'b88b51a9b583a5480717de7955a7b10a28dde9d4' && record.companionSource.files.length === 23, `Missing Qwen3 companion source: ${run.id}`);
              assert(record.runtimeBefore.length === 31, `Missing Qwen3 companion runtime checks: ${run.id}`);
              for (const file of record.companionSource.files) assert(record.runtimeBefore.some(r => r.path === `companion/${file.path}` && r.sha256 === file.sha256), `Qwen3 companion file differs: ${run.id}`);
              assert(record.shapeReference?.completed && record.shapeReference.modelId === record.modelId && record.shapeReference.revision === record.revision && record.shapeReference.files.some(f => f.resolution === resolution), `Missing Qwen3 visual shape reference: ${run.id}`);
            }
            if (isP1536) {
              assert(['384', '640', 'u8'].includes(record.encoder) && resolution === (record.encoder === '640' ? 640 : 384) && frameCount === (record.encoder === '640' ? 6 : 8), `Invalid P1536 encoder or frame plan: ${run.id}`);
              assert(record.runtimeBefore.length === 13 && record.tokenizerSource?.repo === `AXERA-TECH/${record.modelId}` && record.tokenizerSource.revision === record.revision && record.tokenizerSource.path === 'qwen3_tokenizer.txt' && record.tokenizerSource.sha256 === record.tokenizerSha256, `Missing P1536 own vocabulary: ${run.id}`);
              assert(record.filesBefore.some(f => f.path === 'qwen3_tokenizer.txt' && f.sha256 === record.tokenizerSha256), `P1536 vocabulary differs from model files: ${run.id}`);
              assert(record.shapeReference?.completed && record.shapeReference.modelId === record.modelId && record.shapeReference.revision === record.revision && record.shapeReference.files.some(f => f.variant === record.encoder), `Missing P1536 encoder metadata: ${run.id}`);
              if (record.mode === 'video') {
                assert(record.inputFrames.length === frameCount, `Missing P1536 input frame list: ${run.id}`);
                for (const [index, frame] of record.inputFrames.entries()) assert(frame.path === `video/frame_${String(index * 8).padStart(4, '0')}.jpg` && record.filesBefore.some(f => f.path === frame.path && f.sha256 === frame.sha256), `P1536 selected frame differs: ${run.id}`);
              }
            }
            if (is4B) {
              assert(record.variant === (record.mode === 'image' ? 'image' : `video${frameCount}`) && (record.mode === 'image' ? frameCount === 0 : [3, 8].includes(frameCount)), `Invalid 4B frame plan: ${run.id}`);
              assert(record.runtimeBefore.length === 19 && record.tokenizerSource?.repo === 'AXERA-TECH/Qwen3-VL-4B-Instruct' && record.tokenizerSource.revision === record.revision && record.tokenizerSource.path === 'tokenizer.txt' && record.tokenizerSource.sha256 === record.tokenizerSha256, `Missing 4B own vocabulary: ${run.id}`);
              assert(record.filesBefore.some(f => f.path === 'tokenizer.txt' && f.sha256 === record.tokenizerSha256), `4B vocabulary differs from model files: ${run.id}`);
              assert(record.companionSource?.repo === 'AXERA-TECH/Qwen3-VL-2B-Instruct' && record.companionSource.revision === 'b88b51a9b583a5480717de7955a7b10a28dde9d4' && record.companionSource.files.length === 10, `Missing 4B companion inputs: ${run.id}`);
              for (const f of record.companionSource.files) assert(record.runtimeBefore.some(r => r.path === `companion/${f.path}` && r.sha256 === f.sha256), `4B companion hash differs: ${run.id}`);
              const checkInput = input => {
                const own = input.sourceRepo === 'AXERA-TECH/Qwen3-VL-4B-Instruct';
                const source = own ? record.filesBefore : record.companionSource.files;
                assert(own ? input.sourceRevision === record.revision : input.sourceRepo === record.companionSource.repo && input.sourceRevision === record.companionSource.revision, `4B input source differs: ${run.id}`);
                assert(source.some(f => f.path === input.sourcePath && f.sha256 === input.sha256), `4B input hash differs: ${run.id}`);
              };
              if (record.mode === 'image') {
                assert(record.inputImages.length === 5, `Missing 4B image sources: ${run.id}`);
                assert.deepEqual(record.inputImages.map(f => f.sourcePath), ['images/ssd_horse.jpg', '01.jpg', 'images/ssd_car.jpg', '01.jpg', 'images/ssd_horse.jpg'], `4B image mapping differs: ${run.id}`);
                record.inputImages.forEach(checkInput);
              } else {
                assert(record.inputFrames.length === frameCount, `Missing 4B video frames: ${run.id}`);
                for (const [i, f] of record.inputFrames.entries()) {
                  checkInput(f);
                  assert(f.sourcePath === `video/frame_${String(i * 8).padStart(4, '0')}.jpg` && f.sourceRepo === (frameCount === 3 ? 'AXERA-TECH/Qwen3-VL-4B-Instruct' : record.companionSource.repo), `4B frame order/source differs: ${run.id}`);
                }
              }
              assert(record.shapeReference?.completed && record.shapeReference.modelId === record.modelId && record.shapeReference.revision === record.revision && record.shapeReference.files.length === 2, `Missing 4B shape reference: ${run.id}`);
            }
            if (is8B) {
              assert(record.variant === (record.mode === 'image' ? 'image' : 'video8') && frameCount === (record.mode === 'image' ? 0 : 8), `Invalid 8B frame plan: ${run.id}`);
              assert(record.runtimeBefore.length === 9 && record.tokenizerSource?.repo === `AXERA-TECH/${record.modelId}` && record.tokenizerSource.revision === record.revision && record.tokenizerSource.sourceDirectory === 'qwen3-vl-tokenizer' && record.tokenizerSource.sha256 === record.tokenizerSha256, `Missing 8B own tokenizer source: ${run.id}`);
              assert(record.tokenizerExport?.completed && record.tokenizerExport.modelId === record.modelId && record.tokenizerExport.revision === record.revision && record.tokenizerExport.tokenizerSha256 === record.tokenizerSha256 && record.tokenizerExport.converterCommit === '0eed4120c6e1b5ea1e51b51c576924faddc8b2a1', `Missing 8B tokenizer conversion proof: ${run.id}`);
              assert.deepEqual(record.tokenizerSource.sourceFiles, record.tokenizerExport.inputFiles, `8B tokenizer source mapping differs: ${run.id}`);
              assert(record.tokenizerSource.sourceFiles.length === 12 && record.tokenizerSource.sourceFiles.every(f => record.filesBefore.some(s => s.path === f.path && s.sha256 === f.sha256)), `8B tokenizer source hashes differ: ${run.id}`);
              assert(record.positionReference.referenceRepo === record.tokenizerSource.repo && record.positionReference.referenceRevision === record.revision, `8B CPU reference source differs: ${run.id}`);
              const checkInput = input => assert(input.sourceRepo === `AXERA-TECH/${record.modelId}` && input.sourceRevision === record.revision && input.path === input.sourcePath && record.filesBefore.some(f => f.path === input.path && f.sha256 === input.sha256), `8B input source/hash differs: ${run.id}`);
              if (record.mode === 'image') {
                assert(record.inputImages.length === 5 && record.inputImages.every(f => f.root === 'model'), `Missing 8B image sources: ${run.id}`);
                assert.deepEqual(record.inputImages.map(f => f.path), ['images/ssd_horse.jpg', 'images/ssd_horse.jpg', 'images/ssd_car.jpg', 'images/ssd_horse.jpg', 'images/ssd_horse.jpg'], `8B image mapping differs: ${run.id}`);
                record.inputImages.forEach(checkInput);
              } else {
                assert(record.inputFrames.length === 8, `Missing 8B video frames: ${run.id}`);
                for (const [i, f] of record.inputFrames.entries()) {
                  checkInput(f);
                  assert(f.path === `video/frame_${String(i * 8).padStart(4, '0')}.jpg`, `8B frame order differs: ${run.id}`);
                }
              }
              assert(record.shapeReference?.completed && record.shapeReference.modelId === record.modelId && record.shapeReference.revision === record.revision && record.shapeReference.files.length === 2, `Missing 8B shape reference: ${run.id}`);
              assert(record.sessions.every(s => s.model.startsWith(`Qwen3-VL-8B-Instruct-AX650-c128_p1152${is8BInt4 ? '-int4' : ''}/`)), `8B weight directory differs: ${run.id}`);
            }
            assert(record.binarySha256 === ((is4B || is8B) ? '5fe013816dace0fa1f9a2433cb809d6112c152b0b5a7ecfa424615707000cab6' : 'edce8d010fee8050cef9e8f494696346055d692e55feb619573b2bc75cd7db93') && record.runtimeSourceCommit === '3be4cc3fee4a4c730ec7c9b8982ff4b398eefac7', `Qwen3 runtime differs: ${run.id}`);
            assert(record.tokenizerSha256 === (is4B ? 'ee94c32896590639b7fdcfcdeed48e2556ce0115148dddb1da838fa0349a4b6c' : isP1536 ? '46fafa42f69d10f67677adffd3ca6285e0c97b7deddfebaa98ceeac3557f04a3' : '7119de4966cc6a8ae87d7f083e65b315282d06c3122fdd41ce783fdd2d3c1ca2'), `Qwen3 native vocabulary differs: ${run.id}`);
            assert(record.customerEntry && record.mmapEmbedding === false && record.rawIntermediateTensorsCaptured === false && nonempty(record.stopConditionLimitation), `Missing Qwen3 execution scope: ${run.id}`);
            const expectedFiles = [...Array.from({length: (is4B || is8B) ? 36 : 28}, (_, i) => `qwen3_vl_text_p${profile.chunk}_l${i}_together.axmodel`), 'qwen3_vl_text_post.axmodel', (is8B ? 'Qwen3-VL-8B-Instruct_vision.axmodel' : is4B ? 'Qwen3-VL-4B-Instruct_vision.axmodel' : isP1536 && record.encoder === 'u8' ? 'Qwen3-VL-2B-Instruct_vision_u8.axmodel' : resolution === 640 ? 'Qwen3-VL-2B-Instruct_vision_640x640.axmodel' : 'Qwen3-VL-2B-Instruct_vision.axmodel')];
            assert.deepEqual(record.sessions.map(s => s.model.split('/').at(-1)).sort(), expectedFiles.sort(), `Qwen3 weight mapping differs: ${run.id}`);
            assert(['image', 'video'].includes(record.mode) && record.samples.length === (record.mode === 'image' ? 5 : 2) && variant.textSamples.length === record.samples.length, `Qwen3 sample coverage differs: ${run.id}`);
            assert(record.filesBefore.length === profile.files && record.filesBefore.every(f => f.matched), `Missing Qwen3 file checks: ${run.id}`);
            assert.deepEqual(record.filesBefore, record.filesAfter, `Qwen3 files changed: ${run.id}`);
            assert.deepEqual(record.runtimeBefore, record.runtimeAfter, `Qwen3 runtime changed: ${run.id}`);
            assert(record.positionReference.passed && record.positionReference.revision === record.revision, `Missing native Qwen3 position reference: ${run.id}`);
            let total = 0;
            for (const [i, sample] of record.samples.entries()) {
              assert(sample.exitCode === 0 && sample.nativeReleased && sample.processSeconds > 0 && sample.terminationReason === 'eos' && sample.lastToken === 151645 && sample.emittedTokens > 0, `Qwen3 response did not end naturally: ${run.id}`);
              const log = record.rawRequestLogs[i].replace(/\x1b\[[0-9;]*[A-Za-z]/g, '');
              const end = /termination_reason=eos last_token=151645 emitted_tokens=(\d+)[^\n]*\n/.exec(log);
              assert(end && Number(end[1]) === sample.emittedTokens, `Missing Qwen3 termination log: ${run.id}`);
              assert.equal(log.slice(end.index + end[0].length).split('prompt >> ')[0].trim(), sample.output, `Qwen3 native reply differs: ${run.id}`);
              assert.equal(variant.textSamples[i].input, sample.input, `Qwen3 displayed question differs: ${run.id}`);
              assert.equal(variant.textSamples[i].output, sample.output, `Qwen3 displayed answer differs: ${run.id}`);
              assert(nonempty(variant.textSamples[i].observation), `Missing Qwen3 visual review: ${run.id}`);
              const cache = sample.decodeCacheCheck;
              const referenceName = is4B ? (sample.label === 'room-zh' ? 'bus-zh' : record.variant === 'video3' ? `odd-three-${sample.label}` : sample.label) : ((isP1536 && record.encoder === '640' && record.mode === 'video') ? `640-video6-${sample.label.split('-').at(-1)}` : (isC512 || isP1536) ? `${resolution}-${sample.label}` : sample.label);
              const reference = record.positionReference.rows.find(r => r.name === referenceName);
              assert(reference?.chatExact && reference.tokenIdsExact && reference.positionsExact && reference.roundTripExact && reference.cacheIndex === cache.firstCacheIndex && reference.rotaryIndex === cache.firstRotaryIndex, `Qwen3 reference positions differ: ${run.id}`);
              assert(cache.matchedInputLength && cache.steps === sample.emittedTokens && cache.firstCacheIndex > cache.firstRotaryIndex && cache.firstCacheIndex <= profile.inputLimit && (!isC512 || cache.capacity === 4095) && (!(isP1536 || is4B || is8B) || cache.capacity === 2047) && cache.lastCacheIndex < cache.capacity, `Invalid Qwen3 cache range: ${run.id}`);
              if (is4B && record.mode === 'video') assert.deepEqual(reference.timestamps, frameCount === 3 ? [0.5, 2.0] : [0.5, 2.5, 4.5, 6.5], `4B original frame timestamps differ: ${run.id}`);
              if (is8B && record.mode === 'video') assert.deepEqual(reference.timestamps, [0.5, 2.5, 4.5, 6.5], `8B frame timestamps differ: ${run.id}`);
              assert.equal(cache.lastCacheIndex, cache.firstCacheIndex + cache.steps - 1, `Qwen3 cache progression differs: ${run.id}`);
              const steps = [...log.matchAll(/decode_step cache_index=(\d+) rotary_index=(\d+)/g)].map(m => [Number(m[1]), Number(m[2])]);
              assert.deepEqual(steps, Array.from({length: cache.steps}, (_, n) => [cache.firstCacheIndex + n, cache.firstRotaryIndex + n]), `Qwen3 raw cache offsets differ: ${run.id}`);
              const config = /load config:\s*(\{.*?\})/s.exec(log);
              assert(config && JSON.stringify(JSON.parse(config[1])) === JSON.stringify(sample.postConfigLoaded), `Qwen3 actual post configuration differs: ${run.id}`);
              assert(sample.postConfigLoaded.enable_temperature === false && sample.postConfigLoaded.enable_repetition_penalty === false && sample.postConfigLoaded.enable_top_p_sampling === false && sample.postConfigLoaded.enable_top_k_sampling === true && sample.postConfigLoaded.top_k === 1, `Qwen3 greedy settings differ: ${run.id}`);
              const events = record.nativeEvents.filter(e => e.requestIndex === i && e.event === 'execute');
              assert.equal(events.length, sample.nativeCalls, `Qwen3 request calls differ: ${run.id}`);
              for (const session of record.sessions) {
                const calls = events.filter(e => e.model === session.model).length;
                const expected = session.model.split('/').at(-1).includes('_vision') ? (record.mode === 'image' ? 1 : Math.ceil(frameCount / 2)) : session.model.endsWith('_post.axmodel') ? sample.emittedTokens + 1 : Math.ceil(cache.firstCacheIndex / profile.chunk) + sample.emittedTokens;
                assert.equal(calls, expected, `Qwen3 request layer coverage differs: ${run.id}`);
              }
              total += events.length;
            }
            assert.equal(total, record.totalCalls, `Qwen3 total calls differ: ${run.id}`);
          } else if (nativeCliVision) {
            const isVideo = record.mode === 'video';
            const profiles = {
              'Qwen3-VL-2B-Instruct': {layers: 28, chunk: 128, images: 2, size: '2B'},
              'Qwen3-VL-2B-Instruct-GPTQ-Int4-C512-P3584-CTX4095': {layers: 28, chunk: 512, images: 2, size: '2B'},
              'Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047': {layers: 28, chunk: 128, images: 2, size: '2B'},
              'Qwen3-VL-4B-Instruct': {layers: 36, chunk: 128, images: 3, size: '4B'},
              'Qwen3-VL-8B-Instruct': {layers: 36, chunk: 128, images: 2, size: '8B'},
            };
            const profile = profiles[record.modelId];
            assert(profile, `Unknown native vision profile: ${run.id}`);
            const filename = model => model.split('/').at(-1);
            const visionFile = `Qwen3-VL-${profile.size}-Instruct_vision.axmodel`;
            const expectedFiles = [...Array.from({length: profile.layers}, (_, i) => `qwen3_vl_text_p${profile.chunk}_l${i}_together.axmodel`), 'qwen3_vl_text_post.axmodel', visionFile];
            assert.deepEqual(record.sessions.map(s => filename(s.model)).sort(), expectedFiles.sort(), `Native vision layer mapping differs: ${run.id}`);
            assert(['images', 'video'].includes(record.mode) && record.requests?.length === (isVideo ? 2 : 5) && record.sessions.length === profile.layers + 2, `Incomplete native vision: ${run.id}`);
            assert(record.rawIntermediateTensorsCaptured === false && record.mmapEmbedding === false && nonempty(record.stopConditionLimitation), `Missing native vision scope: ${run.id}`);
            assert.equal(record.runtimeSourceCommit, '3be4cc3fee4a4c730ec7c9b8982ff4b398eefac7', `Unexpected CLI source: ${run.id}`);
            assert(record.inputFiles.length === (isVideo ? 8 : profile.images) && variant.textSamples?.length === record.requests.length, `Missing vision inputs or replies: ${run.id}`);
            assert.equal(record.postConfigUsed.top_k, 1, `Non-greedy CLI configuration: ${run.id}`);
            for (const [index, request] of record.requests.entries()) {
              const sample = variant.textSamples[index];
              assert(nonempty(request.prompt) && nonempty(request.reply) && request.seconds > 0 && request.nativeSummaryPresent, `Invalid native vision reply: ${run.id}`);
              assert.equal(sample.input, request.prompt + `（输入：${request.media}）`, `Vision question differs: ${run.id}`);
              assert.equal(sample.output, request.reply, `Vision answer differs: ${run.id}`);
              assert(nonempty(sample.observation), `Missing visual review: ${run.id}`);
              assert.equal(createHash('sha256').update(request.reply, 'utf8').digest('hex'), request.replySha256, `Vision reply hash differs: ${run.id}`);
              const log = record.rawRequestLogs[request.label].replace(/\x1b\[[0-9;]*[A-Za-z]/g, '');
              const match = /^.*hit eos,avg[^\n]*\n/m.exec(log);
              assert(match && log.slice(match.index + match[0].length).trim() === request.reply, `CLI log answer differs: ${run.id}`);
              const events = record.nativeEvents.slice(request.nativeEventStart, request.nativeEventEnd).filter(e => e.event === 'execute');
              assert.equal(events.length, request.axclCalls, `CLI request calls differ: ${run.id}`);
              assert.deepEqual([...new Set(events.map(e => e.model))].sort(), record.sessions.map(s => s.model).sort(), `CLI per-request weights differ: ${run.id}`);
              assert.equal(events.filter(e => filename(e.model) === 'qwen3_vl_text_post.axmodel').length, request.postCalls, `CLI output calls differ: ${run.id}`);
              assert.equal(events.filter(e => filename(e.model) === visionFile).length, isVideo ? 4 : 1, `CLI vision groups differ: ${run.id}`);
              assert.deepEqual([...log.matchAll(/pixel_values size\s+(\d+)/g)].map(m => Number(m[1])), [isVideo ? 4 : 1], `Vision preprocessing count differs: ${run.id}`);
              assert.deepEqual([...log.matchAll(/ttft:\s*([0-9.]+)\s*ms/g)].map(m => Number(m[1])), request.logTtftMilliseconds, `CLI TTFT differs: ${run.id}`);
              if (isVideo) assert.deepEqual(log.split('\n').map(s => s.trim()).filter(s => /^video\/frame_\d+\.jpg$/.test(s)), record.inputFiles.map(f => f.path), `Frame sequence differs: ${run.id}`);
            }
            assert.equal(record.totalCalls, record.sessions.reduce((n, s) => n + s.calls, 0), `Wrong native vision call count: ${run.id}`);
          } else if (nativeChat) {
            assert(record.rawIntermediateTensorsCaptured === false && record.requests?.length === 9 && record.sessions.length === 26 && record.batch === 1, `Incomplete native chat: ${run.id}`);
            assert(nonempty(record.stopConditionLimitation), `Missing chat termination limitation: ${run.id}`);
            assert(variant.textSamples?.length === record.requests.length, `Missing raw chat examples: ${run.id}`);
            for (const [index, request] of record.requests.entries()) {
              assert(request.status === 200 && request.seconds > 0 && request.request.max_tokens === 512 && request.request.temperature === 0 && request.request.stream === false, `Invalid native chat request: ${run.id}`);
              assert(nonempty(request.reply) && request.reply === request.response?.choices?.[0]?.message?.content, `Native reply differs: ${run.id}`);
              const sample = variant.textSamples[index];
              assert(nonempty(sample.input) && nonempty(sample.output) && nonempty(sample.observation), `Missing native chat example: ${run.id}`);
              assert.equal(sample.input, request.prompt + (request.image ? `（图片：${request.image}）` : ''), `Native chat input differs: ${run.id}`);
              assert(request.postCalls < request.request.max_tokens, `Native chat reached generation limit: ${run.id}`);
              if (sample.outputSource === 'response-after-thinking') {
                assert(request.reply.trimStart().startsWith('<think>') && request.reply.includes('</think>'), `Unfinished native answer: ${run.id}`);
                assert.equal(sample.output, request.reply.slice(request.reply.indexOf('</think>') + 8).trim(), `Final answer differs: ${run.id}`);
              } else {
                assert.equal(sample.outputSource, 'raw-response', `Unknown native reply representation: ${run.id}`);
                assert.equal(sample.output, request.reply, `Raw native answer differs: ${run.id}`);
              }
              assert.equal(createHash('sha256').update(request.reply, 'utf8').digest('hex'), request.replySha256, `Native reply hash differs: ${run.id}`);
              const events = record.nativeEvents.slice(request.nativeEventStart, request.nativeEventEnd).filter(e => e.event === 'execute');
              assert(events.length > 0 && events.length === request.axclCalls, `Missing chat request execution: ${run.id}`);
              assert.deepEqual([...new Set(events.map(e => e.model))].sort(), request.executedModels, `Chat request models differ: ${run.id}`);
              assert.equal(events.filter(e => e.model === 'qwen3_5_text_post.axmodel').length, request.postCalls, `Chat output calls differ: ${run.id}`);
            }
            const followup = record.requests.find(r => r.label === 'memory-followup');
            const first = record.requests.find(r => r.label === 'memory-first');
            assert(first && followup?.request.messages.length === 4 && followup.request.messages[2].content === first.reply, `Missing real conversation history: ${run.id}`);
            assert.equal(record.repeatTextIdentical, record.requests[0].reply === record.requests.at(-1).reply, `Chat repeat result differs: ${run.id}`);
            assert.equal(record.totalCalls, record.sessions.reduce((n, s) => n + s.calls, 0), `Wrong chat call count: ${run.id}`);
          } else if (nativeEmbeddings) {
            assert(record.rawIntermediateTensorsCaptured === false && record.requests?.length === 21 && record.sessions.length === 30 && record.batch === 1, `Incomplete native embeddings: ${run.id}`);
            const grouped = new Map();
            for (const request of record.requests) {
              const vector = request.response?.data?.[0]?.embedding;
              assert(request.status === 200 && request.dimensions === 2048 && request.allFinite && request.seconds > 0, `Invalid embedding request: ${run.id}`);
              assert(vector?.length === 2048 && vector.every(Number.isFinite), `Invalid embedding values: ${run.id}`);
              const norm = Math.hypot(...vector);
              assert(Math.abs(norm - 1) < 1e-4 && Math.abs(norm - request.norm) < 1e-5, `Unnormalized embedding: ${run.id}`);
              const bytes = Buffer.alloc(2048 * 4);
              vector.forEach((value, i) => bytes.writeFloatLE(value, i * 4));
              assert.equal(createHash('sha256').update(bytes).digest('hex'), request.vectorSha256, `Embedding hash differs: ${run.id}`);
              const events = record.nativeEvents.slice(request.nativeEventStart, request.nativeEventEnd).filter(e => e.event === 'execute');
              assert(events.length > 0 && events.length === request.axclCalls, `Missing per-request execution: ${run.id}`);
              assert.deepEqual([...new Set(events.map(e => e.model))].sort(), request.executedModels, `Request weights differ: ${run.id}`);
              const key = JSON.stringify([request.kind, request.input, request.repeat]);
              assert(!grouped.has(key), `Duplicate embedding request: ${run.id}`);
              grouped.set(key, vector.map(x => x / norm));
            }
            assert(record.retrieval?.length === 4 && record.repeats?.length === 9, `Missing retrieval comparisons: ${run.id}`);
            for (const result of record.retrieval) {
              assert(result.images.length === 3 && result.texts.length === 3, `Invalid retrieval sample count: ${run.id}`);
              const scores = result.images.map(img => result.texts.map(text => {
                const a = grouped.get(JSON.stringify(['image', img, result.repeat]));
                const b = grouped.get(JSON.stringify(['text-' + result.language, text, result.repeat]));
                assert(a && b, `Missing retrieval vector: ${run.id}`);
                return a.reduce((sum, x, i) => sum + x * b[i], 0);
              }));
              scores.forEach((row, i) => row.forEach((value, j) => assert(Math.abs(value - result.cosine[i][j]) < 1e-5, `Retrieval score differs: ${run.id}`)));
              const top = xs => xs.indexOf(Math.max(...xs));
              assert.deepEqual(scores.map(top), result.imageToTextTop, `Image ranking differs: ${run.id}`);
              assert.deepEqual([0, 1, 2].map(j => top(scores.map(row => row[j]))), result.textToImageTop, `Text ranking differs: ${run.id}`);
            }
            assert.equal(record.totalCalls, record.sessions.reduce((n, s) => n + s.calls, 0), `Wrong embedding call count: ${run.id}`);
          } else if (nativeApplication) {
            assert(record.transcripts?.length && record.transcripts.some(s => nonempty(s.text)), `Missing native application output: ${run.id}`);
            assert(Number.isFinite(record.audio?.durationSeconds) && record.audio.durationSeconds > 0, `Missing input duration: ${run.id}`);
            for (const segment of record.transcripts) {
              assert(Number.isFinite(segment.start_ms) && Number.isFinite(segment.end_ms) && segment.start_ms >= 0 && segment.end_ms >= segment.start_ms && segment.end_ms <= record.audio.durationSeconds * 1000 + 1 && Number.isInteger(segment.speaker), `Invalid transcript segment: ${run.id}`);
            }
          } else {
            assert(nonempty(record.text) && record.naturalEos === true && record.generatedFrames > 0 && record.generatedFrames < record.maxNewTokens, `Incomplete speech generation: ${run.id}`);
            if (nativeVoiceDesign) {
              assert(record.revision === '3d4e2e70131378bd8bfbe307ef2de01192f0bc32' && nonempty(record.instruct), `Missing VoiceDesign version or instruction: ${run.id}`);
              assert(record.sessions.length === 61 && record.generatedFrames < 128 && record.headSaturationObserved === false, `Incomplete VoiceDesign pipeline: ${run.id}`);
              assert(record.filesBefore.length === 87 && record.customerPackageVerified && record.cpuOperators.length === 3, `Missing VoiceDesign runtime preparation: ${run.id}`);
              assert.deepEqual(record.filesBefore, record.filesAfter, `VoiceDesign runtime files changed: ${run.id}`);
              assert(run.testedCompanionWeights.filter(w => w.repo === 'AXERA-TECH/Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650').length === 50 && run.testedCompanionWeights.filter(w => w.repo === 'AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650').length === 11, `VoiceDesign weight sources differ: ${run.id}`);
              const loads = record.nativeEvents.filter(e => e.event === 'load' && e.method === 'memory');
              assert(loads.length === 61 && record.nativeEvents.filter(e => e.event === 'unload').length === 61, `VoiceDesign models not released: ${run.id}`);
              for (const e of loads) {
                const source = run.testedCompanionWeights.find(w => w.repo === e.sourceRepo && w.revision === e.sourceRevision && w.file === e.model);
                assert(source?.sha256 === e.hostTransferSha256, `VoiceDesign transferred model differs: ${run.id}`);
              }
            }
            assert(record.audio?.allFinite === true && record.audio.sampleRate > 0 && record.audio.sampleCount > 0 && record.audio.rms > 0 && record.audio.peak >= record.audio.rms, `Invalid synthesized waveform: ${run.id}`);
            assert.equal(record.audio.durationSeconds, record.audio.sampleCount / record.audio.sampleRate, `Wrong speech duration: ${run.id}`);
            const audio = variant.audio?.find(item => item.path.endsWith('/generated.wav'));
            assert(audio && audio.path.startsWith('/validation/effects/'), `Missing actual speech audio: ${run.id}`);
            const bytes = fs.readFileSync(path.join(root, 'static', audio.path));
            assert.equal(createHash('sha256').update(bytes).digest('hex'), record.audio.sha256, `Synthesized audio hash differs: ${run.id}`);
            assert.equal(record.totalCalls, record.sessions.reduce((n, s) => n + s.calls, 0), `Wrong speech call count: ${run.id}`);
          }
        }
        if (variant.record.inferenceEvidence === 'omni-media-text-and-complete-speech') {
          const record = variant.record;
          assert(run.modelId === 'Qwen2.5-Omni-3B' && run.revision === '38c42b43ece9cca5acf024aeddd8d0a188eca44d', `Unexpected Omni revision: ${run.id}`);
          const imageMode = record.mode === 'image';
          assert(['image', 'video'].includes(record.mode) && record.sessions.length === (imageMode ? 65 : 66), `Incomplete Omni model coverage: ${run.id}`);
          assert(result.variants.length === 4 && new Set(result.variants.map(v => v.record.case)).size === 4, `Missing Omni image/video examples: ${run.id}`);
          const manifest = read('static' + run.evidence.find(e => e.path.endsWith('/download-manifest.json')).path);
          assert(manifest.files.length === 105 && manifest.runnerSha256 === record.customerPackageSha256, `Omni package/weights differ: ${run.id}`);
          const expected = manifest.files.filter(f => f.path.endsWith('.axmodel') && !(imageMode && f.path.endsWith('/audio_tower.axmodel'))).map(f => f.path).sort();
          assert.deepEqual(record.sessions.map(s => s.model).sort(), expected, `Omni executed weight mapping differs: ${run.id}`);
          for (const session of record.sessions) {
            assert(manifest.files.find(f => f.path === session.model)?.verifiedHashes.sha256 === session.sha256, `Omni weight hash differs: ${run.id}`);
            assert(session.calls > 0 && session.released && session.allFinite && session.allReturnCodesZero && session.nativeTiming.repeat === session.calls, `Incomplete Omni calls: ${run.id}`);
            assert([session.nativeTiming.minimum, session.nativeTiming.mean, session.nativeTiming.maximum].every(x => Number.isFinite(x) && x >= 0), `Invalid Omni timings: ${run.id}`);
          }
          assert(record.totalCalls === record.sessions.reduce((n, s) => n + s.calls, 0) && record.cpuOnnxModels === 2 && record.cleanShutdown, `Incomplete Omni execution: ${run.id}`);
          assert(record.allModelsVerifiedBeforeAndAfter && record.verifiedModelFiles === 105 && record.completeReplyTokensPreserved, `Missing Omni provenance: ${run.id}`);
          assert(record.thinkerEosToken === 151645 && record.thinkerTokenIds.at(-1) === 151645 && !record.thinkerTokenIds.slice(0, -1).includes(151645), `Incomplete Omni reply: ${run.id}`);
          assert(record.speechSegments.length > 0 && record.speechSegments.every(s => s.tokenIds.length > 0 && s.tokenIds.length <= 20 && s.codecTokens > 0 && s.codecTokens <= 600 && s.terminalEos && [8292, 8294].includes(s.eosToken) && s.samples === s.codecTokens * 480), `Incomplete Omni speech segments: ${run.id}`);
          assert.deepEqual(record.speechSegments.flatMap(s => s.tokenIds), record.thinkerTokenIds.slice(0, -1), `Omni reply truncated: ${run.id}`);
          assert.equal(record.speechSegments.map(s => s.text).join(''), record.fullText, `Omni text changed: ${run.id}`);
          assert(record.samples[0].output === record.fullText && record.fullQualityAccepted === false && nonempty(record.observation), `Omni effect scope missing: ${run.id}`);
          for (const [url, digest] of [[record.inputPath, record.inputSha256], [record.audioPath, record.waveform.wavSha256]]) {
            assert(run.evidence.some(e => e.path === url), `Missing Omni media: ${run.id}`);
            assert.equal(createHash('sha256').update(fs.readFileSync(path.join(root, 'static', url))).digest('hex'), digest, `Omni media bytes differ: ${run.id}`);
          }
          const wav = fs.readFileSync(path.join(root, 'static', record.audioPath));
          assert(wav.subarray(0, 4).toString() === 'RIFF' && wav.subarray(8, 12).toString() === 'WAVE' && wav.readUInt32LE(4) + 8 === wav.length, `Invalid Omni WAV: ${run.id}`);
          const chunks = new Map();
          for (let offset = 12; offset + 8 <= wav.length;) {
            const tag = wav.subarray(offset, offset + 4).toString();
            const size = wav.readUInt32LE(offset + 4);
            assert(!chunks.has(tag) && offset + 8 + size <= wav.length, `Invalid Omni WAV chunk: ${run.id}`);
            chunks.set(tag, wav.subarray(offset + 8, offset + 8 + size));
            offset += 8 + size + (size % 2);
          }
          const fmt = chunks.get('fmt '), samples = chunks.get('data');
          assert(fmt && samples && fmt.readUInt16LE(0) === 3 && fmt.readUInt16LE(2) === 1 && fmt.readUInt32LE(4) === 24000 && fmt.readUInt16LE(14) === 32, `Wrong Omni audio format: ${run.id}`);
          assert(record.waveform.sampleRate === 24000 && record.waveform.allFinite && samples.length === record.waveform.samples * 4 && record.waveform.samples === record.speechSegments.reduce((n, s) => n + s.samples, 0), `Omni waveform truncated: ${run.id}`);
          assert.equal(record.waveform.seconds, record.waveform.samples / 24000, `Omni audio duration differs: ${run.id}`);
          assert.equal(createHash('sha256').update(samples).digest('hex'), record.waveform.sha256, `Omni complete waveform differs: ${run.id}`);
          let peak = 0;
          for (let i = 0; i < samples.length; i += 4) {
            const value = samples.readFloatLE(i); assert(Number.isFinite(value), `Non-finite Omni audio: ${run.id}`); peak = Math.max(peak, Math.abs(value));
          }
          assert(peak > 0 && Math.abs(peak - record.waveform.peak) < 1e-7, `Silent or altered Omni waveform: ${run.id}`);
        }
        for (const session of variant.record.sessions) {
          const companion = run.testedCompanionWeights?.find(w => w.repo === session.sourceRepo && w.revision === session.sourceRevision && w.file === session.model && w.sha256 === session.sha256);
          assert(run.testedCompanionWeights ? companion : run.testedWeightFiles?.includes(session.model), `Unmapped result weight: ${run.id}`);
          assert(session.runMilliseconds.every(value => Number.isFinite(value) && value >= 0), `Invalid timings: ${run.id}`);
          assert(session.runMilliseconds.length ? (nativeApplication || nativeSpeech || nativeEmbeddings || nativeChat || nativeCliVision || nativeQwen25 || nativeQwen3Fixed || nativeMimo || nativeReconstruction || nativeVoice || nativeCv || session.allFinite === true) : session.nativeTiming?.repeat > 0, `Missing inference checks: ${run.id}`);
        }
        if (variant.record.inferenceEvidence === 'official-speech-http-and-raw-axcl-output') {
          const record = variant.record;
          const speechFileCounts = {'Speech-Translation.axera': 135, 'Spoken-Communication.axera': 122};
          assert(Object.hasOwn(speechFileCounts, record.modelId), `Unknown speech pipeline: ${run.id}`);
          assert(record.provider === 'AXCLRTExecutionProvider' && nonempty(record.originalText) && nonempty(record.translatedText), `Missing speech pipeline text: ${run.id}`);
          assert.deepEqual(record.sessions.map(s => s.model).sort(), ['ax_model/sensevoice.axmodel', 'ax_model/vad.axmodel', 'libmelotts/models/decoder-zh.axmodel'], `Speech weight mapping differs: ${run.id}`);
          assert(record.sessions.every(s => s.released && s.calls > 0 && s.calls === s.runMilliseconds.length), `Speech weights not executed and released: ${run.id}`);
          assert.equal(record.totalCalls, record.sessions.reduce((sum, s) => sum + s.calls, 0), `Speech call count differs: ${run.id}`);
          assert.equal(record.cpuEncoder, 'libmelotts/models/encoder-zh.onnx', `Unexpected speech CPU encoder: ${run.id}`);
          assert(record.filesBefore.length === speechFileCounts[record.modelId] && record.filesBefore.every(f => f.matched) && record.filesAfter.every(f => f.matched), `Missing speech file checks: ${run.id}`);
          assert.deepEqual(record.filesBefore, record.filesAfter, `Speech files changed: ${run.id}`);
          const companion = record.companion;
          assert(companion.repo === 'AXERA-TECH/Qwen2.5-1.5B-Instruct' && companion.revision === 'eaa03390b75ff42286b46ad492d007ce536b303d', `Wrong speech companion: ${run.id}`);
          assert(companion.modelCount === 29 && companion.files.length === 29 && companion.allReturnCodesZero && companion.cleanShutdown && companion.mmapEmbedding === false, `Incomplete speech API evidence: ${run.id}`);
          const required = Array.from({length: 28}, (_, i) => `qwen2.5-1.5b-ctx-ax650/qwen2_p128_l${i}_together.axmodel`).concat('qwen2.5-1.5b-ctx-ax650/qwen2_post.axmodel');
          assert.deepEqual(companion.files.map(f => f.path).sort(), required.sort(), `Speech companion layers differ: ${run.id}`);
          assert(companion.files.every(f => /^[a-f0-9]{64}$/.test(f.sha256) && f.calls > 0) && companion.calls === companion.files.reduce((sum, f) => sum + f.calls, 0), `Invalid speech companion calls: ${run.id}`);
          assert(record.outputAudio.sampleRate === 44100 && record.outputAudio.channels === 1 && record.outputAudio.frames > 0 && record.outputAudio.peak > 0 && record.outputAudio.rms > 0, `Missing speech audio output: ${run.id}`);
          assert.equal(record.outputAudio.seconds, record.outputAudio.frames / 44100, `Wrong speech output duration: ${run.id}`);
          for (const [audioPath, digest] of [[record.inputAudioPath, record.inputSha256], [record.outputAudioPath, record.outputAudio.sha256]]) {
            assert(variant.audio?.some(audio => audio.path === audioPath) && run.evidence.some(e => e.path === audioPath), `Missing speech audio attachment: ${run.id}`);
            assert.equal(createHash('sha256').update(fs.readFileSync(path.join(root, 'static', audioPath))).digest('hex'), digest, `Speech audio bytes differ: ${run.id}`);
          }
          assert(record.samples.length === 1 && record.samples[0].output === record.translatedText && record.samples[0].input.includes(record.originalText), `Speech display text differs: ${run.id}`);
        }
        if (variant.record.inferenceEvidence === 'official-ml-http-and-raw-axcl-output') {
          const record = variant.record;
          assert(record.provider === 'AXCLRTExecutionProvider' && record.applicationPackageUnchanged && record.cleanShutdown, `Incomplete ML application lifecycle: ${run.id}`);
          assert(record.requests?.length === 24 && record.calls?.length === 24 && record.sessions.length === 4, `Missing ML HTTP inference coverage: ${run.id}`);
          for (const [index, request] of record.requests.entries()) {
            const call = record.calls[index];
            assert(request.status === 200 && request.seconds > 0 && call.index === index && call.allFinite, `Invalid ML HTTP request: ${run.id}`);
            assert(call.sourceRepo === `AXERA-TECH/${request.modelId}` && call.model === `${request.mode}/model.axmodel`, `ML request model differs: ${run.id}`);
            assert(call.outputs?.[0].dtype === 'float32' && JSON.stringify(call.outputs[0].shape) === '[1,768]', `Invalid ML embedding dimensions: ${run.id}`);
            const vector = typeof request.response.clip === 'string' ? JSON.parse(request.response.clip) : request.response.clip;
            assert(Array.isArray(vector) && vector.length === 768 && vector.every(Number.isFinite), `Invalid ML HTTP embedding: ${run.id}`);
          }
          for (const session of record.sessions) {
            const calls = record.calls.filter(c => c.sourceRepo === session.sourceRepo && c.model === session.model);
            assert.equal(session.calls, 6, `Missing repeated ML inputs: ${run.id}`);
            assert.deepEqual(session.runMilliseconds, calls.map(c => c.milliseconds), `ML request timings differ: ${run.id}`);
          }
          assert(record.retrieval?.length === 2 && record.retrieval.every(r => r.repeatedVectorsIdentical && r.cosine.length === 3 && r.cosine.every(row => row.length === 3 && row.every(v => Number.isFinite(v) && v >= -1.00001 && v <= 1.00001))), `Missing bilingual retrieval scores: ${run.id}`);
        }
        for (const preview of [...variant.previews, ...(variant.audio ?? []), ...(variant.videos ?? [])]) {
          assert(nonempty(preview.caption) && run.evidence.some(item => item.path === preview.path), `Missing preview asset: ${run.id}`);
        }
        if (variant.textSamples && !nativeChat && !nativeCliVision && !nativeQwen25 && !nativeQwen3Fixed && !nativeMimo && !nativeVideoAgent && !nativeOpenClaw) {
          assert.equal(variant.textSamples.length, variant.record.samples.length, `Text sample count differs from record: ${run.id}`);
          for (const [index, sample] of variant.textSamples.entries()) {
            const recorded = variant.record.samples[index];
            assert(nonempty(sample.input) && nonempty(sample.output) && nonempty(sample.observation), `Missing Python text example: ${run.id}`);
            assert.equal(sample.input, recorded.input, `Text input differs from record: ${run.id}`);
            assert.equal(sample.output, recorded.output, `Text output differs from record: ${run.id}`);
            assert(recorded.hitEos === true && recorded.stopReason === 'eos', `Incomplete Python text response: ${run.id}`);
            for (const picture of sample.images ?? []) assert(run.evidence.some(e => e.path === picture.path), `Missing text input image: ${run.id}`);
          }
        }
        for (const video of variant.videos ?? []) assert(video.path.endsWith('.mp4'), `Invalid video format: ${run.id}`);
      }
    }
  }
}
const publicAttachments = new Set(validation.runs.flatMap(run => run.evidence.map(item => path.resolve(root, 'static', '.' + item.path))));
function checkPublicFiles(directory) {
  for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) checkPublicFiles(file);
    else assert(publicAttachments.has(file), `Unreviewed file in public model effects: ${file}`);
  }
}
checkPublicFiles(path.join(root, 'static/validation'));
const originals = new Map(source.repositories.map(m=>[m.repo,m]));
assert.equal(source.count, originals.size, 'Duplicate source repositories');
assert.equal(facts.length,source.count,'Coverage differs from source snapshot');
assert.equal(catalog.length,facts.length,'Catalog and facts differ');
assert.equal(new Set(facts.map(m=>m.guide)).size,facts.length,'A guide is reused for different repositories');
for(const m of facts){
  const upstream = originals.get(m.repo);
  assert(upstream,`Repository missing in snapshot: ${m.repo}`);
  assert.equal(m.sha,upstream.sha,`Revision mismatch: ${m.id}`);
  assert(/^[0-9a-f]{40}$/.test(m.sha),`Non-fixed revision: ${m.id}`);
  const indexed = catalog.find(x=>x.id===m.id);
  for(const key of ['slug','guide','sha','kind','status'])assert.equal(indexed?.[key],m[key],`Index mismatch ${m.id}: ${key}`);
  const files = new Set(upstream.files);
  if (m.compiledVariants) {
    assert(m.weightCount === 0 && !m.localGuide && !m.files.some(file => file.endsWith('.axmodel')), `Compiled alternatives require a source-only repository: ${m.id}`);
    assert(Array.isArray(m.compiledVariants) && m.compiledVariants.length > 0 && new Set(m.compiledVariants).size === m.compiledVariants.length, `Invalid compiled alternatives: ${m.id}`);
    for (const id of m.compiledVariants) {
      const variant = modelFacts.get(id);
      assert(variant && variant.id !== m.id && variant.weightCount > 0 && variant.readme, `Missing compiled alternative: ${m.id}: ${id}`);
    }
  }
  for(const file of [...m.keyFiles,...m.entryPoints.map(e=>e.path),...m.scripts.map(s=>s.path)])assert(files.has(file),`Missing source file ${m.id}: ${file}`);
  if (m.localGuide) {
    assert(['python', 'cv', 'legacy', 'axllm'].includes(m.kind) && /^[a-z0-9-]+\.md$/.test(m.localGuide), `Invalid local recipe: ${m.id}`);
    const recipe = fs.readFileSync(path.join(root, 'scripts/model-recipes', m.localGuide), 'utf8');
    const generatedDeviceZero = m.config?.generated === true && m.config.devices?.length === 1 && m.config.devices[0] === 0 && recipe.includes("assert config['devices'] == [0]");
    assert(recipe.includes('AXCLRTExecutionProvider') || recipe.includes('AxDeviceType.axcl_device') || recipe.includes('speaker_compare.py') || (['cv', 'legacy'].includes(m.kind) && recipe.includes('AXCL')) || (m.kind === 'axllm' && recipe.includes('AXCL') && (recipe.includes('AXLLM_DEVICES=0') || generatedDeviceZero) && recipe.includes('serve')), `Local recipe lacks AXCL setup: ${m.id}`);
    assert(m.downloadFiles?.length && m.downloadFiles.every(file => files.has(file)), `Local recipe download file absent from source snapshot: ${m.id}`);
    if (m.prerequisitesHandledByRecipe) assert(recipe.includes('## 准备') && recipe.includes('device-check.md'), 'Missing prerequisites in recipe: ' + m.id);
  }
  if(['cv','python'].includes(m.kind) && !m.localGuide){
    for(const key of ['model','input',...(m.kind==='python'?['entry']:[])])assert(files.has(m.recipe[key]),`Recipe file not in snapshot ${m.id}: ${key}`);
    if(m.kind==='python')assert(m.recipe.args.includes('AXCLRTExecutionProvider')||m.recipe.providerEdits.length,`Python lacks explicit AXCL choice: ${m.id}`);
  }
  if(m.kind==='axllm'){
    assert(m.config && m.config.layers>0,`Missing runtime configuration: ${m.id}`);
    assert(!/ax620|ax630|ax637/i.test(m.config.config),`Selected another chip's config: ${m.id}`);
    assert(m.config.layerFiles.length===m.config.layers,`Layer pattern not expanded: ${m.id}`);
    for(const file of m.config.layerFiles){
      assert(files.has(file),`Configuration reference missing ${m.id}: ${file}`);
      assert(!/ax620|ax630|ax637/i.test(file),`Wrong target weight ${m.id}: ${file}`);
    }
    const checkConfigSource = ref => {
      const origin = originals.get(ref.sourceRepo);
      assert(origin && origin.sha === ref.sourceRevision && origin.files.includes(ref.path), `Missing fixed external configuration source: ${m.id}: ${ref.path}`);
    };
    if (m.config.generated) {
      assert(m.localGuide && m.config.source, `Generated configuration lacks recipe or source: ${m.id}`);
      checkConfigSource(m.config.source);
    }
    for (const ref of m.config.references) {
      if (ref.sourceRepo) checkConfigSource(ref);
      else assert(files.has(ref.path), `Configuration reference missing ${m.id}: ${ref.path}`);
      assert(!/ax620|ax630|ax637/i.test(ref.path), `Wrong target weight ${m.id}: ${ref.path}`);
    }
    assert(!['tts','asr','pipeline'].includes(m.profile),`A pipeline is treated as plain LLM: ${m.id}`);
  }
  const page = fs.readFileSync(path.join(root,'docs',m.guide+'.md'),'utf8');
  assert(page.includes(m.sha),`Guide lacks pinned revision: ${m.id}`);
  assert(page.includes(m.id),`Guide lacks model name: ${m.id}`);
  const runs = validation.runs.filter(run => run.modelId === m.id);
  if (m.kind !== 'resource' && !runs.length) {
    const pendingLabel = m.pendingValidationNote ? '尚未通过本机部署验证' : '本机尚未实测';
    assert(page.includes(pendingLabel), `Pending validation scope missing: ${m.id}`);
    if (m.pendingValidationNote) assert(typeof m.pendingValidationNote === 'string' && page.includes(m.pendingValidationNote), `Pending availability note missing: ${m.id}`);
  }
  if (runs.length) {
    assert(page.includes('## 查看部署效果'), `Hardware validation section missing: ${m.id}`);
    assert(!page.includes('尚未在当前 RK3576 + 算力卡环境运行') && !page.includes('本机尚未实测'), `Stale pending statement: ${m.id}`);
    for (const run of displayedRuns([...runs].sort((a, b) => b.date.localeCompare(a.date)))) {
      assert(page.includes(run.revision), `Missing effect version: ${run.id}`);
      if (run.status !== 'passed') assert(page.includes(run.summary), `Missing pending result: ${run.id}`);
      for (const evidence of run.evidence.filter(item => /\.(png|jpe?g|webp|gif|wav|mp3)$/i.test(item.path))) {
        if (run.status === 'passed') assert(page.includes('../../../static' + evidence.path.split('/').map(encodeURIComponent).join('/')), `Missing sample media: ${run.id}`);
      }
    }
  }
  if (m.kind !== 'resource') assert(page.includes('## 查看部署效果'), `Missing effect section: ${m.id}`);
  assert(!page.includes('undefined'),'Undefined text in '+m.id);
  assert(!/memory-diagnosis|dmesg-after|device-failure|host-samples|完整命令，路径和记录工具/.test(page), 'Internal diagnostic content in '+m.id);
}
console.log(`Model audit passed: ${facts.length} repositories, unique pages, fixed revisions, source files and ${validation.runs.length} evidence-backed validation records.`);
