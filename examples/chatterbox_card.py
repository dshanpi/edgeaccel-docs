"""Run official Chatterbox S3 speech tokens on an AXCL M.2 card (not text-to-token)."""
import argparse,hashlib,importlib.util,json,time
from pathlib import Path
import numpy as np
import axengine
MID='chatterbox-onestep'
REVISION='2bec38c6ef8b34b721422d41d2030f6a226bfaac'
PROVIDER='AXCLRTExecutionProvider'
def sha(b):return hashlib.sha256(b).hexdigest()
def info(v):return {'shape':list(v.shape),'dtype':str(v.dtype),'sha256':sha(v.tobytes())}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--manifest',type=Path);p.add_argument('--reference-dir',type=Path);a=p.parse_args()
 root=a.model_dir.resolve();out=a.output.resolve()
 manifest=a.manifest or root/'.validation-download.json'
 if not manifest.exists():manifest=Path(__file__).with_name('download-manifest.json')
 d=json.loads(manifest.read_text());assert d['complete'] and d['revision']==REVISION
 for f in d['files']:assert sha((root/f['path']).read_bytes())==f['verifiedHashes']['sha256'],f['path']
 spec=importlib.util.spec_from_file_location('official_hift',root/'python/hift_vocoder.py');dsp=importlib.util.module_from_spec(spec);spec.loader.exec_module(dsp)
 out.mkdir(parents=True,exist_ok=False)
 record={'modelId':MID,'revision':REVISION,'provider':PROVIDER,'completed':False,'sessions':[],'samples':[], 'cpuStages':['mel chunk assembly','HiFT sine/noise excitation','STFT','ISTFT','PCM WAV'], 'scope':'S3 speech-token-to-waveform; no T3 text-to-token stage', 'melChunkPolicy':'198 frames per HiFT call; concatenate valid outputs without overlap or crossfade'}
 def save():(out/'deployment-result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 class Session:
  def __init__(self,name):
   t=time.perf_counter();self.s=axengine.InferenceSession(str(root/'models'/name),providers=[PROVIDER]);assert self.s.get_providers() in [PROVIDER,[PROVIDER]]
   self.inputs=self.s.get_inputs();self.outputs=self.s.get_outputs()
   self.row={'model':'models/'+name,'weightSha256':sha((root/'models'/name).read_bytes()),'provider':PROVIDER,'loadSeconds':time.perf_counter()-t,'allFinite':True,'inputs':[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in self.inputs],'outputs':[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in self.outputs],'runMilliseconds':[],'calls':[]};record['sessions'].append(self.row);save()
  def run(self,feed,folder,tag):
   assert set(feed)=={x.name for x in self.inputs}
   for m in self.inputs:assert list(feed[m.name].shape)==list(m.shape) and feed[m.name].dtype==m.dtype and np.isfinite(feed[m.name]).all(),m.name
   t=time.perf_counter();vv=self.s.run(None,{k:np.ascontiguousarray(v) for k,v in feed.items()});ms=1000*(time.perf_counter()-t)
   result={m.name:v.copy() for m,v in zip(self.outputs,vv)}
   for m in self.outputs:assert list(result[m.name].shape)==list(m.shape) and np.isfinite(result[m.name]).all()
   arrays={**{'in_'+k:v for k,v in feed.items()},**{'out_'+k:v for k,v in result.items()}}
   path=folder/(tag+'.npz');np.savez_compressed(path,**arrays)
   self.row['calls'].append({'file':path.relative_to(out).as_posix(),'sha256':sha(path.read_bytes()),'inputs':{k:{**info(v),'key':'in_'+k} for k,v in feed.items()},'outputs':{k:{**info(v),'key':'out_'+k} for k,v in result.items()}});self.row['runMilliseconds'].append(ms)
   return result
 base=Session('model.axmodel');clone=Session('model_clone.axmodel') if a.reference_dir else None
 f0net=Session('hifift_f0.axmodel');decoder=Session('hifift_decode.axmodel')
 w=np.load(root/'python/hift_linear_w.npy',allow_pickle=False).astype(np.float64).reshape(1,9);b=np.load(root/'python/hift_linear_b.npy',allow_pickle=False).astype(np.float64)
 tokens=np.load(root/'sample_input/tokens.npy',allow_pickle=False);length=np.load(root/'sample_input/token_len.npy',allow_pickle=False);embedding=np.load(root/'sample_input/embedding.npy',allow_pickle=False);z=np.load(root/'sample_input/z.npy',allow_pickle=False)
 n=int(length.item());assert 0<n<=256 and tokens.shape==(1,256) and np.all((tokens>=0)&(tokens<6561))
 jobs=[('official-full','base',n),('official-repeat','base',n)]
 if clone:jobs+=[('reference-first99','clone',min(99,n)),('reference-repeat','clone',min(99,n))]
 for name,mode,count in jobs:
  folder=out/name;folder.mkdir();starts=[len(s['calls']) for s in record['sessions']];t=time.perf_counter()
  if mode=='base':mel=base.run({'tokens':tokens,'token_len':length,'embedding':embedding,'z':z},folder,'base')['mel'][:,:,:count*2].copy()
  else:
   ref=a.reference_dir;emb=np.load(ref/'ref_embedding.npy',allow_pickle=False);pt=np.load(ref/'ref_prompt_token.npy',allow_pickle=False);pf=np.load(ref/'ref_prompt_feat.npy',allow_pickle=False)
   assert pt.shape==(1,157) and pt.dtype==np.int32 and np.all((pt>=0)&(pt<6561));assert emb.shape==(1,192) and pf.shape==(1,314,80)
   all_tokens=np.zeros((1,256),np.int32);all_tokens[:,:157]=pt;all_tokens[:,157:157+count]=tokens[:,:count]
   rng=np.random.default_rng(42);mels=[]
   for i in range(4):
    zz=rng.standard_normal((1,80,512)).astype(np.float32)
    mels.append(clone.run({'tokens_all':all_tokens,'token_len_all':np.array([157+count],np.int32),'embedding':emb,'z':zz,'prompt_feat':pf},folder,f'clone-{i}')['mel'])
   mel=np.mean(np.stack(mels),axis=0,dtype=np.float32)[:,:,:count*2].copy()
  assert mel.shape==(1,80,count*2) and np.isfinite(mel).all();np.save(folder/'mel.npy',mel)
  pieces=[];chunks=[];rng=np.random.default_rng(2026)
  for index,start in enumerate(range(0,mel.shape[2],198)):
   size=min(198,mel.shape[2]-start);pad=np.full((1,80,198),-11,np.float32);pad[:,:,:size]=mel[:,:,start:start+size]
   phase=rng.uniform(-np.pi,np.pi,size=(1,9,1));phase[:,0,:]=0;noise=rng.standard_normal((1,9,95040))
   f0=f0net.run({'mel':pad},folder,f'chunk-{index}-f0')['f0']
   excitation=dsp.sine_source(dsp.f0_upsample(f0),phase,noise,w,b);stft=dsp.source_stft(excitation)
   values=decoder.run({'mel':pad,'s_stft':stft},folder,f'chunk-{index}-decode')
   unclipped=dsp._istft(np.exp(values['raw_mag'][0].astype(np.float64)).T,np.sin(values['raw_phase'][0].astype(np.float64)).T)
   assert np.isfinite(unclipped).all()
   wav=np.clip(unclipped,-.99,.99)[:size*480].astype(np.float32);pieces.append(wav)
   np.savez_compressed(folder/f'chunk-{index}-dsp.npz',phase=phase,noise=noise,source=excitation,unclipped=unclipped,waveform=wav)
   chunks.append({'index':index,'melStart':start,'validMelFrames':size,'samples':len(wav),'limitedSamples':int(np.count_nonzero(np.abs(unclipped[:size*480])>.99))})
  waveform=np.concatenate(pieces);assert len(waveform)==count*960;np.save(folder/'waveform.npy',waveform);(folder/'output.wav').write_bytes(dsp.wav_bytes(waveform))
  record['samples'].append({'name':name,'mode':mode,'sourceTokenRange':[0,count],'speechTokens':count,'melFrames':2*count,'audioSeconds':len(waveform)/24000,'pipelineSecondsWithTrace':time.perf_counter()-t,'calls':[len(s['calls'])-x for s,x in zip(record['sessions'],starts)],'chunks':chunks,'waveFile':f'{name}/output.wav','waveSha256':sha((folder/'output.wav').read_bytes()),'floatFile':f'{name}/waveform.npy','floatSha256':sha((folder/'waveform.npy').read_bytes()),'floatPeak':float(np.max(np.abs(waveform))),'files':[{'file':f.relative_to(out).as_posix(),'sha256':sha(f.read_bytes()),'bytes':f.stat().st_size} for f in sorted(folder.iterdir())]});save();print(name,record['samples'][-1]['audioSeconds'],'seconds',flush=True)
 record['completed']=True;save()
if __name__=='__main__':main()
