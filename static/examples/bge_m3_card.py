"""BGE-M3 dense, sparse and ColBERT retrieval using the fixed official Python implementation on AXCL."""
import argparse,datetime,gc,hashlib,importlib.util,json,time
from pathlib import Path
import axengine
import numpy as np

MID='bge-m3';REVISION='46734ad9f85c79a243364ba51f5ffa64a628079a'
SOURCE_SHA='1c895826be2fb2185a5e942618172e96e9bd093f3b9f1ba50882324c640c2c77'
TOKENIZER_REVISION='5617a9f61b028005a4858fdac845db406aefb181'
PROVIDER='AXCLRTExecutionProvider'
TEXTS=['What is BGE M3?','Definition of BM25',
       'BGE M3 is an embedding model supporting dense retrieval, lexical matching and multi-vector interaction.',
       'BM25 is a bag-of-words retrieval function that ranks a set of documents based on the query terms appearing in each document.',
       '如何确认算力卡被主机识别？','怎样通过代理下载模型？',
       '运行 axcl-smi，检查算力卡是否被枚举以及设备状态。',
       '下载模型前设置 http_proxy 和 https_proxy，填写可用的代理地址。',
       '番茄需要定期浇水和充足的阳光。','The pianist played a quiet melody at the concert.']

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--tokenizer-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    source=root/'python/axmodel_infer.py';assert sha(source)==SOURCE_SHA
    assert PROVIDER in axengine.get_available_providers()
    spec=importlib.util.spec_from_file_location('bge_m3_official',source)
    official=importlib.util.module_from_spec(spec);spec.loader.exec_module(official)
    r={'modelId':MID,'revision':REVISION,'provider':PROVIDER,'completed':False,'sessions':[],
       'texts':TEXTS,'sourceSha256':SOURCE_SHA,'tokenizerRevision':TOKENIZER_REVISION,
       'tokenizerFiles':{p.name:sha(p) for p in a.tokenizer_dir.iterdir() if p.is_file() and not p.name.startswith('.')},
       'inputTokenIds':[],'results':[],'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'deployment-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    factory=axengine.InferenceSession
    class Measured:
        def __init__(self,path,providers=None):
            assert providers==['AxEngineExecutionProvider']
            t=time.perf_counter();self.session=factory(path,providers=[PROVIDER])
            assert self.session.get_providers() in (PROVIDER,[PROVIDER])
            self.row={'model':Path(path).relative_to(root).as_posix(),'provider':PROVIDER,'weightSha256':sha(path),
                      'loadSeconds':time.perf_counter()-t,'runMilliseconds':[],'allFinite':True,'outputs':[]}
            r['sessions'].append(self.row)
        def run(self,names,feed):
            assert feed['input_ids'].shape==(1,512) and feed['input_ids'].dtype==np.int32
            r['inputTokenIds'].append(feed['input_ids'][0].tolist())
            t=time.perf_counter();values=self.session.run(names,feed);self.row['runMilliseconds'].append((time.perf_counter()-t)*1000)
            assert [list(v.shape) for v in values]==[[1,1024],[1,512,1],[1,511,1024]]
            finite=bool(all(np.isfinite(v).all() for v in values));self.row['allFinite'] &= finite;assert finite
            self.row['outputs'].append([{'shape':list(v.shape),'dtype':str(v.dtype),'sha256':hashlib.sha256(v.tobytes()).hexdigest()} for v in values])
            return values
    try:
        official.axe.InferenceSession=Measured
        model=official.BGEM3Model(str(a.tokenizer_dir),root/'model/bge-m3_u16_npu3.axmodel')
        for text in TEXTS:assert len(model.tokenizer.encode(text))<=512,'Split long input before inference'
        t=time.perf_counter();features=model.encode(TEXTS);r['encodeSeconds']=time.perf_counter()-t
        r['lexicalWeights']=features['lexical_weights'];r['denseNorms']=np.linalg.norm(features['dense_vecs'],axis=1).tolist()
        arrays={'dense':features['dense_vecs'],'input_ids':np.array(r['inputTokenIds'])}
        arrays.update({f'colbert_{i}':v for i,v in enumerate(features['colbert_vecs'])})
        for query,expected in [(0,2),(1,3),(4,6),(5,7)]:
            candidates=[]
            for passage in [2,3,6,7,8,9]:
                dense=float(features['dense_vecs'][query]@features['dense_vecs'][passage])
                sparse=float(model.lexical_matching_score(features['lexical_weights'][query],features['lexical_weights'][passage]))
                colbert=float(model.colbert_score(features['colbert_vecs'][query],features['colbert_vecs'][passage]))
                candidates.append({'index':passage,'text':TEXTS[passage],'dense':dense,'sparse':sparse,'colbert':colbert,
                                   'fused':0.4*dense+0.2*sparse+0.4*colbert})
            candidates.sort(key=lambda c:c['fused'],reverse=True)
            r['results'].append({'queryIndex':query,'query':TEXTS[query],'expectedIndex':expected,
                                 'candidates':candidates,'top1MatchesExpected':candidates[0]['index']==expected})
        r['repeatChecks']=[]
        for i in [0,4]:
            repeated=model.encode(TEXTS[i]);matched=bool(np.array_equal(features['dense_vecs'][i],repeated['dense_vecs'][0]) and
                np.array_equal(features['colbert_vecs'][i],repeated['colbert_vecs'][0]) and features['lexical_weights'][i]==repeated['lexical_weights'][0])
            r['repeatChecks'].append({'textIndex':i,'threeRepresentationsEqual':matched});assert matched
        np.savez_compressed(out/'embeddings.npz',**arrays);r['embeddingFileSha256']=sha(out/'embeddings.npz')
        r['completed']=True;print(json.dumps(r['results'],ensure_ascii=False),flush=True)
    except BaseException as e:r['error']=repr(e);raise
    finally:
        official.axe.InferenceSession=factory
        r['finishedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();gc.collect()

if __name__=='__main__':main()
