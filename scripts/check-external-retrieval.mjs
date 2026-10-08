import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const sha=b=>createHash('sha256').update(b).digest('hex');
const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
const norm=a=>Math.sqrt(dot(a,a));
const close=(a,b,tolerance=1e-6)=>assert(Math.abs(a-b)<tolerance);

export function checkExternalRetrieval({root,run,manifestSha256,manifest}) {
  const item=run.evidence.find(e=>e.path.endsWith('/external-retrieval.json'));
  if(!item) return;
  const r=JSON.parse(fs.readFileSync(path.join(root,'static',item.path),'utf8'));
  assert.equal(r.kind,'compiled-embedding-external-retrieval');
  assert.equal(r.modelId,run.modelId); assert.equal(r.revision,run.revision);
  assert.equal(r.actualCapacity,'16GB'); assert.equal(r.fullLayers,28);
  assert.equal(r.fullBenchmarkEvaluated,false); assert.equal(r.sourceCorpusTextIncluded,false);
  assert(r.allDocumentTokensRetained && r.allRepeatedOutputsExact && r.cleanShutdown);
  assert.equal(r.packageManifestSha256,manifestSha256);
  assert.deepEqual(r.packageFilesBefore,r.packageFilesAfter);
  assert.deepEqual(r.packageFilesBefore,manifest.files.map(f=>({file:f.file,sha256:f.sha256,bytes:f.bytes})));
  assert.equal(r.runtimeSha256,sha(fs.readFileSync(path.join(root,'static',r.runtimePath))));
  assert.equal(r.cases.length,238); assert.equal(r.cardVectors.length,238); assert.equal(r.cpuVectors.length,238);
  let minCos=1,calls=0,maxDelta=0;
  for(let i=0;i<238;i++) {
    const c=r.cases[i],a=r.cardVectors[i],b=r.cpuVectors[i],s=c.stats;
    assert.equal(c.index,i); assert.equal(s.caseIndex,i); assert.equal(s.tokens,c.tokens);
    assert(!('text' in c) && !('tokenIds' in c));
    assert(Number.isInteger(c.tokens) && c.tokens>=1 && c.tokens<=512);
    assert(a.length===1024 && b.length===1024 && a.every(Number.isFinite) && b.every(Number.isFinite));
    close(norm(a),1,1e-5);close(norm(b),1,1e-5);
    const cosine=dot(a,b)/norm(a)/norm(b);assert(cosine>=0.99);minCos=Math.min(minCos,cosine);
    assert.equal(s.decoderExecutions,28*Math.ceil(c.tokens/128));assert.equal(s.postExecutions,1);
    calls+=s.decoderExecutions+s.postExecutions;
  }
  assert.equal(r.extraRepeatSamples.length,2);
  assert.deepEqual(new Set(r.extraRepeatSamples.map(s=>s.label)),new Set(['repeat-immediate','repeat-after-all']));
  for(const s of r.extraRepeatSamples) {
    assert.equal(s.caseIndex,0);assert.equal(s.tokens,r.cases[0].tokens);
    assert.equal(s.decoderExecutions,28*Math.ceil(s.tokens/128));assert.equal(s.postExecutions,1);
    calls+=s.decoderExecutions+s.postExecutions;
  }
  assert.equal(r.nativeCalls,calls);close(r.minCpuCosine,minCos);
  assert.equal(r.datasets.length,2);
  const seen=new Set();
  for(const d of r.datasets) {
    assert.equal(d.queryCases.length,16);assert.equal(d.rows.length,16);assert.equal(d.queries,16);
    assert.equal(d.documents,d.documentCases.length);
    const repo=d.name==='scifact'?'BeIR/scifact':'C-MTEB/DuRetrieval';assert.equal(d.repository,repo);
    assert(/^[a-f0-9]{40}$/.test(d.revision) && /^[a-f0-9]{40}$/.test(d.qrelsRevision));
    const docs=d.documentCases;
    for(const doc of docs) {
      assert(!('text' in doc));assert(/^[a-f0-9]{64}$/.test(doc.textSha256));
      let end=0;
      for(let j=0;j<doc.chunks.length;j++) {
        const chunk=doc.chunks[j],c=r.cases[chunk.caseIndex];seen.add(chunk.caseIndex);
        assert.equal(c.kind,'document-chunk');assert.equal(c.sourceId,doc.id);assert.equal(c.dataset,d.name);
        assert.equal(chunk.offset,j*448);assert.equal(c.offset,chunk.offset);assert.equal(c.tokens,chunk.tokens);
        assert.equal(chunk.tokens,Math.min(512,doc.originalTokens-chunk.offset));end=chunk.offset+chunk.tokens;
      }
      assert.equal(end,doc.originalTokens);
    }
    const metrics=[];
    for(let i=0;i<16;i++) {
      const q=d.queryCases[i],qi=q.caseIndex,c=r.cases[qi],row=d.rows[i];seen.add(qi);
      assert.equal(c.kind,'query');assert.equal(c.sourceId,q.id);assert.equal(c.dataset,d.name);assert.equal(row.queryId,q.id);
      assert(!('text' in q));assert.deepEqual(q.relevance,row.positiveDocumentIds);
      const score=vectors=>docs.map(doc=>Math.max(...doc.chunks.map(chunk=>dot(vectors[qi],vectors[chunk.caseIndex]))));
      const cardScores=score(r.cardVectors),cpuScores=score(r.cpuVectors);
      const order=values=>values.map((s,j)=>({s,j})).sort((a,b)=>b.s-a.s || (docs[a.j].id<docs[b.j].id?-1:docs[a.j].id>docs[b.j].id?1:0)).map(x=>x.j);
      const ranked=order(cardScores),cpuRanked=order(cpuScores);
      assert.deepEqual(row.allRanks.map(x=>x.documentId),ranked.map(j=>docs[j].id));
      assert.deepEqual(row.cpuAllRanks.map(x=>x.documentId),cpuRanked.map(j=>docs[j].id));
      for(let j=0;j<docs.length;j++) {
        close(row.allRanks[j].score,cardScores[ranked[j]]);close(row.cpuAllRanks[j].score,cpuScores[cpuRanked[j]]);
        maxDelta=Math.max(maxDelta,Math.abs(cardScores[j]-cpuScores[j]));
      }
      const relevant=Object.keys(q.relevance),ranks=ranked.flatMap((j,k)=>relevant.includes(docs[j].id)?[k+1]:[]);
      assert.equal(ranks.length,relevant.length);assert(relevant.length>0);
      const gain=g=>2**g-1;
      const dcg=ranked.slice(0,10).reduce((s,j,k)=>s+gain(q.relevance[docs[j].id]??0)/Math.log2(k+2),0);
      const idcg=Object.values(q.relevance).sort((a,b)=>b-a).slice(0,10).reduce((s,g,k)=>s+gain(g)/Math.log2(k+2),0);
      const m={hitAt1:Number(ranks[0]===1),recallAt3:ranks.filter(n=>n<=3).length/relevant.length,
        recallAt10:ranks.filter(n=>n<=10).length/relevant.length,mrr:1/ranks[0],ndcgAt10:dcg/idcg};
      for(const [key,value] of Object.entries(m))close(value,row.metrics[key],1e-10);metrics.push(m);
    }
    for(const key of Object.keys(metrics[0]))close(metrics.reduce((s,m)=>s+m[key],0)/16,d.metrics[key],1e-10);
  }
  assert.equal(seen.size,238);assert(maxDelta<=0.02);close(maxDelta,r.maxScoreDifference);
}
