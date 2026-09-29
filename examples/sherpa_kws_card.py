"""Run fixed official Sherpa KWS Python code through an explicit AXCL provider."""
import argparse,hashlib,importlib.metadata,json,re,shutil,sys,time,wave
from pathlib import Path
import axengine
import numpy as np

SOURCE_HASHES={'scripts/runtime.py':'99b9f762b630a186cf3b010f57b11987564cb76e41ab403e78d3ada57729b0fb',
 'scripts/sherpa_kws_ax.py':'f6205b7cbcce709635893668ae99e737d05f4358db67ff8ecc73e1b88ffede22'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def desc(a):return {'shape':list(a.shape),'dtype':str(a.dtype),'sha256':hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()}
def memory():
 n=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1]);assert n>512*1024;return n

def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True)
 p.add_argument('--chunk-size',type=int,choices=[8,16],required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();root=a.model_dir.resolve();out=a.output.resolve();assert not out.exists()
 for name,h in SOURCE_HASHES.items():assert sha(root/name)==h
 assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
 out.mkdir(parents=True);sys.path.insert(0,str(root/'scripts'))
 report={'modelId':'Sherpa-ONNX-KWS.AXERA','provider':'AXCLRTExecutionProvider','completed':False,
  'sourceHashes':SOURCE_HASHES,'versions':{n:importlib.metadata.version(n) for n in ['numpy','kaldi-native-fbank']},
  'settings':{'chunkSize':a.chunk_size,'maxActivePaths':1,'keywordsThreshold':.25,'numTrailingBlanks':1,
   'decoderCache':'Fresh decoder/cache per audio sample; original algorithm unchanged within each sample.',
   'rawEvidence':'All IO hashes; encoder outputs, decoder/joiner inputs and outputs, fbank, initial decoder output.'},
  'sessions':[],'samples':[]}
 def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 current={'sample':'','chunk':-1,'frame':-1};counter=0;cached={};stored=0
 def store(arrays):
  nonlocal stored
  meta={k:desc(v) for k,v in arrays.items()};key=hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest();name='raw-'+key+'.npz'
  if key not in cached:
   np.savez_compressed(out/name,**arrays);stored+=(out/name).stat().st_size
   assert stored<1024**3,'Evidence exceeded 1 GiB budget'
   cached[key]=sha(out/name)
  return {'file':name,'sha256':cached[key],'arrays':meta}
 original=axengine.InferenceSession
 class Session:
  def __init__(self,path,*args,**kwargs):
   memory();t=time.perf_counter();self.engine=original(path,providers=['AXCLRTExecutionProvider'])
   schema=lambda xs:[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in xs]
   self.rec={'model':str(Path(path).resolve().relative_to(root)),'weightSha256':sha(Path(path)),
    'provider':self.engine.get_providers(),'loadSeconds':time.perf_counter()-t,'inputs':schema(self.engine.get_inputs()),
    'outputs':schema(self.engine.get_outputs()),'allFinite':True,'runMilliseconds':[],'calls':[]}
   report['sessions'].append(self.rec);save()
  def get_inputs(self):return self.engine.get_inputs()
  def get_outputs(self):return self.engine.get_outputs()
  def run(self,names,feeds):
   nonlocal counter
   memory();encoder='__encoder-' in self.rec['model']
   if encoder:current['chunk']+=1
   for cfg in self.get_inputs():assert list(feeds[cfg.name].shape)==list(cfg.shape) and np.isfinite(feeds[cfg.name]).all()
   t=time.perf_counter();ys=self.engine.run(names,feeds);ms=(time.perf_counter()-t)*1000
   assert len(ys)==len(self.get_outputs()) and all(np.isfinite(v).all() for v in ys)
   row={**current,'index':counter,'input':{k:desc(v) for k,v in feeds.items()},'output':{c.name:desc(v) for c,v in zip(self.get_outputs(),ys)}};counter+=1
   raw={'out_'+str(i):v for i,v in enumerate(ys)}
   if not encoder:raw.update({'in_'+str(i):feeds[c.name] for i,c in enumerate(self.get_inputs())})
   row['raw']=store(raw);self.rec['calls'].append(row);self.rec['runMilliseconds'].append(ms)
   return ys
 axengine.InferenceSession=Session
 import sherpa_kws_ax as official
 tokenfile=root/'config/tokens.txt';kwfile=root/'config/keywords.txt';initfile=root/'config/sherpa_decoder_initial.npy'
 for f in [tokenfile,kwfile,initfile]:shutil.copy2(f,out/f.name)
 table=official.load_token_table(tokenfile);keywords=official.load_keywords(kwfile,table,1,.25)
 initial=np.load(initfile,allow_pickle=False);assert initial.shape in [(1,320),(320,)] and np.isfinite(initial).all()
 report.update(keywords=keywords,configHashes={f.name:sha(f) for f in [tokenfile,kwfile,initfile]},initialDecoder=store({'initial':initial}))
 reference_file=root/'reference/local_inference_results.json'
 report['upstreamReferenceSha256']=sha(reference_file)
 references=official.reference_by_audio(reference_file,a.chunk_size)
 sessions={name:official.InferenceSession(official.model_path(root/'models/650',name,a.chunk_size,'axengine'),'axengine') for name in ['encoder','decoder','joiner']}
 original_features=official.compute_fbank;sample_record=None
 def features(samples,sr):
  x=original_features(samples,sr);sample_record['features']=store({'features':x});return x
 official.compute_fbank=features
 class Decoder(official.SinglePathKeywordDecoder):
  def decode_frame(self,encoder_frame):
   current['frame']+=1;before=list(self.history)
   phrase=super().decode_frame(encoder_frame)
   sample_record['frames'].append({'frame':current['frame'],'chunk':current['chunk'],'historyBefore':before,
    'historyAfter':list(self.history),'trailingBlanksAfter':self.trailing_blanks,'detected':phrase})
   return phrase
 jobs=[(f.stem,f) for f in sorted((root/'audio/sherpa').glob('*.wav'))];assert len(jobs)==9
 jobs.append(('zh_0-repeat',root/'audio/sherpa/zh_0.wav'))
 silence=out/'silence.wav'
 with wave.open(str(silence),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(np.zeros(32000,dtype='<i2').tobytes())
 jobs.append(('silence',silence))
 try:
  for name,path in jobs:
   current.update(sample=name,chunk=-1,frame=-1);memory()
   if path.parent!=out:shutil.copy2(path,out/(name+'.wav'))
   sample_record={'kind':name,'input':name+'.wav','inputSha256':sha(path),'frames':[]};report['samples'].append(sample_record);save()
   decoder=Decoder(sessions['decoder'],sessions['joiner'],official.ContextGraph(keywords),initial,1)
   t=time.perf_counter();result=official.infer_audio(path,sessions['encoder'],decoder,a.chunk_size,references.get(path.name) if name!='silence' else None)
   elapsed=time.perf_counter()-t;result['audio']=name+'.wav'
   sample_record.update(result=result,processSeconds=elapsed,audioSeconds=result['sample_count']/result['sample_rate'],
    cacheEntries=len(decoder.cache),availableAfterKiB=memory());save()
   print(json.dumps({'chunk':a.chunk_size,'sample':name,'detections':result['detections'],'referenceMatch':result['detection_match'],'seconds':elapsed},ensure_ascii=False),flush=True)
  assert all(s['runMilliseconds'] for s in report['sessions'])
  report.update(completed=True,evidenceBytes=stored);save()
 finally:axengine.InferenceSession=original

if __name__=='__main__':main()
