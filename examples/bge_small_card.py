"""Run the official BGE-small batch-1/batch-2 AXMODEL files and their CPU ONNX references."""
import argparse,datetime,gc,hashlib,json,time
from pathlib import Path
import axengine
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

MID='bge-small-en-v1.5'
REVISION='7a15f5aa8ecb76e1f87c4e8e6c9c73f87d33f7b4'
TOKENIZER_REVISION='5c38ec7c405ec4b44b94cc5a9bb96e735b38267a'
PROVIDER='AXCLRTExecutionProvider'
TEXTS=['I really love math','I pretty like mathematics',
       'How can I check whether my accelerator card is detected?',
       'Run axcl-smi to list detected accelerator cards and check their device status.',
       'How do I download a model through a proxy?',
       'Set http_proxy and https_proxy to the proxy address before downloading model files.',
       'Tomatoes need regular watering and sunlight.',
       'The pianist played a quiet melody at the concert.']

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir',type=Path,required=True)
    p.add_argument('--tokenizer-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    assert PROVIDER in axengine.get_available_providers()
    tokenizer=AutoTokenizer.from_pretrained(a.tokenizer_dir,local_files_only=True)
    encoded=tokenizer(TEXTS,padding='max_length',max_length=512,truncation=False,return_tensors='np')
    ids=encoded['input_ids'];assert ids.shape==(8,512)
    tokenizer_hashes={p.name:sha(p) for p in a.tokenizer_dir.iterdir() if p.is_file() and not p.name.startswith('.')}
    r={'modelId':MID,'revision':REVISION,'provider':PROVIDER,'completed':False,'sessions':[],'cpuSessions':[],
       'texts':TEXTS,'inputTokenIds':ids.tolist(),'tokenizerRevision':TOKENIZER_REVISION,'tokenizerFiles':tokenizer_hashes,
       'variants':[],'pooling':'First token (CLS), then L2 normalization; no query instruction prefix.',
       'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'deployment-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    arrays={}
    try:
        for batch in [1,2]:
            suffix='' if batch==1 else '_b2'
            results={}
            for backend in ['axcl','onnx']:
                rel=f'model/bge-small-en-v1.5{suffix}'+('_u16_npu3.axmodel' if backend=='axcl' else '.onnx')
                t=time.perf_counter()
                if backend=='axcl':
                    session=axengine.InferenceSession(str(root/rel),providers=[PROVIDER]);dtype=np.int32
                    assert session.get_providers() in (PROVIDER,[PROVIDER])
                else:
                    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
                    session=ort.InferenceSession(str(root/rel),sess_options=options,providers=['CPUExecutionProvider'])
                    dtype={'tensor(int64)':np.int64,'tensor(int32)':np.int32}[session.get_inputs()[0].type]
                    assert session.get_providers()==['CPUExecutionProvider']
                row={'model':rel,'provider':PROVIDER if backend=='axcl' else 'CPUExecutionProvider',
                     'weightSha256':sha(root/rel),'loadSeconds':time.perf_counter()-t,
                     'runMilliseconds':[],'allFinite':True,'outputChecks':[]}
                r['sessions' if backend=='axcl' else 'cpuSessions'].append(row)
                vectors=[]
                for i in range(0,len(TEXTS),batch):
                    feed={'input_ids':ids[i:i+batch].astype(dtype)}
                    t=time.perf_counter();outputs=session.run(None,feed);row['runMilliseconds'].append((time.perf_counter()-t)*1000)
                    assert len(outputs)==1 and outputs[0].shape==(batch,512,384)
                    finite=bool(np.isfinite(outputs[0]).all());row['allFinite'] &= finite;assert finite
                    row['outputChecks'].append({'shape':list(outputs[0].shape),'dtype':str(outputs[0].dtype),
                                               'sha256':hashlib.sha256(outputs[0].tobytes()).hexdigest()})
                    cls=outputs[0][:,0].astype(np.float32,copy=True)
                    norm=np.linalg.norm(cls,axis=1,keepdims=True);assert (norm>0).all()
                    vectors.append(cls/norm)
                results[backend]=np.concatenate(vectors);arrays[f'{backend}_b{batch}']=results[backend]
                del session;gc.collect();save()
            npu,cpu=results['axcl'],results['onnx']
            scores=npu@npu.T;reference=cpu@cpu.T
            candidates=[3,5,6,7];retrieval=[]
            for query,expected in [(2,3),(4,5)]:
                order=sorted(candidates,key=lambda i:float(scores[query,i]),reverse=True)
                reforder=sorted(candidates,key=lambda i:float(reference[query,i]),reverse=True)
                retrieval.append({'queryIndex':query,'query':TEXTS[query],'expectedIndex':expected,'top1MatchesExpected':order[0]==expected,
                                  'referenceOrder':reforder,'order':order,
                                  'candidates':[{'textIndex':i,'text':TEXTS[i],'cosine':float(scores[query,i]),
                                                 'referenceCosine':float(reference[query,i])} for i in order]})
            variant={'batch':batch,'sameMeaningPair':{'texts':TEXTS[:2],'cosine':float(scores[0,1]),'referenceCosine':float(reference[0,1])},
                     'retrieval':retrieval,'referenceComparison':{'normalizedVectorCosines':np.sum(npu*cpu,axis=1).tolist(),
                     'normalizedVectorMaxAbsoluteError':float(np.max(np.abs(npu-cpu))),
                     'similarityMatrixMaxAbsoluteError':float(np.max(np.abs(scores-reference)))}}
            r['variants'].append(variant);save();print(json.dumps(variant,ensure_ascii=False),flush=True)
        r['batchComparison']={'vectorCosines':np.sum(arrays['axcl_b1']*arrays['axcl_b2'],axis=1).tolist(),
                              'maxAbsoluteError':float(np.max(np.abs(arrays['axcl_b1']-arrays['axcl_b2'])))}
        np.savez_compressed(out/'embeddings.npz',input_ids=ids,**arrays)
        r['embeddingFileSha256']=sha(out/'embeddings.npz');r['completed']=True
    except BaseException as e:r['error']=repr(e);raise
    finally:r['finishedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()

if __name__=='__main__':main()
