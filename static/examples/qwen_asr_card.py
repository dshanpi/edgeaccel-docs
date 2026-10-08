"""AXCL inference for the pinned AXERA Qwen3-ASR C64/P448/CTX2047 export.

Audio masking and prompt follow Abandon-ht/sherpa-onnx
9a92ab39b6df9b31a1df39f2c5c57bb08b90e1d2 Qwen3-ASR implementation.
Whisper features use the model's own preprocessor configuration.
"""
import argparse, hashlib, json, math, time
from pathlib import Path

MID='Qwen3-ASR-0.6B-AX650-C64-P448-CTX2047'
REVISION='db1e8640ea9e888aa0ac04f4edd410eee98ef817'
PROVIDER='AXCLRTExecutionProvider'
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',required=True,type=Path);p.add_argument('--audio',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--max-new-tokens',type=int,default=256);p.add_argument('--inspect',action='store_true');a=p.parse_args()
    root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    m=json.loads((root/'download-manifest.json').read_text());assert m['complete'] and m['revision']==REVISION
    rec=dict(modelId=MID,revision=REVISION,provider=PROVIDER,completed=False,runnerSha256=sha(__file__),inputSha256=sha(a.audio),inputPath=str(a.audio),sessions=[],totalCalls=0,filesBefore=[],filesAfter=[],generatedTokenIds=[])
    def save(): (out/'deployment-result.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    for f in m['files']:
        assert (root/f['path']).stat().st_size==f['size'];digest=sha(root/f['path']);assert digest==f['verifiedHashes']['sha256'],f['path'];rec['filesBefore'].append(dict(path=f['path'],sha256=digest))
    import numpy as np
    import ml_dtypes
    import torch,axengine,soundfile as sf
    from scipy.signal import resample_poly
    from transformers import Qwen2Tokenizer,WhisperFeatureExtractor
    import importlib.metadata as md
    torch.set_num_threads(2)
    rec['versions']={n:md.version(n) for n in ['numpy','torch','transformers','tokenizers','ml-dtypes','soundfile','scipy']}
    assert PROVIDER in axengine.get_available_providers()
    def nodes(v):return [dict(name=n.name,shape=list(n.shape),dtype=str(n.dtype)) for n in v]
    class Session:
        def __init__(self,name):
            self.name=name;self.audit=dict(model=name,sha256=sha(root/name),groups={},calls=0,runMilliseconds=[],allFinite=True);rec['sessions'].append(self.audit);save();start=time.perf_counter()
            self.s=axengine.InferenceSession(str(root/name),providers=[PROVIDER]);actual=self.s.get_providers();assert actual in [PROVIDER,[PROVIDER]];self.audit.update(providerActual=actual,loadSeconds=time.perf_counter()-start)
            self.group(0);save()
        def group(self,g):
            ins=self.s.get_inputs(shape_group=g);outs=self.s.get_outputs(shape_group=g);self.audit['groups'][str(g)]=dict(inputs=nodes(ins),outputs=nodes(outs));return ins,outs
        def run(self,feeds,g=0):
            ins,outs=self.group(g);assert set(feeds)=={n.name for n in ins}
            for n in ins:
                v=feeds[n.name];assert tuple(v.shape)==tuple(n.shape),(self.name,g,n.name,v.shape,n.shape);assert v.dtype==np.dtype(n.dtype),(n.name,v.dtype,n.dtype)
            start=time.perf_counter();values=self.s.run(None,feeds,shape_group=g);ms=1000*(time.perf_counter()-start);assert len(values)==len(outs)
            finite=all(np.isfinite(v.astype(np.float32)).all() for v in values)
            entry=dict(index=rec['totalCalls'],model=self.name,shapeGroup=g,runMilliseconds=ms,allFinite=bool(finite),outputs=[])
            for n,v in zip(outs,values):
                assert tuple(v.shape)==tuple(n.shape) and v.dtype==np.dtype(n.dtype);entry['outputs'].append(dict(name=n.name,shape=list(v.shape),dtype=str(v.dtype),sha256=hashlib.sha256(v.tobytes()).hexdigest()))
            if self.name=='qwen3_asr_post.axmodel':
                logits=values[0].astype(np.float32).flatten();entry['greedyTokenId']=int(np.argmax(logits));entry['maxLogit']=float(logits.max())
            with (out/'calls.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(entry)+'\n');f.flush()
            self.audit['calls']+=1;self.audit['runMilliseconds'].append(ms);self.audit['allFinite'] &= bool(finite);rec['totalCalls']+=1
            if rec['totalCalls']%100==0:save()
            assert finite;return values
    start=time.perf_counter()
    try:
        if a.inspect:
            for name in ['conv_frontend.axmodel','encoder.axmodel','qwen3_asr_p64_l0_together.axmodel','qwen3_asr_post.axmodel']:
                session=Session(name)
                if '_l0_' in name:
                    for g in range(1,8):session.group(g)
                save();del session
            rec['inspectionCompleted']=True;return
        audio,sr=sf.read(a.audio,dtype='float32',always_2d=True);rec['audio']=dict(sampleRate=sr,samples=len(audio),channels=audio.shape[1],durationSeconds=len(audio)/sr)
        assert 0<len(audio)<=sr*30,'Use audio between 0 and 30 seconds; no silent truncation'
        wave=audio.mean(axis=1)
        if sr!=16000:
            gcd=math.gcd(sr,16000);wave=resample_poly(wave,16000//gcd,sr//gcd).astype(np.float32)
        features=WhisperFeatureExtractor.from_pretrained(root/'tokenizer',local_files_only=True)
        # Extract features on real samples, then pad feature frames with zeros,
        # matching the compiled frontend's input padding in sherpa-onnx.
        f=features(wave,sampling_rate=16000,padding=False,return_attention_mask=True,return_tensors='np')['input_features'][0].T.copy()
        assert f.shape[1]==128 and 0<f.shape[0]<=3000
        frames=len(f);audio_tokens=13*(frames//100)+(frames%100+7)//8
        rec['preprocessing']=dict(featureFrames=frames,audioTokens=audio_tokens,method='WhisperFeatureExtractor, unpadded audio, zero feature padding',featureSha256=hashlib.sha256(f.tobytes()).hexdigest())
        conv=Session('conv_frontend.axmodel');ins,_=conv.group(0);assert len(ins)==1 and list(ins[0].shape)==[1,3000,128]
        padded=np.zeros(ins[0].shape,dtype=ins[0].dtype);padded[0,:frames]=f;conv_out=conv.run({ins[0].name:padded})[0];del conv
        encoder=Session('encoder.axmodel');ins,_=encoder.group(0);assert list(conv_out.shape)==[1,390,896] and len(ins)==2 and 0<audio_tokens<=390
        mask=np.zeros(ins[1].shape,dtype=ins[1].dtype);mask[0,:audio_tokens]=1
        audio_embed=encoder.run({ins[0].name:conv_out.astype(ins[0].dtype),ins[1].name:mask})[0][0,:audio_tokens].copy();del encoder
        tok=Qwen2Tokenizer.from_pretrained(root/'tokenizer',local_files_only=True)
        before=tok.encode('<|im_start|>system\n<|im_end|>\n<|im_start|>user\n<|audio_start|>',add_special_tokens=False)
        after=tok.encode('<|audio_end|><|im_end|>\n<|im_start|>assistant\n',add_special_tokens=False)
        pad=tok.encode('<|audio_pad|>',add_special_tokens=False);assert len(pad)==1
        ids=before+pad*audio_tokens+after;n=len(ids);assert n<=448
        embed=np.memmap(root/'model.embed_tokens.weight.bfloat16.bin',mode='r',dtype=ml_dtypes.bfloat16,shape=(151936,1024))
        data=embed[ids].copy();data[len(before):len(before)+audio_tokens]=audio_embed.astype(ml_dtypes.bfloat16)
        rec.update(promptTokenIds=ids,promptTokens=n,eosTokenId=tok.eos_token_id,audioEmbeddingSha256=hashlib.sha256(audio_embed.tobytes()).hexdigest());save()
        layers=[Session(f'qwen3_asr_p64_l{i}_together.axmodel') for i in range(28)];post=Session('qwen3_asr_post.axmodel')
        ins,_=layers[0].group(0);spec={n.name:n for n in ins};kvshape=spec['K_cache'].shape;assert list(kvshape)==[1,2047,1024]
        caches=[(np.zeros(kvshape,dtype=spec['K_cache'].dtype),np.zeros(kvshape,dtype=spec['V_cache'].dtype)) for _ in layers]
        for offset in range(0,n,64):
            g=offset//64+1;ins,_=layers[0].group(g);sp={v.name:v for v in ins};count=min(64,n-offset)
            x=np.zeros(sp['input'].shape,dtype=sp['input'].dtype);x[0,:count]=data[offset:offset+count]
            assert list(sp['indices'].shape)==[3,64]
            indices=np.tile(np.arange(offset,offset+64,dtype=sp['indices'].dtype),(3,1))
            mask=np.full(sp['mask'].shape,-65536,dtype=sp['mask'].dtype)
            for i in range(count):mask[0,i,:offset+i+1]=0
            for layer,(k,v) in zip(layers,caches):
                # The first prefill group has one dummy KV row, with no history.
                kin=np.ascontiguousarray(k[:,:offset]) if offset else np.zeros(sp['K_cache'].shape,dtype=sp['K_cache'].dtype)
                vin=np.ascontiguousarray(v[:,:offset]) if offset else np.zeros(sp['V_cache'].shape,dtype=sp['V_cache'].dtype)
                feeds=dict(input=x,indices=indices,mask=mask,K_cache=kin,V_cache=vin)
                ko,vo,x=layer.run(feeds,g);k[:,offset:offset+count]=ko[:,:count];v[:,offset:offset+count]=vo[:,:count]
            print('Prefill',g,flush=True)
        logits=post.run({'input':x[:,count-1:count]})[0];next_token=int(np.argmax(logits.astype(np.float32)))
        position=n;decode_start=time.perf_counter()
        for _ in range(a.max_new_tokens):
            rec['generatedTokenIds'].append(next_token)
            if next_token==tok.eos_token_id:rec['terminatedWithEos']=True;break
            assert position<2047
            x=embed[next_token].reshape(1,1,1024).copy();indices=np.array([[position]],dtype=spec['indices'].dtype)
            mask=np.full(spec['mask'].shape,-65536,dtype=spec['mask'].dtype);mask[...,:position]=0;mask[...,-1]=0
            for layer,(k,v) in zip(layers,caches):
                ko,vo,x=layer.run(dict(input=x,indices=indices,mask=mask,K_cache=k,V_cache=v));k[:,position:position+1]=ko;v[:,position:position+1]=vo
            logits=post.run({'input':x})[0];next_token=int(np.argmax(logits.astype(np.float32)));position+=1
        rec['decodeSeconds']=time.perf_counter()-decode_start;rec['rawText']=tok.decode(rec['generatedTokenIds'],skip_special_tokens=False);rec['text']=tok.decode(rec['generatedTokenIds'],skip_special_tokens=True)
        assert rec.get('terminatedWithEos') and rec['text'].strip(),rec['rawText']
        for f in m['files']:
            digest=sha(root/f['path']);assert digest==f['verifiedHashes']['sha256'];rec['filesAfter'].append(dict(path=f['path'],sha256=digest))
        assert len(rec['sessions'])==31 and all(s['calls']>0 for s in rec['sessions']);rec['completed']=True
        print(rec['rawText'],flush=True)
    finally:
        rec['pipelineSeconds']=time.perf_counter()-start;rec['npuCallTotalMilliseconds']=sum(sum(s['runMilliseconds']) for s in rec['sessions']);save()
if __name__=='__main__':main()
