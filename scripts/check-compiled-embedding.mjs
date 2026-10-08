import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {checkEmbeddingRetrieval} from './check-embedding-retrieval.mjs';
import {checkExternalRetrieval} from './check-external-retrieval.mjs';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const dot = (a, b) => a.reduce((sum, value, i) => sum + value * b[i], 0);
const norm = a => Math.sqrt(dot(a, a));

export function checkCompiledEmbedding({root, model, run}) {
  assert.equal(model.id, 'Qwen3-Embedding-0.6B-GPTQ-Int8');
  assert.equal(run.revision, '4c972fca3731832e33899e14da1555dd78c3f8d6');
  assert(!run.testedWeightFiles && !run.testedCompanionWeights, 'Derived weights must not be attributed to upstream AXModels');
  assert.equal(run.testedDerivedWeights.manifest, '/examples/qwen3-embedding/tested-package.json');
  const bytes = fs.readFileSync(path.join(root, 'static', run.testedDerivedWeights.manifest));
  const manifest = JSON.parse(bytes);
  assert.equal(manifest.sourceRevision, run.revision);
  assert.deepEqual(manifest.compiler, {version: '7.0-patch1', commit: '29f4c81a', imageId: 'sha256:f9d2e54003775abaa782acb2bf92cbd5e3f19c88b7e5615bb3e6673da80b456e'});
  assert.deepEqual(manifest.profile, {chip: 'AX650', layers: 28, prefillLength: 512, prefillStep: 128,
    hiddenStateType: 'bf16', weightType: 's8', postWeightType: 'bf16', parallel: 1, maxContext: 1024});
  assert.equal(manifest.sourceFiles.length, model.files.length);
  assert.deepEqual(manifest.sourceFiles.map(f => f.path).sort(), [...model.files].sort());
  for (const file of manifest.sourceFiles) assert(file.size > 0 && /^[a-f0-9]{64}$/.test(file.sha256));
  assert.equal(manifest.sourceFiles.find(f => f.path === 'model.safetensors').sha256,
    '3ef6e7ba596d1d4ff7aa0e119eae4c602c1ef81017dcb12febce66cfb2e54708');
  assert.equal(manifest.sourceFiles.find(f => f.path === 'config.json').sha256,
    '3685971057fdecc9db898989c82d7561318b08dd064806ae1f63f225cedc2252');
  const expectedNames = Array.from({length: 28}, (_, i) => `qwen3_p128_l${i}_together.axmodel`)
    .concat(['qwen3_post.axmodel', 'model.embed_tokens.weight.bfloat16.bin', 'tokenizer.json']);
  assert.deepEqual(manifest.files.map(f => f.file).sort(), expectedNames.sort());
  for (const file of manifest.files) assert(file.bytes > 0 && /^[a-f0-9]{64}$/.test(file.sha256));
  assert.equal(manifest.files.find(f => f.file === 'qwen3_post.axmodel').sha256,
    '42d757c47f4eb3a849523f6a133f322c623d59e482d1f1df94df0a0e884df86f');
  assert.equal(manifest.files.find(f => f.file === 'model.embed_tokens.weight.bfloat16.bin').sha256,
    'a55b140d86852835bd18d8200222a9f302340730f0670eb7e23a4895e5489033');
  const evidence = run.evidence.find(e => e.path.endsWith('/embedding-result.json'));
  assert(evidence, 'Missing complete embedding application result');
  const result = JSON.parse(fs.readFileSync(path.join(root, 'static', evidence.path)));
  assert.equal(result.kind, 'compiled-text-embedding');
  assert.equal(result.modelId, model.id);
  assert.equal(result.revision, run.revision);
  assert.equal(result.date, run.date);
  assert.equal(result.packageManifestSha256, digest(bytes));
  assert(result.completed && result.customerConverterRetested && result.cleanShutdown && result.actual8GBTested === false);
  assert.equal(result.runtimePath, '/examples/qwen3-embedding/qwen3_embedding_axcl.py');
  assert.equal(result.runtimeSha256, digest(fs.readFileSync(path.join(root, 'static', result.runtimePath))));
  assert.equal(result.converterPath, '/examples/qwen3-embedding/convert.py');
  assert.equal(result.converterSha256, digest(fs.readFileSync(path.join(root, 'static', result.converterPath))));
  assert.equal(result.examples.length, 2);
  let calls = 0;
  for (const example of result.examples) {
    const record = example.record;
    const payload = JSON.parse(fs.readFileSync(path.join(root, 'static/examples/qwen3-embedding', example.inputFile)));
    assert(['official-readme-example.json', 'chinese-retrieval-example.json'].includes(example.inputFile));
    assert.equal(record.provider, 'AXCLRTExecutionProvider');
    assert(record.normalized && record.dimensions === 1024 && record.batch === 1 && record.maxTokens === 512);
    assert(Number.isFinite(record.loadSeconds) && record.loadSeconds > 0);
    assert.deepEqual(record.queries, payload.queries);
    assert.deepEqual(record.documents, payload.documents);
    assert.deepEqual(record.texts, payload.queries.map(q => `Instruct: ${payload.instruction}\nQuery:${q}`).concat(payload.documents));
    assert.equal(record.samples.length, 4);
    assert.equal(example.vectors.length, 4);
    assert.equal(example.cpuVectors.length, 4);
    for (const [i, sample] of record.samples.entries()) {
      const vector = example.vectors[i], cpu = example.cpuVectors[i];
      assert(vector.length === 1024 && cpu.length === 1024 && vector.every(Number.isFinite) && cpu.every(Number.isFinite));
      assert(Math.abs(norm(vector) - 1) < 1e-5 && Math.abs(norm(cpu) - 1) < 1e-5);
      assert(dot(vector, cpu) / norm(vector) / norm(cpu) >= 0.99, 'Embedding CPU agreement failed');
      assert(Number.isInteger(sample.tokens) && sample.tokens >= 1 && sample.tokens <= 512);
      assert.equal(sample.chunks, Math.ceil(sample.tokens / 128));
      assert.equal(sample.decoderExecutions, 28 * sample.chunks);
      assert.equal(sample.postExecutions, 1);
      assert(Number.isFinite(sample.seconds) && sample.seconds > 0);
      calls += sample.decoderExecutions + sample.postExecutions;
    }
    assert.equal(record.similarities.length, 2);
    assert.equal(record.matches.length, 2);
    for (let i = 0; i < 2; i++) {
      assert.equal(record.similarities[i].length, 2);
      for (let j = 0; j < 2; j++) {
        const score = record.similarities[i][j];
        assert(Number.isFinite(score));
        assert(Math.abs(score - dot(example.vectors[i], example.vectors[j + 2])) < 1e-6);
        assert(Math.abs(score - dot(example.cpuVectors[i], example.cpuVectors[j + 2])) <= 0.02);
      }
      const match = record.matches[i];
      assert.equal(match.documentIndex, i);
      assert.equal(match.query, record.queries[i]);
      assert.equal(match.document, record.documents[i]);
      assert.equal(match.score, record.similarities[i][i]);
      assert(record.similarities[i][i] > record.similarities[i][1 - i]);
    }
  }
  assert.equal(result.customerNativeCalls, calls);
  assert.equal(calls, 232);
  checkEmbeddingRetrieval({root, run, manifestSha256: digest(bytes)});
  checkExternalRetrieval({root, run, manifestSha256: digest(bytes), manifest});
}
