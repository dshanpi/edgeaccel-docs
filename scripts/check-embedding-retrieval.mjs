import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const dot = (a,b) => a.reduce((sum,x,i) => sum + x*b[i],0);
const norm = a => Math.sqrt(dot(a,a));

export function checkEmbeddingRetrieval({root,run,manifestSha256}) {
  const evidence = run.evidence.find(e => e.path.endsWith('/retrieval-quality.json'));
  if (!evidence) return;
  const r = JSON.parse(fs.readFileSync(path.join(root,'static',evidence.path),'utf8'));
  assert.equal(r.kind,'compiled-embedding-constructed-retrieval');
  assert.equal(r.revision,run.revision);
  assert.equal(r.modelId,run.modelId);
  assert.equal(r.packageManifestSha256,manifestSha256);
  assert.equal(r.actualCapacity,'16GB');
  assert.equal(r.fullLayers,28);
  assert.equal(r.qualityTaskComplete,false);
  assert(r.authorship.includes('not a public benchmark') && r.authorship.includes('not independent human annotation'));
  assert.equal(r.runtimeSha256,sha(fs.readFileSync(path.join(root,'static',r.runtimePath))));
  const inputBytes = fs.readFileSync(path.join(root,'static',r.inputPath));
  assert.equal(r.inputSha256,sha(inputBytes));
  const input = JSON.parse(inputBytes);
  assert.equal(r.queries.length,41); assert.equal(r.documents.length,20);
  assert.equal(new Set(r.queries.slice(0,40).map(q=>q.text)).size,40);
  assert.equal(new Set(r.documents.map(d=>d.id)).size,20);
  assert.deepEqual(input.queries,r.queries.map(q=>q.text));
  assert.deepEqual(input.documents,r.documents.map(d=>d.text));
  assert.deepEqual(r.record.texts,input.queries.map(q=>`Instruct: ${input.instruction}\nQuery:${q}`).concat(input.documents));
  assert.equal(r.record.provider,'AXCLRTExecutionProvider');
  assert.equal(r.cardVectors.length,61); assert.equal(r.cpuVectors.length,61);
  assert.equal(r.record.samples.length,61);
  let calls=0, minCos=1, maxScoreDelta=0;
  for(let i=0;i<61;i++) {
    const a=r.cardVectors[i], b=r.cpuVectors[i], s=r.record.samples[i];
    assert(a.length===1024 && b.length===1024 && a.every(Number.isFinite) && b.every(Number.isFinite));
    assert(Math.abs(norm(a)-1)<1e-5 && Math.abs(norm(b)-1)<1e-5);
    const cos=dot(a,b)/norm(a)/norm(b); assert(cos>=0.99); minCos=Math.min(minCos,cos);
    assert(Number.isInteger(s.tokens) && s.tokens>=1 && s.tokens<=512);
    assert.equal(s.chunks,Math.ceil(s.tokens/128));
    assert.equal(s.decoderExecutions,s.chunks*28); assert.equal(s.postExecutions,1);
    calls+=s.decoderExecutions+s.postExecutions;
  }
  assert.equal(r.nativeCalls,calls);
  assert.deepEqual(r.cardVectors[0],r.cardVectors[40]);
  assert.equal(r.queries[40].repeatOf,r.queries[0].id);
  assert.equal(r.queries[40].text,r.queries[0].text);
  const ranks=[],cpuRanks=[];
  for(let i=0;i<41;i++) {
    const scores=r.documents.map((_,j)=>dot(r.cardVectors[i],r.cardVectors[j+41]));
    const cpuScores=r.documents.map((_,j)=>dot(r.cpuVectors[i],r.cpuVectors[j+41]));
    assert.equal(r.record.similarities[i].length,20);
    for(let j=0;j<20;j++) {
      assert(Math.abs(scores[j]-r.record.similarities[i][j])<1e-6);
      maxScoreDelta=Math.max(maxScoreDelta,Math.abs(scores[j]-cpuScores[j]));
    }
    const order=scores.map((s,j)=>({s,j})).sort((a,b)=>b.s-a.s).map(x=>x.j);
    const cpuOrder=cpuScores.map((s,j)=>({s,j})).sort((a,b)=>b.s-a.s).map(x=>x.j);
    assert.equal(r.record.matches[i].documentIndex,order[0]);
    if(i===40) continue;
    assert.equal(r.queries[i].relevantDocumentIds.length,1);
    const target=r.queries[i].relevantDocumentIds[0];
    const rank=order.findIndex(j=>r.documents[j].id===target)+1;
    const cpuRank=cpuOrder.findIndex(j=>r.documents[j].id===target)+1;
    assert(rank>0 && cpuRank>0); ranks.push(rank); cpuRanks.push(cpuRank);
    assert.equal(r.ranks[i].id,r.queries[i].id); assert.equal(r.ranks[i].rank,rank);
    assert.deepEqual(r.ranks[i].allRanks.map(x=>x.documentId),order.map(j=>r.documents[j].id));
    assert.equal(r.numericalComparison.rows[i].cpuRank,cpuRank);
  }
  assert(maxScoreDelta<=0.02);
  assert(Math.abs(r.numericalComparison.minCpuCosine-minCos)<1e-6);
  assert(Math.abs(r.numericalComparison.maxRetrievalScoreDifference-maxScoreDelta)<1e-6);
  assert.equal(r.numericalComparison.cpuTop1Hits,cpuRanks.filter(n=>n===1).length);
  const metrics={hitAt1:ranks.filter(n=>n===1).length/40,hitAt3:ranks.filter(n=>n<=3).length/40,
    mrrAt20:ranks.reduce((s,n)=>s+1/n,0)/40,recallAt3:ranks.filter(n=>n<=3).length/40,
    ndcgAt3:ranks.reduce((s,n)=>s+(n<=3?1/Math.log2(n+1):0),0)/40};
  for(const [key,value] of Object.entries(metrics)) assert(Math.abs(r.metrics[key]-value)<1e-10);
  assert(r.repeatedQueryExact && r.cleanShutdown && r.pretrainedPackagePosthashMatched);
}
