"""Run four-stem music separation with fixed official preprocessing on AXCL."""
import argparse,hashlib,json,shutil,sys,time
from pathlib import Path
import axengine
import numpy as np
import soundfile as sf
import torch

p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--audio',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();root,out=a.model_dir.resolve(),a.output.resolve()
assert not out.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
source_sha='754aa6483d29cf81029d5e32614dc540262dc46c5a9f10cf0da5cc01f2175cab'
assert sha(root/'MelBandRoformer.py')==source_sha
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
wave,sr=sf.read(a.audio,dtype='float32',always_2d=True)
assert sr==44100 and wave.shape[1]==2 and 0<len(wave)/sr<=15 and np.isfinite(wave).all()
torch.manual_seed(0);torch.set_num_threads(4)
out.mkdir(parents=True);shutil.copy2(a.audio,out/'input.wav')
sf.write(out/'silence.wav',np.zeros((2*sr,2),np.float32),sr,subtype='PCM_24')
report={'modelId':'mel_band_roformer','provider':'AXCLRTExecutionProvider','completed':False,'sourceSha256':source_sha,
 'audioSha256':sha(a.audio),'settings':{'sampleRate':sr,'segmentSamples':88200,'overlap':.25,'strideSamples':66150,'nFft':2048,'hopLength':441,'torchThreads':4},
 'sessions':[],'samples':[]}
original=axengine.InferenceSession;sample_index=0;chunks=[];pending=None;seen={}
def save(): (out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
class Measured:
 def __init__(self,path,providers):
  assert providers==['AxEngineExecutionProvider','AXCLRTExecutionProvider']
  t=time.perf_counter();self.engine=original(path,providers=['AXCLRTExecutionProvider'])
  self.record={'model':'mel_band_roformer.axmodel','weightSha256':sha(Path(path)),'loadSeconds':time.perf_counter()-t,'allFinite':True,
   'runMilliseconds':[],'calls':[],'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.engine.get_inputs()],
   'outputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.engine.get_outputs()]}
  report['sessions'].append(self.record);save()
 def run(self,names,feeds):
  global pending
  for m in self.engine.get_inputs():assert feeds[m.name].shape==tuple(m.shape) and feeds[m.name].dtype==np.dtype(m.dtype) and np.isfinite(feeds[m.name]).all()
  t=time.perf_counter();values=self.engine.run(names,feeds);ms=(time.perf_counter()-t)*1000
  assert len(values)==1 and all(np.isfinite(v).all() for v in values)
  x=feeds['stft_input'];y=values[0];ih,oh=digest(x),digest(y);key=ih+oh
  if key not in seen:
   raw=out/f'io-{len(seen)+1:02d}.npz';np.savez_compressed(raw,stft=x,masks=y);seen[key]={'file':raw.name,'sha256':sha(raw)}
  pending={'sampleIndex':sample_index,'inputHash':ih,'outputHash':oh,'raw':seen[key]}
  self.record['runMilliseconds'].append(ms);self.record['calls'].append(pending)
  return values
sys.path.insert(0,str(root));axengine.InferenceSession=Measured
try:
 from MelBandRoformer import MelBandRoformer
 model=MelBandRoformer(str(root/'mel_band_roformer.axmodel'))
 np.savez_compressed(out/'frequency-layout.npz',indices=model.freq_indices.numpy(),counts=model.num_bands_per_freq.numpy())
 report['frequencyLayoutSha256']=sha(out/'frequency-layout.npz')
 postprocess=model.postprocess
 def capture(*args,**kwargs):
  result=postprocess(*args,**kwargs)
  chunk=out/f'chunk-{sample_index:02d}-{len(chunks)+1:02d}.npz';np.savez_compressed(chunk,audio=result)
  pending.update(chunkFile=chunk.name,chunkSha256=sha(chunk),chunkOutputHash=digest(result),audioLength=result.shape[-1])
  chunks.append(pending.copy());return result
 model.postprocess=capture
 for kind,wav in [('music',out/'input.wav'),('repeat',out/'input.wav'),('silence',out/'silence.wav')]:
  sample_index+=1;chunks=[];audio,rate=sf.read(wav,dtype='float32',always_2d=True)
  t=time.perf_counter();stems=model.infer(audio.T,chunk_size=88200,overlap=.25,num_stems=4);elapsed=time.perf_counter()-t
  assert stems.shape==(4,2,len(audio)) and np.isfinite(stems).all()
  raw=out/f'{kind}-stems.npz';np.savez_compressed(raw,audio=audio,stems=stems)
  outputs=[]
  for name,stem in zip(['drums','bass','other','vocals'],stems):
   gain=max(1.01*float(np.max(np.abs(stem))),1.);pcm=out/f'{kind}-{name}.wav';sf.write(pcm,(stem/gain).T,rate,subtype='PCM_24')
   outputs.append({'stem':name,'file':pcm.name,'sha256':sha(pcm),'peakBeforeScaling':float(np.max(np.abs(stem))),
    'rmsBeforeScaling':float(np.sqrt(np.mean(stem**2))),'saveDivisor':gain,'sampleRate':rate,'samples':len(audio),'channels':2})
  row={'kind':kind,'audioSeconds':len(audio)/rate,'processSeconds':elapsed,'includesRawEvidenceWriting':True,
   'chunks':chunks,'rawFile':raw.name,'rawSha256':sha(raw),'outputs':outputs}
  report['samples'].append(row);save();print(json.dumps(row),flush=True)
 report['completed']=True;save()
finally:axengine.InferenceSession=original
