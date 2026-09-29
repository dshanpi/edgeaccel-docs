"""Run the fixed WakeUp SDK on an AXCL M.2 card; retain per-frame evidence."""
import argparse, hashlib, importlib.metadata, json, shutil, sys, time, wave
from pathlib import Path
import numpy as np
import axengine

SOURCE_HASHES = {
 '__init__.py':'baab463be544913adbd54416bd8ce7d6ef3a3f7893288652587b0297fdac93db',
 'detector.py':'f2fada8fbe192ac20f6ffea8d2536046027527aaf292500d825d10257f86f4ef',
 'inference.py':'bf7ee71dcc0d3cdbac9c43bcb2e67de69938eebde8aacddfd90926f478f081eb',
 'postprocess.py':'08fc8eefc476b861c37d2626bfc54b4b46f58c0fa36662a42681971abe53dd6a',
 'preprocess.py':'24c808e93b76fb9e330899a96717baaed8025d79f19a325b49454175c59633ff'}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def desc(x):
 return {'shape':list(x.shape),'dtype':str(x.dtype),'sha256':hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()}
def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--audio',type=Path,action='append');p.add_argument('--threshold',type=float,default=.615);a=p.parse_args()
 root=a.model_dir.resolve();out=a.output.resolve();assert not out.exists();assert np.isfinite(a.threshold)
 for f,h in SOURCE_HASHES.items():assert sha(root/'python/wakeup_axera_sdk'/f)==h,f
 assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
 sys.path.insert(0,str(root/'python'));from wakeup_axera_sdk.detector import WakeWordDetector
 out.mkdir(parents=True);weight=root/'models/ax650/model.axmodel'
 report={'modelId':'WakeUp.axera','provider':'AXCLRTExecutionProvider','completed':False,'sourceHashes':SOURCE_HASHES,
  'versions':{'numpy':importlib.metadata.version('numpy')},'settings':{'threshold':a.threshold,'detWin':3,'frameSamples':512,'sampleRate':16000,'contextFrames':64,'scoreType':'signed score, not probability','resetBetweenSamples':True},'sessions':[],'samples':[]}
 def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 t=time.perf_counter();det=WakeWordDetector(str(weight),providers=['AXCLRTExecutionProvider'],threshold=a.threshold)
 engine=det.session.session
 schema=lambda xs:[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in xs]
 rec={'model':'models/ax650/model.axmodel','weightSha256':sha(weight),'provider':engine.get_providers(),'loadSeconds':time.perf_counter()-t,'inputs':schema(engine.get_inputs()),'outputs':schema(engine.get_outputs()),'allFinite':True,'runMilliseconds':[],'calls':[]}
 report['sessions'].append(rec);shutil.copy2(root/'models/ax650/model_meta.json',out/'model_meta.json')
 assert len(engine.get_inputs())==len(engine.get_outputs())==1
 assert list(engine.get_inputs()[0].shape)==[1,26,64] and list(engine.get_outputs()[0].shape)==[1,2,64]
 current={};original=det.session.run_named
 def trace(feeds,names=None):
  t=time.perf_counter();ys=original(feeds,names);ms=(time.perf_counter()-t)*1000
  assert all(np.isfinite(x).all() for x in feeds+ys)
  arrays={'input':np.ascontiguousarray(feeds[0],dtype=np.float32),'output':ys[0]}
  key=hashlib.sha256(json.dumps({k:desc(v) for k,v in arrays.items()},sort_keys=True).encode()).hexdigest();file=out/('raw-'+key+'.npz')
  if not file.exists():np.savez_compressed(file,**arrays)
  rec['calls'].append({**current,'raw':file.name,'rawSha256':sha(file),'arrays':{k:desc(v) for k,v in arrays.items()}});rec['runMilliseconds'].append(ms)
  return ys
 det.session.run_named=trace
 if a.audio:jobs=[('custom-'+str(i),f.resolve()) for i,f in enumerate(a.audio)]
 else:
  silence=out/'silence.wav'
  with wave.open(str(silence),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(np.zeros(32000,dtype='<i2').tobytes())
  jobs=[('positive',root/'models/sample_nihao_aixin.wav'),('near-negative',root/'models/sample_nihao_qita.wav'),('positive-repeat',root/'models/sample_nihao_aixin.wav'),('silence',silence)]
 for kind,path in jobs:
  with wave.open(str(path),'rb') as w:
   assert w.getframerate()==16000 and w.getnchannels()==1 and w.getsampwidth()==2 and w.getcomptype()=='NONE','Use 16 kHz mono PCM16 WAV'
   pcm=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').copy()
  assert len(pcm)>=1536,'Need at least three complete frames'
  dest=out/(kind+'.wav')
  if dest!=path:shutil.copy2(path,dest)
  det.reset();rows=[];t=time.perf_counter()
  for i in range(len(pcm)//512):
   current.update(sample=kind,frame=i);rows.append(det.process(pcm[i*512:(i+1)*512]))
  elapsed=time.perf_counter()-t;scores=np.array([r['wake_score'] for r in rows]);batch=np.convolve(scores,np.ones(3),mode='valid');trigger=[i for i,r in enumerate(rows) if r['triggered']]
  row={'kind':kind,'input':dest.name,'inputSha256':sha(dest),'sampleCount':len(pcm),'audioSeconds':len(pcm)/16000,'frames':rows,'discardedTailSamples':len(pcm)%512,'processSeconds':elapsed,'triggeredFrames':len(trigger),'firstTriggerEndSeconds':(trigger[0]+1)*.032 if trigger else None,'maxStreamingSum':max(r['window_sum'] for r in rows),'maxBatchSum':float(batch.max()),'streamTriggered':bool(trigger),'batchTriggered':bool(np.any(batch>a.threshold))}
  report['samples'].append(row);save();print(json.dumps({k:v for k,v in row.items() if k!='frames'}),flush=True)
 report['completed']=True;save()
if __name__=='__main__':main()
