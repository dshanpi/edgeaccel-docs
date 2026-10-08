"""Run pinned official MOSS ASR with explicit AXCL and auditable outputs."""
import argparse, hashlib, importlib.util, json, sys, time
from pathlib import Path

REVISION = 'c627e9bad59af4074d95c4bc24a87483141d5cc7'
PROVIDER = 'AXCLRTExecutionProvider'

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--audio', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--kv-transfer', choices=['full','incremental'], default='full')
    a = p.parse_args()
    root, out, audio = a.model_dir.resolve(), a.output.resolve(), a.audio.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((root/'download-manifest.json').read_text())
    assert manifest['complete'] and manifest['revision'] == REVISION
    files = {f['path']:f for f in manifest['files']}
    rec = dict(modelId='MOSS-Transcribe-Diarize-0.9B', revision=REVISION, provider=PROVIDER,
               completed=False, runnerSha256=sha(__file__), inputSha256=sha(audio),
               inputPath=str(audio), kvTransfer=a.kv_transfer, sessions=[], totalCalls=0, filesBefore=[], filesAfter=[], postGreedyTokenIds=[])
    def save():
        (out/'deployment-result.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    for name,f in files.items():
        path=root/name
        assert path.is_file() and path.stat().st_size == f['size']
        digest=sha(path)
        assert digest == f['verifiedHashes']['sha256'], name
        rec['filesBefore'].append(dict(path=name,sha256=digest))
    save()
    import axengine
    import numpy as np
    import torch
    import importlib.metadata as md
    torch.set_num_threads(2)
    np.random.seed(0)
    assert PROVIDER in axengine.get_available_providers()
    rec['versions']={n:md.version(n) for n in ['numpy','torch','transformers','tokenizers','ml-dtypes','soundfile','scipy']}
    OriginalSession=axengine.InferenceSession
    from axengine._axclrt import axclrt_cffi as ffi, axclrt_lib as lib
    def checked(code,label):
        if code:raise RuntimeError(f'{label}: AXCL error {code:#x}')
    def incremental_decode(session, feeds):
        """Keep KV buffers on device; upload only the row just changed by InferManager.

        The first decode uploads the complete official host cache. Later calls in
        this single-request session overwrite exactly the previous token's row.
        Prefill always uses the original path and resets this incremental state.
        """
        native=session._sess
        checked(lib.axclrtSetCurrentContext(native._thread_context[0]),'set context')
        step=int(feeds['indices'].reshape(-1)[0])
        previous=getattr(session,'last_decode_step',None)
        assert 0<=step<10240
        delta=previous is not None and step==previous+1
        ptr=ffi.new('void **');size=ffi.new('uint64_t *');total=0
        for i,node in enumerate(session.get_inputs(shape_group=0)):
            value=np.ascontiguousarray(feeds[node.name])
            checked(lib.axclrtEngineGetInputBufferByIndex(native._io[0],i,ptr,size),'input buffer')
            offset=0;count=value.nbytes
            if node.name in ['K_cache','V_cache']:
                assert value.shape==(1,10240,1024) and value.dtype.name=='bfloat16'
                if delta:
                    offset=previous*1024*2;count=1024*2
            assert offset+count<=size[0]
            checked(lib.axclrtMemcpy(ffi.cast('char *',ptr[0])+offset,ffi.cast('char *',value.ctypes.data)+offset,count,lib.AXCL_MEMCPY_HOST_TO_DEVICE),'H2D')
            total+=count
        checked(lib.axclrtEngineExecute(native._model_id[0],native._context_id[0],0,native._io[0]),'execute')
        values=[]
        for i,node in enumerate(session.get_outputs(shape_group=0)):
            value=np.empty(node.shape,dtype=node.dtype)
            checked(lib.axclrtEngineGetOutputBufferByIndex(native._io[0],i,ptr,size),'output buffer')
            assert value.nbytes<=size[0]
            checked(lib.axclrtMemcpy(ffi.cast('void *',value.ctypes.data),ptr[0],value.nbytes,lib.AXCL_MEMCPY_DEVICE_TO_HOST),'D2H')
            values.append(value)
        session.last_decode_step=step
        return values,dict(step=step,incremental=delta,hostToDeviceBytes=total)
    def nodes(items):
        return [dict(name=n.name,shape=list(n.shape),dtype=str(n.dtype)) for n in items]
    class Session(OriginalSession):
        def __init__(self,path,*args,**kwargs):
            name=Path(path).resolve().relative_to(root).as_posix()
            assert name in files and not args and not kwargs
            self.audit=dict(model=name,sha256=files[name]['verifiedHashes']['sha256'],groups={},calls=0,runMilliseconds=0,allFinite=True)
            rec['sessions'].append(self.audit);save()
            started=time.perf_counter()
            super().__init__(path,providers=[PROVIDER])
            actual=self.get_providers()
            assert actual in [PROVIDER,[PROVIDER]],actual
            self.audit.update(providerActual=actual,loadSeconds=time.perf_counter()-started)
            save()
        def run(self,names,feeds,shape_group=0):
            group=str(shape_group)
            if group not in self.audit['groups']:
                self.audit['groups'][group]=dict(inputs=nodes(self.get_inputs(shape_group=shape_group)),outputs=nodes(self.get_outputs(shape_group=shape_group)))
                save()
            ins=self.get_inputs(shape_group=shape_group)
            assert set(feeds)=={n.name for n in ins}
            # The official first prefill uses a dummy KV tensor for zero-size bindings.
            for n in ins:
                value=feeds[n.name]
                assert value.dtype==np.dtype(n.dtype),(n.name,value.dtype,n.dtype)
                if np.prod(n.shape)>0:
                    assert tuple(value.shape)==tuple(n.shape),(n.name,value.shape,n.shape)
            started=time.perf_counter()
            transfer=None
            if a.kv_transfer=='incremental' and self.audit['model'].startswith('qwen3_p256_l') and shape_group==0:
                assert names is None
                values,transfer=incremental_decode(self,feeds)
            else:
                if shape_group!=0:self.last_decode_step=None
                values=super().run(names,feeds,shape_group=shape_group)
            ms=1000*(time.perf_counter()-started)
            outs=self.get_outputs(shape_group=shape_group)
            assert len(values)==len(outs)
            finite=all(np.isfinite(v.astype(np.float32)).all() for v in values)
            entry=dict(index=rec['totalCalls'],model=self.audit['model'],shapeGroup=shape_group,runMilliseconds=ms,allFinite=bool(finite),outputs=[])
            if transfer:entry['kvTransfer']=transfer
            for n,v in zip(outs,values):
                assert tuple(v.shape)==tuple(n.shape) and v.dtype==np.dtype(n.dtype)
                entry['outputs'].append(dict(name=n.name,shape=list(v.shape),dtype=str(v.dtype),sha256=hashlib.sha256(v.tobytes()).hexdigest()))
            if self.audit['model']=='qwen3_post.axmodel':
                logits=values[0].astype(np.float32).flatten()
                # Mirror the official top_k=1 selection, including ties. argmax
                # chooses the first maximum and need not match argpartition.
                chosen=int(np.argpartition(logits,-1)[-1])
                maxima=np.flatnonzero(logits==logits.max())
                assert chosen in maxima
                entry.update(greedyTokenId=chosen,argmaxFirstTokenId=int(np.argmax(logits)),maxLogit=float(logits[chosen]),maxLogitTokenCount=int(maxima.size),maxLogitTokenIds=([int(x) for x in maxima] if maxima.size<=16 else None))
                rec['postGreedyTokenIds'].append(chosen)
            with (out/'calls.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps(entry)+'\n');f.flush()
            self.audit['calls']+=1;self.audit['runMilliseconds']+=ms;self.audit['allFinite'] &= bool(finite);rec['totalCalls']+=1
            if rec['totalCalls']%100==0:save()
            assert finite,'Nonfinite output'
            return values
    axengine.InferenceSession=Session
    sys.path.insert(0,str(root))
    spec=importlib.util.spec_from_file_location('moss_official',root/'infer_moss_axengine.py')
    official=importlib.util.module_from_spec(spec);sys.modules[spec.name]=official;spec.loader.exec_module(official)
    sys.argv=['infer_moss_axengine.py',str(audio),'--model-dir',str(root),'--save-response',str(out/'response.json'),'--stream']
    started=time.perf_counter()
    try:
        official.main()
        rec['pipelineSeconds']=time.perf_counter()-started
        response=json.loads((out/'response.json').read_text())
        assert response['generated_token_ids'] and response['text'].strip()
        from tokenizers import Tokenizer
        rec['eosTokenId']=Tokenizer.from_file(str(root/'tokenizer.json')).token_to_id('<|im_end|>')
        rec['terminatedWithEos']=rec['postGreedyTokenIds'][-1]==rec['eosTokenId']
        assert rec['terminatedWithEos'], 'Decode did not reach EOS'
        assert rec['postGreedyTokenIds'][:-1]==response['generated_token_ids'], 'Greedy tokens mismatch'
        rec['responseSha256']=sha(out/'response.json')
        for name in files:
            digest=sha(root/name);assert digest==files[name]['verifiedHashes']['sha256']
            rec['filesAfter'].append(dict(path=name,sha256=digest))
        assert len(rec['sessions'])==30 and all(s['calls']>0 for s in rec['sessions'])
        rec['completed']=True
    finally:
        rec['npuCallTotalMilliseconds']=sum(s['runMilliseconds'] for s in rec['sessions'])
        save()
    print(json.dumps({'completed':rec['completed'],'calls':rec['totalCalls'],'pipelineSeconds':rec['pipelineSeconds']}),flush=True)

if __name__=='__main__':main()
