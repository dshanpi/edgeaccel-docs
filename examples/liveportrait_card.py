"""Fixed AXERA LivePortrait human pipeline, AXCL + CPU, with real output evidence."""
import argparse,hashlib,importlib,importlib.metadata,json,os,pickle,shutil,sys,time,types
from pathlib import Path
import cv2,numpy as np,onnxruntime as ort,axengine,torch

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def desc(a):return {'shape':list(a.shape),'dtype':str(a.dtype),'sha256':hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()}

def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=['image','video'],default='image');p.add_argument('--source',type=Path);p.add_argument('--driving',type=Path);p.add_argument('--frames',type=int,default=8);p.add_argument('--stride',type=int,default=5);a=p.parse_args()
 root=a.model_dir.resolve();out=a.output.resolve();assert not out.exists();assert 1<=a.frames<=32 and 1<=a.stride<=30
 src=root/'python';assert sha(src/'infer.py')=='ab5332d17b5cdf96b07a66da1e2ac2e62281693ddfb713a8dd2d60e4e0e5b0e5';assert sha(src/'cropper.py')=='13b0db186331c25d519ca62ce5e10a9073c4fbca695835006df2aec180927168'
 out.mkdir(parents=True);torch.set_num_threads(2);torch.set_num_interop_threads(1);cv2.setNumThreads(1);os.environ['IMAGEIO_FFMPEG_EXE']='/usr/bin/ffmpeg'
 report={'modelId':'LivePortrait','revision':'c5664269a6b14012164c999fbaa01899713e5692','provider':'AXCLRTExecutionProvider','completed':False,'settings':{'mode':a.mode,'cpuThreads':2,'maxFrames':a.frames,'stride':a.stride,'humanOnly':True,'audio':False,'sourceSha256':sha(src/'infer.py')},'versions':{n:importlib.metadata.version(n) for n in ['numpy','torch','onnx','onnxruntime','imageio','imageio-ffmpeg']},'sessions':[],'samples':[]}
 report['versions']['opencv']=cv2.__version__
 active={'sample':'setup','frame':0};cache={}
 def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 def store(arrays):
  meta={k:desc(np.asarray(v)) for k,v in arrays.items()};key=hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest();f=out/('raw-'+key+'.npz')
  if key not in cache:np.savez_compressed(f,**arrays);cache[key]=sha(f)
  return {'file':f.name,'sha256':cache[key],'arrays':meta}
 def init_record(engine,path,provider,start):
  schema=lambda xs:[{'name':x.name,'shape':list(x.shape),'dtype':str(getattr(x,'dtype',getattr(x,'type','unknown')))} for x in xs]
  r={'model':str(Path(path).relative_to(root)),'weightSha256':sha(path),'provider':provider,'loadSeconds':time.perf_counter()-start,'inputs':schema(engine.get_inputs()),'outputs':schema(engine.get_outputs()),'allFinite':True,'runMilliseconds':[],'calls':[]};report['sessions'].append(r);save();return r
 def trace(r,names,feed,values,elapsed,raw=True):
  arrays={**{'input-'+k:np.asarray(v) for k,v in feed.items()},**{'output-'+k:np.asarray(v) for k,v in zip(names,values)}}
  finite=all(np.isfinite(v).all() for v in arrays.values());r['allFinite'] &= finite
  call={'sample':active['sample'],'milliseconds':elapsed,'arrays':{k:desc(v) for k,v in arrays.items()}}
  if raw:call['raw']=store(arrays)
  r['calls'].append(call);r['runMilliseconds'].append(elapsed);save();assert finite
 realort=ort.InferenceSession
 class CpuSession(realort):
  def __init__(self,path,*args,**kwargs):
   opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1;opts.enable_cpu_mem_arena=False
   kwargs.update(sess_options=opts,providers=['CPUExecutionProvider']);start=time.perf_counter();super().__init__(path,**kwargs);assert self.get_providers()==['CPUExecutionProvider'];self.evidence=init_record(self,path,self.get_providers(),start)
  def run(self,names,feed,*args,**kwargs):
   start=time.perf_counter();values=super().run(names,feed,*args,**kwargs);elapsed=(time.perf_counter()-start)*1000;trace(self.evidence,names or [x.name for x in self.get_outputs()],feed,values,elapsed,Path(self.evidence['model']).name=='warp.onnx');return values
 ort.InferenceSession=CpuSession
 class AxSession:
  def __init__(self,path,*args,**kwargs):
   start=time.perf_counter();self.engine=axengine.InferenceSession(path,providers=['AXCLRTExecutionProvider']);assert 'AXCLRTExecutionProvider' in self.engine.get_providers();self.evidence=init_record(self.engine,path,self.engine.get_providers(),start)
  def run(self,names,input_feed):
   start=time.perf_counter();values=self.engine.run(names,input_feed);elapsed=(time.perf_counter()-start)*1000;trace(self.evidence,names or [x.name for x in self.engine.get_outputs()],input_feed,values,elapsed);return values
  def __getattr__(self,k):return getattr(self.engine,k)
 # Keep original files unchanged. Remove only two author-specific debug writes.
 croptext=(src/'cropper.py').read_text(encoding='utf-8');removed=[l for l in croptext.splitlines() if 'cv2.imwrite("/data/tmp/yongqiang/' in l];assert len(removed)==2
 croptext='\n'.join(l for l in croptext.splitlines() if l not in removed)
 marker='            providers=self.face_analysis_wrapper_provider,';assert croptext.count(marker)==1
 croptext=croptext.replace(marker,marker+'\n            allowed_modules=["detection", "landmark_2d_106"],')
 # Upstream cropper uses log() on no-face inputs without importing it.
 croptext='from utils.rprint import rlog as log\n'+croptext
 report['adaptations']={'removedAuthorDebugWrites':removed,'allowedFaceModules':['detection','landmark_2d_106'],'addedMissingLogImport':True,'cpuSessionThreads':2,'audioDisabled':True};save()
 sys.path.insert(0,str(src));cropmod=types.ModuleType('cropper');cropmod.__file__=str(src/'cropper.py');sys.modules['cropper']=cropmod;exec(compile(croptext,cropmod.__file__,'exec'),cropmod.__dict__)
 import infer as official
 official.InferenceSession=AxSession
 class ArrayOnlyUnpickler(pickle.Unpickler):
  def find_class(self,module,name):
   allowed={('numpy.core.multiarray','_reconstruct'):np.core.multiarray._reconstruct,('numpy','ndarray'):np.ndarray,('numpy','dtype'):np.dtype}
   if (module,name) not in allowed:raise pickle.UnpicklingError('Unexpected pickle global')
   return allowed[(module,name)]
 def load_array(f):
  x=ArrayOnlyUnpickler(f).load();assert isinstance(x,np.ndarray) and x.shape==(1,21,3) and np.isfinite(x).all();return x
 official.pkl=types.SimpleNamespace(load=load_array)
 # No automatic downloads or unused identity/age/3D models.
 face_dir=src/'pretrained_weights/insightface/models/buffalo_l';assert sorted(p.name for p in face_dir.glob('*.onnx'))==['2d106det.onnx','det_10g.onnx']
 cropper=cropmod.Cropper();assert set(cropper.face_analysis_wrapper.models)=={'detection','landmark_2d_106'};official.Cropper=lambda:cropper
 # Check no-face handling before allocating card sessions.
 blank=np.full((512,512,3),114,dtype=np.uint8);report['blankFaceRejected']=cropper.crop_source_image(blank) is None;assert report['blankFaceRejected'];save()
 original_crop=cropper.crop_source_image
 def crop_image(img):
  x=original_crop(img)
  if x is not None:
   arrays={k:v for k,v in x.items() if isinstance(v,np.ndarray)};active['record']['sourceCrop']=store(arrays);save()
  return x
 cropper.crop_source_image=crop_image
 modelcache={};original_load=official.load_model
 def load_model(kind,path):
  if kind not in modelcache:modelcache[kind]=original_load(kind,path)
  return modelcache[kind]
 official.load_model=load_model
 official.has_audio_stream=lambda path:False
 original_parse=official.parse_output;original_paste=official.paste_back;original_mask=official.prepare_paste_back
 def save_rgb(name,img):
  file=out/name;assert cv2.imwrite(str(file),img[...,::-1]);return {'file':name,'sha256':sha(file),'pixels':desc(img)}
 def parse_output(value):
  x=original_parse(value);idx=len(active['record']['frames']);active['record']['frames'].append({'index':idx,'crop':save_rgb(active['sample']+f'-{idx:03}-crop.png',x[0])});save();return x
 def paste_back(img,M,original,mask):
  x=original_paste(img,M,original,mask);active['record']['frames'][-1]['pasteback']=save_rgb(active['sample']+f'-{len(active["record"]["frames"])-1:03}-pasteback.png',x);save();return x
 def prepare_mask(mask,M,dsize):
  active['record']['pastebackGeometry']=store({'mask':mask,'M':M});return original_mask(mask,M,dsize)
 official.parse_output=parse_output;official.paste_back=paste_back;official.prepare_paste_back=prepare_mask
 originals={k:getattr(official,k) for k in ['prepare_source','prepare_videos','load_video','get_fps']}
 def videos(imgs):
  active['record']['drivingFrames']=[save_rgb(active['sample']+f'-{i:03}-driving.png',x) for i,x in enumerate(imgs)];return originals['prepare_videos'](imgs)
 official.prepare_videos=videos
 def load_video(path,*args):
  cap=cv2.VideoCapture(path);fps=float(cap.get(cv2.CAP_PROP_FPS));assert fps>0;frames=[];indices=[];idx=0
  while len(frames)<a.frames:
   ok,bgr=cap.read()
   if not ok:break
   if idx%a.stride==0:frames.append(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB));indices.append(idx)
   idx+=1
  cap.release();assert frames;active['record']['videoSampling']={'sourceFps':fps,'indices':indices,'playbackFps':fps/a.stride};return frames
 official.load_video=load_video
 # Upstream casts get_fps to int. Save at the exact sampled rate in the writer.
 original_writer=official.images2video
 def images2video(images,wfp,**kwargs):
  kwargs['fps']=active['record']['videoSampling']['playbackFps'];original_writer(images,wfp,**kwargs)
 official.images2video=images2video
 assets=root/'assets/examples'
 if a.source or a.driving:
  assert a.source and a.driving;jobs=[('custom',a.source.resolve(),a.driving.resolve())]
 elif a.mode=='image':jobs=[('s0-d8',assets/'source/s0.jpg',assets/'driving/d8.jpg'),('s5-d8',assets/'source/s5.jpg',assets/'driving/d8.jpg'),('s0-d8-repeat',assets/'source/s0.jpg',assets/'driving/d8.jpg')]
 else:jobs=[('s0-d0-short',assets/'source/s0.jpg',assets/'driving/d0.mp4')]
 for name,source,driving in jobs:
  active.update(sample=name);sample={'id':name,'source':source.name,'sourceSha256':sha(source),'driving':driving.name,'drivingSha256':sha(driving),'frames':[]};report['samples'].append(sample);active['record']=sample
  for path in [source,driving]:
   dest=out/path.name
   if not dest.exists():shutil.copy2(path,dest)
  sample['sourceRgb']=save_rgb(name+'-source.png',official.preprocess(str(source))[0]);sampledir=out/name
  official.parse_args=lambda:types.SimpleNamespace(source=str(source),driving=str(driving),models=str(src/'axmodels'),output_dir=str(sampledir))
  start=time.perf_counter();official.main();sample['pipelineSecondsWithEvidence']=time.perf_counter()-start;sample['outputs']=[{'file':str(f.relative_to(out)),'sha256':sha(f)} for f in sorted(sampledir.iterdir())];save();print(json.dumps({'sample':name,'seconds':sample['pipelineSecondsWithEvidence'],'frames':len(sample['frames'])}),flush=True)
 report['completed']=True;save()

if __name__=='__main__':main()
