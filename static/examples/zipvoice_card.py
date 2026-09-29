"""Trace the official fixed ZipVoice Python pipeline through AXCL."""
import argparse,functools,hashlib,importlib,importlib.metadata,json,os,re,shutil,subprocess,sys,time,types
from pathlib import Path
import axengine
import numpy as np
import soundfile as sf
import torch

SOURCE_HASHES={
 'infer_zipvoice_axera.py':'029770fc1f27d5dd13859348af571f75e67f317370200ddf4ad0aa072178a496',
 'scripts/__init__.py':'45be955983e02f3ba53a715250287a2707f9ad2d1ed1b4942886b3767eb03592',
 'scripts/common_infer.py':'0fc5a4b0abbb34d2e1b679dea13048ceacc98f4b3fb1e2f5d6f085e7f6ea5204',
 'scripts/local_audio.py':'f83c75c7593a0ad9f3b1b1a6391db890c14e4203bbfd90a623701d8530a8969f',
 'scripts/local_tokenizer.py':'f88aa134e2dbdbbab9533a500fd8a324b33ad25c9c3c88c3d020c3b5eab5af59',
 'scripts/text_processing.py':'8db08ea705c60ebc640f475394a8a0c2889b849838ae8b428434dee43d8e9ef3',
 'scripts/zipvoice_decoder4_runtime.py':'d7ecb3fcd8608cb5b835bbc2eab52fe059d79add0594d6d12e95af1122005f6a',
 'scripts/zipvoice_runtime.py':'8167bdb1398ccc2b8d214eca65000b64081e94e932cc08f38194e605691e3569'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
def desc(x):return {'shape':list(x.shape),'dtype':str(x.dtype),'sha256':digest(x)}
def memory():
 n=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1]);assert n>512*1024;return n

def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True)
 p.add_argument('--variant',choices=['standard','distill'],required=True)
 p.add_argument('--phonemizer-prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();root,out=a.model_dir.resolve(),a.output.resolve();assert not out.exists()
 for name,h in SOURCE_HASHES.items():assert sha(root/name)==h,name
 mode='zipvoice_ax650' if a.variant=='standard' else 'zipvoice_distill_ax650'
 config=json.loads((root/'models'/mode/'runtime_config.json').read_text())
 assert (config['num_step'],config['guidance_scale'])==((10,1.0) if a.variant=='standard' else (4,3.0))
 prefix=a.phonemizer_prefix.resolve();binary=prefix/'bin/piper_phonemize';assert binary.is_file()
 assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
 out.mkdir(parents=True);torch.set_num_threads(4);os.environ['ZIPVOICE_AXERA_VERBOSE']='1'
 report={'modelId':'ZipVoice.AXERA','provider':'AXCLRTExecutionProvider','completed':False,'variant':a.variant,
  'sourceHashes':SOURCE_HASHES,'runtimeConfig':config,'configSha256':sha(root/'models'/mode/'runtime_config.json'),
  'splitManifest':json.loads((root/'models'/mode/'decoder4_split_manifest.json').read_text()),
  'splitManifestSha256':sha(root/'models'/mode/'decoder4_split_manifest.json'),
  'phonemizer':{'implementation':'official piper-phonemize CLI, flattened phonemes are passed to the original tokenizer',
    'sourceRevision':'ba3cc06c5248215928821f1393b2b854a936991a','binarySha256':sha(binary),'queries':[]},
  'versions':{n:importlib.metadata.version(n) for n in ['numpy','torch','soundfile','jieba','pypinyin']},
  'settings':{'seed':42,'torchThreads':4,'vocoder':'models/vocoder/vocos_full.axmodel','sampleRate':24000,
    'rawEvidence':'All IO hashes; full encoder/vocoder tensors, decoder part0 inputs and part3 output. Intermediate part0/1/2 outputs retain hashes.'},
  'sessions':[],'samples':[]}
 def save(): (out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 @functools.lru_cache(maxsize=256)
 def phonemize(text,voice):
  assert voice=='en-us' and '\n' not in text
  cmd=[str(binary),'--language',voice,'--espeak_data',str(prefix/'share/espeak-ng-data'),'--json_input']
  r=subprocess.run(cmd,input=json.dumps({'text':text})+'\n',text=True,capture_output=True,timeout=30,check=True)
  j=json.loads(r.stdout);assert j['text']==text and j['phonemes']
  report['phonemizer']['queries'].append({'text':text,'voice':voice,'phonemes':j['phonemes']});save()
  return [j['phonemes']]
 # The official tokenizer flattens sentence lists without inserting separators;
 # the official CLI already produces exactly that flat phoneme list.
 shim=types.ModuleType('piper_phonemize');shim.phonemize_espeak=phonemize;sys.modules['piper_phonemize']=shim
 sys.path.insert(0,str(root));entry=importlib.import_module('infer_zipvoice_axera')
 common=importlib.import_module('scripts.common_infer')
 runtime_module=importlib.import_module('scripts.zipvoice_decoder4_runtime')
 original=axengine.InferenceSession;current={'sample':'','segment':0};raw_files={}
 def store_arrays(arrays):
  metadata={k:desc(v) for k,v in arrays.items()}
  key=hashlib.sha256(json.dumps(metadata,sort_keys=True).encode()).hexdigest();name='raw-'+key+'.npz'
  if key not in raw_files:
   np.savez_compressed(out/name,**arrays);raw_files[key]=sha(out/name)
  return {'file':name,'sha256':raw_files[key],'arrays':metadata}
 class Session:
  def __init__(self,path,*args,**kwargs):
   memory();t=time.perf_counter();self.engine=original(path,providers=['AXCLRTExecutionProvider'])
   def schema(xs):return [{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in xs]
   self.rec={'model':str(Path(path).resolve().relative_to(root)),'sample':current['sample'],
    'weightSha256':sha(Path(path)),'loadSeconds':time.perf_counter()-t,'provider':self.engine.get_providers(),
    'inputs':schema(self.engine.get_inputs()),'outputs':schema(self.engine.get_outputs()),
    'allFinite':True,'runMilliseconds':[],'calls':[]}
   report['sessions'].append(self.rec);save()
  def get_inputs(self):return self.engine.get_inputs()
  def get_outputs(self):return self.engine.get_outputs()
  def run(self,names,feeds):
   memory()
   for cfg in self.get_inputs():
    x=feeds[cfg.name];assert list(x.shape)==list(cfg.shape) and np.isfinite(x).all()
   t=time.perf_counter();ys=self.engine.run(names,feeds);ms=(time.perf_counter()-t)*1000
   assert len(ys)==len(self.get_outputs()) and all(np.isfinite(y).all() for y in ys)
   row={**current,'input':{k:desc(v) for k,v in feeds.items()},'output':{c.name:desc(y) for c,y in zip(self.get_outputs(),ys)}}
   stem=Path(self.rec['model']).stem;arrays={}
   if stem in ['encoder','vocos_full','decoder_part0']:arrays.update({'in_'+str(i):feeds[c.name] for i,c in enumerate(self.get_inputs())})
   if stem in ['encoder','vocos_full','decoder_part3']:arrays.update({'out_'+str(i):y for i,y in enumerate(ys)})
   if arrays:row['raw']=store_arrays(arrays)
   self.rec['calls'].append(row);self.rec['runMilliseconds'].append(ms);save()
   return ys
 axengine.InferenceSession=Session
 original_sample=runtime_module.Decoder4ZipVoiceBoardRuntime.sample
 original_prompt=entry.extract_prompt_features;original_decode=common.axmodel_vocoder_decode
 sample_record=None;segment_record=None
 def capture_prompt(*args,**kwargs):
  feats,rms=original_prompt(*args,**kwargs);assert np.isfinite(feats).all() and rms>0
  sample_record['promptRms']=rms;sample_record['promptFeatures']=store_arrays({'features':feats})
  return feats,rms
 def capture_sample(self,**kwargs):
  nonlocal segment_record
  current['segment']+=1;t=time.perf_counter();pred,timing=original_sample(self,**kwargs)
  assert np.isfinite(pred).all() and 0<pred.shape[1]<=620
  segment_record={'index':current['segment'],'parameters':{k:v for k,v in kwargs.items() if not isinstance(v,np.ndarray)},
   'timing':timing,'recordedSampleSeconds':time.perf_counter()-t,
   'raw':store_arrays({k:v for k,v in kwargs.items() if isinstance(v,np.ndarray)}|{'predFeatures':pred}),
   'decoderSeqLen':self.decoder_seq_len,'hasPaddingMask':self.decoder_has_padding_mask}
  sample_record['segments'].append(segment_record);return pred,timing
 def capture_decode(session,features,**kwargs):
  audio=original_decode(session,features,**kwargs);assert np.isfinite(audio).all() and len(audio)>0
  segment_record['audio']=store_arrays({'floatAudio':audio})
  segment_record['vocoderParameters']=kwargs
  return audio
 entry.extract_prompt_features=capture_prompt;runtime_module.Decoder4ZipVoiceBoardRuntime.sample=capture_sample;common.axmodel_vocoder_decode=capture_decode
 jobs=[('zh','zh_1_4p5s.wav','不管怎么样我和汤姆还是要感谢贝尔卡金的援手','今天午后天气很好，我打开窗户，听见远处有人聊天，水杯也轻轻晃了一下。'),
       ('en','en_4_4p5s.wav','This is almost twice the current industry production level per train.','This morning, a small train left the station, carrying sleepy passengers toward a bright coastal town.')]
 jobs+=[('zh-repeat',*jobs[0][1:])]
 try:
  for kind,prompt_name,prompt_text,text in jobs:
   current.update(sample=kind,segment=0);source=root/'assets/moss_prompts'/prompt_name
   shutil.copy2(source,out/prompt_name);target=out/(kind+'.wav')
   sample_record={'kind':kind,'text':text,'promptText':prompt_text,'promptFile':prompt_name,'promptSha256':sha(source),'segments':[],
                  'availableBeforeKiB':memory()};report['samples'].append(sample_record);save()
   sys.argv=['infer_zipvoice_axera.py','--model-name',mode,'--prompt-text',prompt_text,'--prompt-wav',str(source),
     '--text',text,'--vocoder-model',str(root/'models/vocoder/vocos_full.axmodel'),'--output-wav',str(target),'--seed','42']
   t=time.perf_counter();entry.main();elapsed=time.perf_counter()-t
   wave,sr=sf.read(target,dtype='float32');assert sr==24000 and np.isfinite(wave).all() and np.max(np.abs(wave))>0
   sample_record.update(processSeconds=elapsed,output=target.name,outputSha256=sha(target),audioSeconds=len(wave)/sr,
     peak=float(np.max(np.abs(wave))),rms=float(np.sqrt(np.mean(wave.astype(np.float64)**2))),availableAfterKiB=memory());save()
  report['completed']=True;save();print(json.dumps({'variant':a.variant,'samples':[(s['kind'],s['audioSeconds'],s['processSeconds']) for s in report['samples']],
   'calls':sum(len(s['calls']) for s in report['sessions'])}),flush=True)
 finally:axengine.InferenceSession=original

if __name__=='__main__':main()
