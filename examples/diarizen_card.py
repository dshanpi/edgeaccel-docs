"""Run DiariZen's fixed 4-second CNN AXCL + ONNX CPU segmentation pipeline."""
import argparse,hashlib,itertools,json,re,shutil,sys,time
from pathlib import Path
import axengine
import numpy as np
import onnxruntime as ort
import soundfile as sf

p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--audio',type=Path,required=True)
p.add_argument('--output',type=Path,required=True);p.add_argument('--cpu-threads',type=int,default=4)
a=p.parse_args();root,out=a.model_dir.resolve(),a.output.resolve()
assert not out.exists() and 1<=a.cpu_threads<=4
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda v:hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()
hashes={'inference.py':'cdb71bd935d9438aec0174f202679e59211a204ba395b3c56be1e3f8f71105e7',
 'postprocess.py':'1b7cc5c80c3d46d89dadcffd2d86d68ba93fdcd1a7796dfea6014c8141a835e0',
 'preprocess.py':'cb39a2c674521e1b62412874b8c43ca66b221b6d7094f025448857317c176dea',
 '__init__.py':'a2c913e14953552825ae7139a195b728c18204f3054789c7d2b0058ec97f1b42'}
for name,value in hashes.items():assert sha(root/'python/diarizen_sdk'/name)==value
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
audio,sr=sf.read(a.audio,dtype='float32',always_2d=True);audio=audio[:,0]
assert 0<len(audio)/sr<=60 and np.isfinite(audio).all()
out.mkdir(parents=True);shutil.copy2(a.audio,out/'input.wav')
mapping=np.zeros((11,4),dtype=np.int64);classes=[]
for size in range(3):
 for group in itertools.combinations(range(4),size):
  mapping[len(classes),list(group)]=1;classes.append(list(group))
report={'modelId':'DiariZen','provider':'AXCLRTExecutionProvider','completed':False,'sourceHashes':hashes,
 'inputSha256':sha(a.audio),'audioSeconds':len(audio)/sr,'sampleRate':sr,
 'settings':{'windowSeconds':4,'cpuThreads':a.cpu_threads,'cpuInterOpThreads':1,'powersetClasses':classes,
 'speakerLabelsAreWindowLocal':True,'crossWindowClustering':False},'sessions':[],'samples':[]}
original_ax=axengine.InferenceSession;original_ort=ort.InferenceSession;current=0;captured={}
def save(): (out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def memory():
 available=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])
 assert available>512*1024,'Host MemAvailable below 512 MiB; stop before another window'
 return available
def schema(session):return [{'name':x.name,'shape':list(x.shape),'dtype':str(getattr(x,'dtype',getattr(x,'type','')))} for x in session.get_inputs()]
class CNN:
 def __init__(self,path):
  t=time.perf_counter();self.engine=original_ax(path,providers=['AXCLRTExecutionProvider'])
  self.record={'model':'models/cnn_features.axmodel','weightSha256':sha(Path(path)),'loadSeconds':time.perf_counter()-t,
   'allFinite':True,'inputs':schema(self.engine),'runMilliseconds':[],'calls':[]}
  report['sessions'].append(self.record);save()
 def input_names(self):return [x.name for x in self.engine.get_inputs()]
 def run(self,feeds):
  assert len(feeds)==1
  value=next(iter(feeds.values()));assert value.shape==(1,64000) and value.dtype==np.float32 and np.isfinite(value).all()
  t=time.perf_counter();result=self.engine.run(None,feeds);elapsed=(time.perf_counter()-t)*1000
  assert len(result)==1 and result[0].shape==(1,199,211) and np.isfinite(result[0]).all()
  self.record['runMilliseconds'].append(elapsed);self.record['calls'].append({'sampleIndex':current,'inputHash':digest(value),'outputHash':digest(result[0])})
  captured['normalized']=value.copy();captured['cnnFeatures']=result[0].copy()
  return result
class CPU:
 def __init__(self,path,providers):
  assert providers==['CPUExecutionProvider']
  opts=ort.SessionOptions();opts.intra_op_num_threads=a.cpu_threads;opts.inter_op_num_threads=1
  opts.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
  t=time.perf_counter();self.engine=original_ort(path,sess_options=opts,providers=providers)
  assert self.engine.get_providers()==providers
  self.record={'model':'models/backend.onnx','provider':'CPUExecutionProvider','weightSha256':sha(Path(path)),
   'loadSeconds':time.perf_counter()-t,'allFinite':True,'inputs':schema(self.engine),'runMilliseconds':[],'calls':[]}
  report['cpuSession']=self.record;save();memory()
 def get_inputs(self):return self.engine.get_inputs()
 def run(self,names,feeds):
  x=next(iter(feeds.values()));assert np.array_equal(x,captured['cnnFeatures'])
  t=time.perf_counter();result=self.engine.run(names,feeds);elapsed=(time.perf_counter()-t)*1000
  assert len(result)==1 and result[0].shape==(1,199,11) and np.isfinite(result[0]).all()
  self.record['runMilliseconds'].append(elapsed);self.record['calls'].append({'sampleIndex':current,'inputHash':digest(x),'outputHash':digest(result[0])})
  captured['logProbs']=result[0].copy();return result

sys.path.insert(0,str(root/'python'))
from diarizen_sdk import DiarizenSegmenter
from diarizen_sdk.postprocess import log_probs_to_probs
axengine.InferenceSession=CNN;ort.InferenceSession=CPU
try:
 model=DiarizenSegmenter(str(root/'models/cnn_features.axmodel'),str(root/'models/backend.onnx'))
 model._init_cnn();model._init_backend()
 jobs=[('window',i, audio[i:i+4*sr]) for i in range(0,len(audio),4*sr)]
 jobs+=[('repeat',0,audio[:4*sr]),('silence',0,np.zeros(4*sr,np.float32))]
 for kind,start,wave in jobs:
  current+=1;captured={};available=memory();t=time.perf_counter()
  logprobs=model(wave,sr);probs=log_probs_to_probs(logprobs);pred=np.argmax(probs[0],axis=-1);activity=mapping[pred]
  elapsed=time.perf_counter()-t
  assert np.allclose(probs.sum(axis=-1),1,atol=1e-5)
  npz=out/f'window-{current:02d}.npz';np.savez_compressed(npz,wave=wave,probabilities=probs,classes=pred,activity=activity,**captured)
  row={'kind':kind,'startSeconds':start/sr,'inputSeconds':len(wave)/sr,'paddedSeconds':4-len(wave)/sr,
   'processSeconds':elapsed,'cnnMilliseconds':report['sessions'][0]['runMilliseconds'][-1],
   'cpuMilliseconds':report['cpuSession']['runMilliseconds'][-1],'availableBeforeKiB':available,'availableAfterKiB':memory(),
   'activeLocalSpeakers':int(activity.any(axis=0).sum()),'classFrameCounts':np.bincount(pred,minlength=11).tolist(),
   'speakerActiveFrameCounts':activity.sum(axis=0).tolist(),'rawFile':npz.name,'rawSha256':sha(npz)}
  report['samples'].append(row);save();print(json.dumps(row),flush=True)
 report['completed']=True;save()
finally:
 axengine.InferenceSession=original_ax;ort.InferenceSession=original_ort
