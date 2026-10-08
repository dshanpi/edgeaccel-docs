"""Run the pinned official meeting transcription pipeline with AXCL evidence."""
import argparse,hashlib,importlib.metadata,json,os,re,sys,time
from pathlib import Path
MID='3D-Speaker-MT.Axera';REV='3592794622a5627aca47c81fdc2569e632ffc910';PROVIDER='AXCLRTExecutionProvider'
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--audio',default='wav/vad_example.wav');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);audio=(root/a.audio).resolve();assert audio.is_relative_to(root)
    manifest=json.loads((root/'.validation-download.json').read_text());assert manifest['complete'] and manifest['revision']==REV
    rec=dict(modelId=MID,revision=REV,provider=PROVIDER,completed=False,scope='official offline VAD, speaker clustering and ASR; web and LLM summary not tested',runnerSha256=sha(__file__),inputPath=a.audio,inputSha256=sha(audio),filesBefore=[],filesAfter=[],sessions=[],totalCalls=0,stages={})
    def convert(value):
        if hasattr(value,'tolist'):return value.tolist()
        raise TypeError(type(value).__name__)
    def save():(out/'deployment-result.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2,default=convert)+'\n',encoding='utf-8')
    save()
    for f in manifest['files']:
        d=sha(root/f['path']);assert d==f['verifiedHashes']['sha256'];rec['filesBefore'].append(dict(path=f['path'],sha256=d))
    import numpy as np,axengine,torch,soundfile as sf
    torch.set_num_threads(2);np.random.seed(42)
    rec['versions']={name:importlib.metadata.version(name) for name in ['numpy','scipy','scikit-learn','fastcluster','kaldi-native-fbank','soundfile','torch','sentencepiece','jieba']}
    native=axengine.InferenceSession
    class Session:
        def __init__(self,path,*args,**kwargs):
            name=Path(path).resolve().relative_to(root).as_posix();kwargs['providers']=[PROVIDER];t=time.perf_counter();self.s=native(path,*args,**kwargs);assert self.s.get_providers() in (PROVIDER,[PROVIDER]);self.name=name
            self.row=dict(model=name,sha256=sha(path),provider=PROVIDER,loadSeconds=time.perf_counter()-t,calls=0,allFinite=True,runMilliseconds=[],groups={});rec['sessions'].append(self.row);save()
        def __getattr__(self,name):return getattr(self.s,name)
        def run(self,names,feed,**kwargs):
            group=kwargs.get('shape_group',0);ins=self.s.get_inputs(shape_group=group);outs=self.s.get_outputs(shape_group=group);chosen=[next(v for v in outs if v.name==n) for n in names] if names else outs
            self.row['groups'][str(group)]=dict(inputs=[dict(name=n.name,shape=list(n.shape),dtype=str(n.dtype)) for n in ins],outputs=[dict(name=n.name,shape=list(n.shape),dtype=str(n.dtype)) for n in outs])
            assert set(feed)=={n.name for n in ins}
            for n in ins:
                v=feed[n.name];assert list(v.shape)==list(n.shape) and v.dtype==np.dtype(n.dtype),(self.name,n.name,v.shape,v.dtype,n.shape,n.dtype);assert np.isfinite(v.astype(np.float32)).all()
            t=time.perf_counter();values=self.s.run(names,feed,**kwargs);ms=1000*(time.perf_counter()-t);assert len(values)==len(chosen)
            info=[]
            for n,v in zip(chosen,values):
                assert list(v.shape)==list(n.shape) and v.dtype==np.dtype(n.dtype);assert np.isfinite(v.astype(np.float32)).all();info.append(dict(name=n.name,shape=list(v.shape),dtype=str(v.dtype),sha256=hashlib.sha256(v.tobytes()).hexdigest()))
            if self.row['calls']==0:np.savez_compressed(out/(Path(self.name).stem+'-first-call.npz'),**{'input_'+k:v for k,v in feed.items()},**{'output_'+n.name:v for n,v in zip(chosen,values)})
            with (out/'calls.jsonl').open('a') as f:f.write(json.dumps(dict(index=rec['totalCalls'],model=self.name,milliseconds=ms,outputs=info,allFinite=True))+'\n')
            self.row['calls']+=1;self.row['runMilliseconds'].append(ms);rec['totalCalls']+=1
            if rec['totalCalls']%20==0:save()
            return values
    axengine.InferenceSession=Session;sys.path.insert(0,str(root));os.environ['AX_MODEL_DIR']=str(root/'ax_meeting/ax_model')
    start=time.perf_counter()
    try:
        from ax_meeting.diar_asr_cli import diar_asr,load_audio
        from ax_meeting.model_bundle import ModelBundle
        original_audio,sr=sf.read(audio,dtype='float32',always_2d=True);speech=load_audio(str(audio),16000);rec['audio']=dict(originalSamples=len(original_audio),originalSampleRate=sr,originalChannels=original_audio.shape[1],processedSamples=len(speech),sampleRate=16000,durationSeconds=len(speech)/16000)
        bundle=ModelBundle();bundle.ensure_loaded()
        vad=bundle.vad_infer;speaker=bundle.speaker_infer;asr=bundle.asr_infer
        def vad_traced(*args,**kw):
            result=vad(*args,**kw);rec['stages'].setdefault('vad',[]).append(result);save();return result
        def speaker_traced(*args,**kw):
            result=speaker(*args,**kw);np.save(out/'speaker-embeddings.npy',result);rec['stages']['speaker']=dict(chunks=kw.get('chunks'),embeddingShape=list(result.shape),sha256=sha(out/'speaker-embeddings.npy'));save();return result
        def asr_traced(*args,**kw):
            result=asr(*args,**kw);rec['stages'].setdefault('asr',[]).append(dict(key=kw.get('key'),samples=len(args[0]),text=result[0],metadata=result[1]));save();return result
        bundle.vad_infer=vad_traced;bundle.speaker_infer=speaker_traced;bundle.asr_infer=asr_traced
        transcript=diar_asr(bundle,speech,fs=16000);(out/'transcript.txt').write_text(transcript+'\n',encoding='utf-8');rec['transcript']=transcript;rec['transcriptSha256']=sha(out/'transcript.txt');assert transcript.strip()
        segments=[]
        for line in transcript.splitlines():
            match=re.fullmatch(r'Speaker_(\d+): \[([0-9.]+) ([0-9.]+)\] (.+)',line);assert match,line
            identity,left,right,text=match.groups();assert 0<=float(left)<float(right)<=rec['audio']['durationSeconds']+0.002;segments.append(dict(speaker=int(identity),start=float(left),end=float(right),text=text))
        rec['segments']=segments;rec['speakerCount']=len({s['speaker'] for s in segments})
        for f in manifest['files']:
            d=sha(root/f['path']);assert d==f['verifiedHashes']['sha256'];rec['filesAfter'].append(dict(path=f['path'],sha256=d))
        assert len(rec['sessions'])==3 and all(s['calls']>0 for s in rec['sessions']);rec['completed']=True;print(transcript,flush=True)
    finally:rec['elapsedSeconds']=time.perf_counter()-start;save()
if __name__=='__main__':main()
