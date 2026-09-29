"""Run five fixed YOLO26-Depth variants serially on an AXCL M.2 card."""
import argparse,gc,hashlib,importlib.metadata,json,shutil,sys,time
from pathlib import Path
import cv2,numpy as np,axengine

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def desc(x):return {'shape':list(x.shape),'dtype':str(x.dtype),'sha256':hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()}
def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--variant',choices=['all','n','s','m','l','x'],default='all');p.add_argument('--image',type=Path);a=p.parse_args()
 root=a.model_dir.resolve();out=a.output.resolve();assert not out.exists();source=root/'infer_depth.py';assert sha(source)=='fc3fecb7093d77ccb49c6036fe8eccd4d0f8f56d3a7832818f3d394077ddda17'
 assert 'AXCLRTExecutionProvider' in axengine.get_available_providers();sys.path.insert(0,str(root));import infer_depth as official
 out.mkdir(parents=True);report={'modelId':'Yolo26-Depth','provider':'AXCLRTExecutionProvider','completed':False,'sourceSha256':sha(source),'versions':{'numpy':np.__version__,'opencv':cv2.__version__,'onnxruntime':importlib.metadata.version('onnxruntime')},'settings':{'variants':list('nsmlx') if a.variant=='all' else [a.variant],'postprocess':'default','colorMode':'disparity','percentiles':[2,98],'colorMap':'jet','overlayAlpha':.6,'depthUnits':'Model-predicted depth; not checked against measured ground truth.'},'sessions':[],'samples':[]}
 def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 stored={}
 def store(arrays):
  meta={k:desc(v) for k,v in arrays.items()};key=hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest();file=out/('raw-'+key+'.npz')
  if key not in stored:np.savez_compressed(file,**arrays);stored[key]=sha(file)
  return {'file':file.name,'sha256':stored[key],'arrays':meta}
 if a.image:jobs=[('custom',a.image.resolve())]
 else:
  blank=out/'blank.png';base=cv2.imread(str(root/'asserts/ssd_car.jpg'));assert base is not None;assert cv2.imwrite(str(blank),np.full_like(base,114))
  jobs=[('car',root/'asserts/ssd_car.jpg'),('bus',root/'asserts/bus.jpg'),('car-repeat',root/'asserts/ssd_car.jpg'),('blank',blank)]
 for variant in report['settings']['variants']:
  path=root/f'ax8850n/yolo26{variant}-depth_w8a8_mix.axmodel';t=time.perf_counter();engine=axengine.InferenceSession(str(path),providers=['AXCLRTExecutionProvider'])
  schema=lambda xs:[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in xs]
  session={'model':str(path.relative_to(root)),'variant':variant,'weightSha256':sha(path),'provider':engine.get_providers(),'loadSeconds':time.perf_counter()-t,'inputs':schema(engine.get_inputs()),'outputs':schema(engine.get_outputs()),'allFinite':True,'runMilliseconds':[],'calls':[]};report['sessions'].append(session);save()
  assert len(engine.get_inputs())==len(engine.get_outputs())==1 and list(engine.get_inputs()[0].shape)==[1,768,768,3] and str(engine.get_inputs()[0].dtype)=='uint8'
  inputname,size=official.model_input_size(engine,True);assert size==(768,768)
  for kind,imagepath in jobs:
   sample=variant+'-'+kind;destination=out/(kind+'-input'+imagepath.suffix)
   if not destination.exists():shutil.copy2(imagepath,destination)
   image=cv2.imread(str(imagepath));assert image is not None;t=time.perf_counter();tensor,pad=official.preprocess(image,size,True)
   start=time.perf_counter();output=engine.run(None,{inputname:tensor})[0];elapsed=(time.perf_counter()-start)*1000
   assert np.isfinite(output).all() and official.output_depth_map(output).shape==size
   evidence=store({'input':tensor,'output':output});session['calls'].append({'sample':sample,'raw':evidence});session['runMilliseconds'].append(elapsed)
   depth=official.restore_depth(output,image.shape[:2],pad);assert np.isfinite(depth).all();heat=official.colorize_depth(depth,'jet','disparity')
   depthpath,heatpath,overlaypath=official.save_results(Path(sample+'.jpg'),out,image,depth,heat,.6)
   valid=depth[depth>0];values=1/valid if valid.size else np.zeros(0);percentiles=np.percentile(values,[2,98]).tolist() if valid.size else [0.,1.]
   record={'variant':variant,'kind':kind,'input':destination.name,'inputSha256':sha(destination),'size':list(image.shape[:2]),'padding':list(pad),'depthFile':depthpath.name,'depthSha256':sha(depthpath),'heatmap':heatpath.name,'heatmapSha256':sha(heatpath),'overlay':overlaypath.name,'overlaySha256':sha(overlaypath),'depthStats':{'positiveFraction':float(np.mean(depth>0)),'min':float(valid.min()) if valid.size else None,'median':float(np.median(valid)) if valid.size else None,'max':float(valid.max()) if valid.size else None},'colorScaleInverseDepthPercentiles':percentiles,'processSeconds':time.perf_counter()-t}
   report['samples'].append(record);save();print(json.dumps({'variant':variant,'kind':kind,'axclMs':elapsed,'depth':record['depthStats']}),flush=True)
  del engine;gc.collect()
 report['completed']=True;save()
if __name__=='__main__':main()
