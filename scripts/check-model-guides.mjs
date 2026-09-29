import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
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
  assert(typeof run.date === 'string' && /^\d{4}-\d{2}-\d{2}(?:T.*)?$/.test(run.date) && !Number.isNaN(Date.parse(run.date)), `Invalid validation date: ${run.id}`);
  assert.equal(run.revision, model.sha, `Test revision differs from documented model revision: ${run.id}`);
  if (run.testedWeightFiles) {
    assert(Array.isArray(run.testedWeightFiles) && run.testedWeightFiles.length, `Empty tested file list: ${run.id}`);
    assert(run.testedWeightFiles.every(file => model.files.includes(file) && file.endsWith('.axmodel')), `Tested weight absent from source: ${run.id}`);
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
    assert(/\.(png|jpe?g|webp|gif|wav|mp3|mp4)$/i.test(evidence.path) || ['api.json', 'download-manifest.json', 'media-manifest.json', 'speaker-result.json', 'sensevoice-result.json', 'tts-result.json', 'classification-result.json', 'punctuation-result.json', 'qrcode-result.json', 'decision-result.json', 'enhancement-result.json', 'deployment-result.json', 'text-result.json'].includes(path.basename(evidence.path)), `Unexpected customer attachment: ${evidence.path}`);
    assert(!/[\\?#]/.test(evidence.path) && !evidence.path.split('/').includes('..'), `Unsafe evidence path: ${run.id}`);
    const evidencePath = path.resolve(root, 'static', '.' + evidence.path);
    const evidenceRoot = path.resolve(root, 'static', 'validation') + path.sep;
    assert(evidencePath.startsWith(evidenceRoot), `Evidence escapes validation directory: ${run.id}`);
    assert(fs.existsSync(evidencePath) && fs.statSync(evidencePath).isFile(), `Evidence file missing: ${evidence.path}`);
    assert(fs.statSync(evidencePath).size > 0, `Evidence file is empty: ${evidence.path}`);
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
        assert(sample.exitCode === 0 && Number.isFinite(sample.processSeconds) && sample.processSeconds > 0, `Invalid text process result: ${run.id}`);
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
        assert(nonempty(variant.label) && nonempty(variant.observation), `Missing variant explanation: ${run.id}`);
        assert(variant.record?.completed === true, `Incomplete deployment result: ${run.id}`);
        assert(['AXCLRTExecutionProvider', 'AXCL C++', 'AXCL C API'].includes(variant.record.provider), `Non-card result: ${run.id}`);
        for (const session of variant.record.sessions) {
          assert(run.testedWeightFiles.includes(session.model), `Unmapped result weight: ${run.id}`);
          assert(session.runMilliseconds.every(value => Number.isFinite(value) && value >= 0), `Invalid timings: ${run.id}`);
          assert(session.runMilliseconds.length ? session.allFinite === true : session.nativeTiming?.repeat > 0, `Missing inference checks: ${run.id}`);
        }
        for (const preview of [...variant.previews, ...(variant.audio ?? []), ...(variant.videos ?? [])]) {
          assert(nonempty(preview.caption) && run.evidence.some(item => item.path === preview.path), `Missing preview asset: ${run.id}`);
        }
        if (variant.textSamples) {
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
  for(const file of [...m.keyFiles,...m.entryPoints.map(e=>e.path),...m.scripts.map(s=>s.path)])assert(files.has(file),`Missing source file ${m.id}: ${file}`);
  if (m.localGuide) {
    assert(['python', 'cv', 'legacy', 'axllm'].includes(m.kind) && /^[a-z0-9-]+\.md$/.test(m.localGuide), `Invalid local recipe: ${m.id}`);
    const recipe = fs.readFileSync(path.join(root, 'scripts/model-recipes', m.localGuide), 'utf8');
    const generatedDeviceZero = m.config?.generated === true && m.config.devices?.length === 1 && m.config.devices[0] === 0 && recipe.includes("assert config['devices'] == [0]");
    assert(recipe.includes('AXCLRTExecutionProvider') || recipe.includes('AxDeviceType.axcl_device') || recipe.includes('speaker_compare.py') || (['cv', 'legacy'].includes(m.kind) && recipe.includes('AXCL')) || (m.kind === 'axllm' && recipe.includes('AXCL') && (recipe.includes('AXLLM_DEVICES=0') || generatedDeviceZero) && recipe.includes('serve')), `Local recipe lacks AXCL setup: ${m.id}`);
    assert(m.downloadFiles?.length && m.downloadFiles.every(file => files.has(file)), `Local recipe download file absent from source snapshot: ${m.id}`);
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
  if (m.kind !== 'resource' && !runs.length) assert(page.includes('本机尚未实测'), `Pending validation scope missing: ${m.id}`);
  if (runs.length) {
    assert(page.includes('## 查看部署效果'), `Hardware validation section missing: ${m.id}`);
    assert(!page.includes('尚未在当前 RK3576 + 算力卡环境运行') && !page.includes('本机尚未实测'), `Stale pending statement: ${m.id}`);
    for (const run of runs) {
      assert(page.includes(run.revision), `Missing effect version: ${run.id}`);
      if (run.status === 'passed') assert(page.includes(run.date), `Missing sample date: ${run.id}`);
      else assert(page.includes(run.summary), `Missing pending result: ${run.id}`);
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
