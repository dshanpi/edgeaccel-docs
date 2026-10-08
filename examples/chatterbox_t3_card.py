"""AXCL T3 text-to-speech-token runner; audio decoding is a separate stage."""
import argparse,hashlib,json,time
from pathlib import Path

MID='chatterbox-p192-ctx384-ax650';REVISION='f37f2a4bd7331fbf511e089a6741f5685d58c2c0';PROVIDER='AXCLRTExecutionProvider'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        offset=0
        for block in iter(lambda:f.read(8*1024*1024),b''):
            h.update(block)
            if hasattr(__import__('os'),'posix_fadvise'):
                import os
                os.posix_fadvise(f.fileno(),offset,len(block),os.POSIX_FADV_DONTNEED)
            offset+=len(block)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--max-new-tokens',type=int,default=180);a=p.parse_args()
    root=a.model_dir;out=a.output;out.mkdir(parents=True,exist_ok=False)
    manifest_path=root/'download-manifest.json'
    if not manifest_path.exists():manifest_path=root/'.validation-download.json'
    manifest=json.loads(manifest_path.read_text());assert manifest['complete'] and manifest['revision']==REVISION
    prep=json.loads((a.prepared/'preparation.json').read_text());assert prep['completed'] and len(prep['embeddingChecks'])==5
    rec=dict(modelId=MID,revision=REVISION,provider=PROVIDER,completed=False,scope='text-to-speech tokens; waveform stage separate',runnerSha256=sha(__file__),preparationSha256=sha(a.prepared/'preparation.json'),text=prep['text'],language=prep['language'],sessions=[],totalCalls=0,filesBefore=[],filesAfter=[],generatedTokenIds=[],cfgWeight=0.5,alignmentAnalyzer=False,sampling=dict(seed=42,temperature=0.8,minP=0.05,topP=1.0,repetitionPenalty=1.2),maxNewTokens=a.max_new_tokens)
    def save():(out/'deployment-result.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    for f in manifest['files']:
        d=sha(root/f['path']);assert d==f['verifiedHashes']['sha256'];rec['filesBefore'].append(dict(path=f['path'],sha256=d))
    import numpy as np,ml_dtypes,axengine,torch
    from transformers.generation.logits_process import RepetitionPenaltyLogitsProcessor,MinPLogitsWarper,TopPLogitsWarper
    bf=ml_dtypes.bfloat16
    for f in prep['preparedFiles']:
        if f['path']=='input-embeddings.npy':assert sha(a.prepared/f['path'])==f['sha256']
    data=np.load(a.prepared/'input-embeddings.npy',allow_pickle=False);n=data.shape[1];assert data.shape==(2,n,1024) and n<=192 and prep["cfgWeight"]==0.5
    rec['promptPositions']=n;assert a.max_new_tokens>=0 and n+a.max_new_tokens<384
    def nodes(ns):return [dict(name=v.name,shape=list(v.shape),dtype=str(v.dtype)) for v in ns]
    class Session:
        def __init__(self,name):
            self.name=name;self.row=dict(model=name,sha256=sha(root/name),groups={},calls=0,allFinite=True,runMilliseconds=[]);rec['sessions'].append(self.row);save();t=time.perf_counter()
            self.s=axengine.InferenceSession(str(root/name),providers=[PROVIDER]);assert self.s.get_providers() in (PROVIDER,[PROVIDER]);self.row['loadSeconds']=time.perf_counter()-t;self.group(0);save()
        def group(self,g):
            ins=self.s.get_inputs(shape_group=g);outs=self.s.get_outputs(shape_group=g);self.row['groups'][str(g)]=dict(inputs=nodes(ins),outputs=nodes(outs));return {v.name:v for v in ins},outs
        def run(self,feed,g=0):
            ins,outs=self.group(g);assert set(feed)==set(ins)
            for name,v in feed.items():assert list(v.shape)==list(ins[name].shape) and v.dtype==np.dtype(ins[name].dtype),(self.name,name,v.shape,v.dtype)
            t=time.perf_counter();values=self.s.run(None,{k:np.ascontiguousarray(v) for k,v in feed.items()},shape_group=g);ms=1000*(time.perf_counter()-t);assert len(values)==len(outs)
            finite=all(np.isfinite(v.astype(np.float32)).all() for v in values)
            row=dict(index=rec['totalCalls'],model=self.name,group=g,milliseconds=ms,finite=bool(finite),outputs=[])
            for spec,v in zip(outs,values):
                assert list(v.shape)==list(spec.shape) and v.dtype==np.dtype(spec.dtype)
                row['outputs'].append(dict(name=spec.name,shape=list(v.shape),dtype=str(v.dtype),sha256=hashlib.sha256(v.tobytes()).hexdigest()))
            with (out/'calls.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            rec['totalCalls']+=1;self.row['calls']+=1;self.row['runMilliseconds'].append(ms);self.row['allFinite'] &= bool(finite);assert finite
            return {s.name:v for s,v in zip(outs,values)}
    t=time.perf_counter()
    try:
        layers=[Session(f'llama_p64_l{i}_together.axmodel') for i in range(30)];post=Session('llama_post.axmodel');head=Session('t3_speech_head.axmodel')
        specs,_=layers[0].group(0);assert list(specs['K_cache'].shape)==[1,383,1024]
        branches=[[(np.zeros((1,383,1024),bf),np.zeros((1,383,1024),bf)) for _ in layers] for branch in range(2)]
        hidden=[]
        for branch,caches in enumerate(branches):
            for offset in range(0,n,64):
                group=offset//64+1;sp,_=layers[0].group(group);count=min(64,n-offset)
                x=np.zeros((1,64,1024),bf);x[0,:count]=data[branch,offset:offset+count].astype(bf)
                indices=np.arange(offset,offset+64,dtype=np.uint32)[None];mask=np.full(sp['mask'].shape,-65536,dtype=bf)
                for j in range(count):mask[0,j,:offset+j+1]=0
                for index,(layer,(k,v)) in enumerate(zip(layers,caches)):
                    kin=k[:,:offset].copy() if offset else np.zeros(sp['K_cache'].shape,bf);vin=v[:,:offset].copy() if offset else np.zeros(sp['V_cache'].shape,bf)
                    r=layer.run(dict(input=x,indices=indices,mask=mask,K_cache=kin,V_cache=vin),group)
                    k[:,offset:offset+count]=r['K_cache_out'][:,:count];v[:,offset:offset+count]=r['V_cache_out'][:,:count];x=r['output']
                    if index in (0,29):np.save(out/f'card-branch-{branch}-layer-{index}-chunk-{offset}.npy',x[:,:count].astype(np.float32))
            hidden.append(x[:,count-1:count].copy())
        def project(x,first=False):
            p=post.run({'input':x});norm=p['output_norm'].astype(np.float32).reshape(1,1024)
            # The original speech head is bias-free linear. Its compiled input
            # clips large activations; homogeneous scaling avoids saturation.
            # Zero/basis/scaled real-state probes are archived before adaptation.
            scale=float(2**max(0,int(np.ceil(np.log2(max(float(np.abs(norm).max())/3.0,1.0))))))
            logits=head.run({'hidden_state':norm/scale})['speech_logits']*scale
            rec.setdefault('headInputScales',[]).append(scale)
            if first:
                np.save(out/'card-norm.npy',norm);np.save(out/'card-text-logits.npy',p['output'].astype(np.float32));np.save(out/'card-speech-logits.npy',logits)
            return logits.reshape(-1)
        parts=[project(x,branch==0) for branch,x in enumerate(hidden)];logits=parts[0]+0.5*(parts[0]-parts[1]);np.save(out/'card-cfg-logits.npy',logits);rec['firstGreedyToken']=int(np.argmax(logits));save();print('First pass',rec['firstGreedyToken'],flush=True)
        def embedding(name,shape):
            raw=(root/name).read_bytes();expected=next(f['verifiedHashes']['sha256'] for f in manifest['files'] if f['path']==name)
            assert hashlib.sha256(raw).hexdigest()==expected
            rec.setdefault('embeddingReadChecks',[]).append(dict(path=name,sha256=expected,bytes=len(raw)))
            return np.frombuffer(raw,dtype=bf).reshape(shape).copy()
        speech=embedding('speech_embedding.float16.bin',(8194,1024));position_emb=embedding('speech_position_embedding.float16.bin',(4100,1024));history=[6561];torch.set_num_threads(2);torch.manual_seed(42)
        repeat=RepetitionPenaltyLogitsProcessor(1.2);minp=MinPLogitsWarper(0.05);topp=TopPLogitsWarper(1.0);rec["sampling"]["implementation"]="torch.multinomial + official Transformers logits processors";rec["sampling"]["torchVersion"]=torch.__version__
        decode=time.perf_counter()
        for step in range(a.max_new_tokens):
            ids=torch.tensor([history],dtype=torch.long);scores=torch.from_numpy(logits.astype(np.float32).copy()).reshape(1,-1);scores=repeat(ids,scores)/0.8;scores=topp(ids,minp(ids,scores));token=int(torch.multinomial(torch.softmax(scores,dim=-1),num_samples=1).item());rec['generatedTokenIds'].append(token);history.append(token)
            save();print('Token',step,token,flush=True)
            if token==6562:rec['terminatedWithEos']=True;break
            assert 0<=token<6561,('non-acoustic token',token)
            if step+1==a.max_new_tokens:break
            position=n+step;x=(speech[token].astype(np.float32)+position_emb[step+1].astype(np.float32)).astype(bf).reshape(1,1,1024)
            mask=np.full((1,1,384),-65536,bf);mask[...,:position]=0;mask[...,-1]=0;indices=np.array([[position]],np.uint32)
            decoded=[]
            for caches in branches:
                branch_x=x.copy()
                for layer,(k,v) in zip(layers,caches):
                    r=layer.run(dict(input=branch_x,indices=indices,mask=mask,K_cache=k,V_cache=v));k[:,position:position+1]=r['K_cache_out'];v[:,position:position+1]=r['V_cache_out'];branch_x=r['output']
                decoded.append(project(branch_x))
            logits=decoded[0]+0.5*(decoded[0]-decoded[1])
        rec['decodeSeconds']=time.perf_counter()-decode
        for f in manifest['files']:
            d=sha(root/f['path']);assert d==f['verifiedHashes']['sha256'];rec['filesAfter'].append(dict(path=f['path'],sha256=d))
        if a.max_new_tokens:
            tokens=rec['generatedTokenIds'];assert rec.get('terminatedWithEos') and len(tokens)>1
            np.save(out/'speech-tokens.npy',np.array(tokens[:-1],np.int32)[None]);rec['speechTokensSha256']=sha(out/'speech-tokens.npy');rec['completed']=True
        else:rec['firstPassCompleted']=True
    finally:
        rec['elapsedSeconds']=time.perf_counter()-t;rec['npuCallMilliseconds']=sum(sum(s['runMilliseconds']) for s in rec['sessions']);save()
if __name__=='__main__':main()
