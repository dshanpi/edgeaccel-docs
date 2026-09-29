"""AXCL adaptation of the fixed official MOSS-TTS-Nano.AXERA release."""
import argparse,hashlib,json,logging,sys,time
from pathlib import Path
import numpy as np

def digest(x):return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
def save_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

class TracedSession:
 def __init__(self,path,backend,owner,key):
  self.owner=owner;self.key=key;self.path=path;self.backend=backend
  if backend=='AXCLRTExecutionProvider':
   import axengine
   self.session=axengine.InferenceSession(str(path),providers=[backend])
  else:
   import onnxruntime as ort
   opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1;opts.enable_cpu_mem_arena=False
   self.session=ort.InferenceSession(str(path),sess_options=opts,providers=[backend])
  providers=self.session.get_providers();assert backend in ([providers] if isinstance(providers,str) else providers)
  self.inputs=self.session.get_inputs();self.outputs=self.session.get_outputs();assert self.inputs and self.outputs
 def get_inputs(self):return self.inputs
 def get_outputs(self):return self.outputs
 def run(self,names,feed,*args,**kwargs):
  assert set(feed)=={x.name for x in self.inputs}
  for x in self.inputs:
   arr=feed[x.name];assert tuple(arr.shape)==tuple(x.shape),(x.name,arr.shape,x.shape)
   dtype=getattr(x,'dtype',None)
   if dtype is None:dtype={'tensor(float)':np.dtype('float32'),'tensor(int32)':np.dtype('int32'),'tensor(int64)':np.dtype('int64'),'tensor(bool)':np.dtype('bool')}[x.type]
   assert arr.dtype==dtype and np.isfinite(arr).all(),(x.name,arr.dtype,dtype)
  begin=time.perf_counter();values=self.session.run(None,feed);ms=1000*(time.perf_counter()-begin)
  out={x.name:np.asarray(v).copy() for x,v in zip(self.outputs,values,strict=True)};assert all(np.isfinite(v).all() for v in out.values())
  index=len(self.owner.calls);name=f'{index:04d}-{self.key}';arrays={};record={'name':name,'network':self.key,'backend':self.backend,'model':str(self.path.relative_to(self.owner.model_dir)),'milliseconds':ms,'inputHashes':{k:digest(v) for k,v in feed.items()},'outputHashes':{k:digest(v) for k,v in out.items()}}
  for k,v in feed.items():
   if not (self.key=='decode' and k.startswith('past_')):arrays['in_'+k]=v
  for k,v in out.items():
   if self.key=='decode' and k.startswith('present_'):
    past=feed[k.replace('present_','past_',1)];assert v.dtype==past.dtype==np.float32
    assert v.shape[1] in (1,past.shape[1]+1)
    record['cacheOutputFormat']='new-row' if v.shape[1]==1 else 'full-cache'
    arrays['new_'+k]=v[:,-1:].copy()
    if v.shape[1]!=1:
     xor=np.bitwise_xor(v[:,:-1].view(np.uint32),past.view(np.uint32))
     if np.any(xor):arrays['xor_'+k]=xor
   else:arrays['out_'+k]=v
  np.savez_compressed(self.owner.case_dir/(name+'.npz'),**arrays);self.owner.calls.append(record)
  wanted=[x.name for x in self.outputs] if names is None else names
  return [out[k] for k in wanted]

class NewRowDecoderAdapter:
 """Expand the published ONNX's new KV rows for the upstream full-cache loop.

 This is host-side adaptation, equivalent to upstream Static320 NewKvSessionAdapter.
 The wrapped TracedSession archives the actual one-row neural-network outputs.
 """
 def __init__(self,session):
  self.session=session;self.inputs=session.get_inputs();self.raw_outputs=session.get_outputs()
  assert len(self.inputs)==26 and len(self.raw_outputs)==25
  from types import SimpleNamespace
  self.outputs=[]
  for x in self.raw_outputs:
   shape=list(x.shape)
   if x.name.startswith('present_'):
    assert shape[1]==1;past=next(i for i in self.inputs if i.name==x.name.replace('present_','past_',1));shape[1]=past.shape[1]+1
   self.outputs.append(SimpleNamespace(name=x.name,shape=shape,type=getattr(x,'type',None)))
 def get_inputs(self):return self.inputs
 def get_outputs(self):return self.outputs
 def run(self,names,feed,*args,**kwargs):
  assert names is None
  values=self.session.run(None,feed);out=[]
  for spec,value in zip(self.raw_outputs,values,strict=True):
   out.append(np.concatenate([feed[spec.name.replace('present_','past_',1)],value],axis=1) if spec.name.startswith('present_') else value)
  return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--decode-backend',choices=['cpu','axcl'],default='cpu');p.add_argument('--text');p.add_argument('--voice',default='Junhao');p.add_argument('--max-frames',type=int,default=110);p.add_argument('--first-only',action='store_true');a=p.parse_args()
 assert 1<=a.max_frames<=128
 if a.text is not None and not a.text.strip():raise ValueError('Text must not be empty')
 a.model_dir=a.model_dir.resolve();a.output=a.output.resolve();a.output.mkdir(exist_ok=False,parents=True)
 manifest_path=a.model_dir/'.validation-download.json'
 if not manifest_path.is_file():manifest_path=Path(__file__).resolve().parent/'download-manifest.json'
 manifest=json.loads(manifest_path.read_text(encoding='utf-8'));assert manifest['complete'] and manifest['modelId']=='MOSS-TTS-Nano.AXERA' and manifest['revision']=='74e28d5b9f1d91634b85fdb77ab245744ee7e3f7'
 for f in manifest['files']:assert hashlib.sha256((a.model_dir/f['path']).read_bytes()).hexdigest()==f['verifiedHashes']['sha256']
 sys.path.insert(0,str(a.model_dir));from scripts.tts_runtime import AxTtsRuntime
 class Runtime(AxTtsRuntime):
  def __init__(self):
   self.model_dir=a.model_dir;self.calls=[];self.decisions=[];self.chunks=[]
   super().__init__(a.model_dir/'config',a.model_dir/'models/axmodels_650',onnx_dir=a.model_dir/'models/onnxmodels',use_onnx_decode=a.decode_backend=='cpu',max_new_frames=a.max_frames,do_sample=True,sample_mode='fixed')
   prefill_shape=next(x.shape for x in self.sessions['prefill'].get_inputs() if x.name=='input_ids');codec_shape=next(x.shape for x in self.sessions['codec_decode'].get_inputs() if x.name=='audio_codes')
   assert list(prefill_shape)==[1,512,17] and list(codec_shape)==[1,128,16]
   self.tts_static_shapes['prefill_seq']=int(prefill_shape[1]);self.codec_static_shapes['decode_code_length']=int(codec_shape[1])
  def _infer_global_kv_len(self):
   shapes=[list(x.shape) for x in self.sessions['decode'].get_inputs() if x.name.startswith('past_key_') or x.name.startswith('past_value_')]
   assert len(shapes)==24 and all(s==shapes[0] for s in shapes)
   assert shapes[0]==[1,320 if a.decode_backend=='cpu' else 512,12,64]
   return int(shapes[0][1])
  def _create_sessions(self):
   self._session_input_names={};self._model_display_names={};sessions={}
   spec=[('prefill','models/axmodels_650/tts_prefill.axmodel','AXCLRTExecutionProvider'),('local_fixed_sampled_frame','models/axmodels_650/tts_local_fixed_sampled_frame.axmodel','AXCLRTExecutionProvider'),('codec_decode','models/axmodels_650/codec_decode.axmodel','AXCLRTExecutionProvider')]
   spec.append(('decode','models/onnxmodels/moss_tts_decode_step.onnx','CPUExecutionProvider') if a.decode_backend=='cpu' else ('decode','models/axmodels_650/tts_decode_step.axmodel','AXCLRTExecutionProvider'))
   for key,name,backend in spec:
    s=TracedSession(a.model_dir/name,backend,self,key)
    if key=='decode' and int(s.get_outputs()[1].shape[1])==1:s=NewRowDecoderAdapter(s)
    sessions[key]=s;self._session_input_names[key]=[x.name for x in s.get_inputs()];self._model_display_names[key]=name+' ['+backend+']'
   return sessions
  def run_local_fixed_sampled_frame(self,*args,**kwargs):
   cont,frame=super().run_local_fixed_sampled_frame(*args,**kwargs);assert len(frame)==16 and all(0<=v<=1024 for v in frame);self.decisions.append({'continue':cont,'frame':frame});return cont,frame
  def generate_audio_frames(self,rows,on_frame=None):
   actual=len(rows['inputIds']);capacity=self._infer_global_kv_len();assert capacity is not None and actual+a.max_frames<=capacity,(actual,a.max_frames,capacity)
   start=len(self.decisions);frames=super().generate_audio_frames(rows,on_frame);decisions=self.decisions[start:]
   stop='model-end' if decisions and not decisions[-1]['continue'] else 'pad-frame-guard' if len(frames)<len(decisions) else 'frame-limit'
   self.chunks.append({'promptRows':actual,'capacity':capacity,'frames':len(frames),'stopReason':stop,'requestRows':rows,'decisions':decisions});return frames
 logging.basicConfig(level=logging.INFO);loaded=time.perf_counter();rt=Runtime();load_seconds=time.perf_counter()-loaded
 samples=[('custom',a.text,a.voice)] if a.text is not None else [('zh','你好，欢迎使用算力卡。','Junhao'),('en','Hello, welcome to the edge AI demo.','Ava'),('zh-repeat','你好，欢迎使用算力卡。','Junhao')]
 if a.first_only:samples=samples[:1]
 results=[]
 for name,text,voice in samples:
  rt.case_dir=a.output/name;rt.case_dir.mkdir();rt.calls=[];rt.decisions=[];rt.chunks=[];started=time.perf_counter()
  r=rt.synthesize(text=text,voice=voice,output_audio_path=rt.case_dir/'output.wav',sample_mode='fixed',do_sample=True,streaming=False,max_new_frames=a.max_frames,seed=42)
  wall=time.perf_counter()-started;waveform=r.pop('waveform');tokens=r.pop('audio_token_ids');assert waveform.size and len(tokens)>0 and np.isfinite(waveform).all()
  np.save(rt.case_dir/'waveform.npy',waveform);np.save(rt.case_dir/'tokens.npy',tokens)
  result={'name':name,'text':text,'voice':voice,'seed':42,'decodeBackend':a.decode_backend,'runtimeResult':r,'secondsIncludingTrace':wall,'frames':len(tokens),'duration':waveform.shape[0]/r['sample_rate'],'channels':waveform.shape[1],'clippedSamples':int((np.abs(waveform)>1).sum()),'chunks':rt.chunks,'calls':rt.calls}
  save_json(rt.case_dir/'result.json',result);results.append(result);print(json.dumps({'name':name,'frames':len(tokens),'duration':result['duration'],'stopReasons':[c['stopReason'] for c in rt.chunks]},ensure_ascii=False),flush=True)
 record={'completed':True,'modelId':manifest['modelId'],'revision':manifest['revision'],'provider':'AXCLRTExecutionProvider','decodeBackend':a.decode_backend,'loadSeconds':load_seconds,'results':results}
 save_json(a.output/'results.json',record)
 sessions=[]
 for key in rt.sessions:
  calls=[c for r in results for c in r['calls'] if c['network']==key];assert calls
  sessions.append({'network':key,'model':calls[0]['model'],'backend':calls[0]['backend'],'allFinite':True,'runMilliseconds':[c['milliseconds'] for c in calls]})
 save_json(a.output/'deployment-result.json',{**record,'sessions':sessions})

if __name__=='__main__':main()
