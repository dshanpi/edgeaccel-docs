"""Run fixed YOLOE-26n-Seg AXCL inference and the matching CPU post graph."""
import argparse,hashlib,importlib.metadata,json,shutil,sys,time
from pathlib import Path
from types import SimpleNamespace
import cv2
import numpy as np
import axengine
import onnxruntime as ort
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def desc(x):return {'shape':list(x.shape),'dtype':str(x.dtype),'sha256':hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()}
def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--image',type=Path);a=p.parse_args()
 root=a.model_dir.resolve();out=a.output.resolve();assert not out.exists()
 source=root/'src/infer/e2e_infer_axmodel.py';assert sha(source)=='abaf692886b64c1c1e3a4fb75c43e062ee3aed3f6ac8ff83cd26f2cc17ec671e'
 sys.path.insert(0,str(source.parent));import e2e_infer_axmodel as official
 assert 'AXCLRTExecutionProvider' in axengine.get_available_providers();out.mkdir(parents=True)
 report={'modelId':'yoloe-26n-seg','provider':'AXCLRTExecutionProvider','completed':False,'sourceSha256':sha(source),
  'versions':{**{k:importlib.metadata.version(k) for k in ['numpy','onnxruntime']},'opencv':cv2.__version__},
  'settings':{'displayThreshold':.25,'evaluationThreshold':.001,'iou':.45,'maskThreshold':.5,'classes':80,'warmup':0},'sessions':[],'auxiliarySessions':[],'samples':[]}
 def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 current={};stored={}
 def store(arrays):
  meta={k:desc(v) for k,v in arrays.items()};key=hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest();file=out/('raw-'+key+'.npz')
  if key not in stored:np.savez_compressed(file,**arrays);stored[key]=sha(file)
  return {'file':file.name,'sha256':stored[key],'arrays':meta}
 class Session:
  def __init__(self,path,provider):
   t=time.perf_counter()
   if provider=='AXCLRTExecutionProvider':self.engine=axengine.InferenceSession(str(path),providers=[provider])
   else:
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    self.engine=ort.InferenceSession(str(path),sess_options=options,providers=[provider])
   schema=lambda xs:[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype) if hasattr(x,'dtype') else x.type} for x in xs]
   self.rec={'model':str(path.relative_to(root)),'weightSha256':sha(path),'provider':self.engine.get_providers(),'loadSeconds':time.perf_counter()-t,'inputs':schema(self.get_inputs()),'outputs':schema(self.get_outputs()),'allFinite':True,'runMilliseconds':[],'calls':[]}
   report['sessions' if provider=='AXCLRTExecutionProvider' else 'auxiliarySessions'].append(self.rec);save()
  def get_inputs(self):return self.engine.get_inputs()
  def get_outputs(self):return self.engine.get_outputs()
  def run(self,names,feeds):
   for cfg in self.get_inputs():assert list(feeds[cfg.name].shape)==list(cfg.shape) and np.isfinite(feeds[cfg.name]).all()
   t=time.perf_counter();ys=self.engine.run(names,feeds);elapsed=(time.perf_counter()-t)*1000
   assert len(ys)==len(self.get_outputs()) and all(np.isfinite(v).all() for v in ys)
   arrays={**{'in_'+str(i):feeds[c.name] for i,c in enumerate(self.get_inputs())},**{'out_'+str(i):v for i,v in enumerate(ys)}}
   self.rec['calls'].append({**current,'raw':store(arrays)});self.rec['runMilliseconds'].append(elapsed);return ys
 ax=Session(root/'models/yoloe_26n_seg_m1.axmodel','AXCLRTExecutionProvider');post=Session(root/'models/4_m1_cut_yoloe-26n-seg_640_post.onnx','CPUExecutionProvider')
 assert list(ax.get_inputs()[0].shape)==[1,640,640,3] and str(ax.get_inputs()[0].dtype)=='uint8'
 for file in ['models/4_m1_cut_yoloe-26n-seg_640_post.onnx','models/4_m1_cut_yoloe-26n-seg_640_pulsar2.onnx','datasets/annotations_val2017/annotations/instances_val2017.json','datasets/yoloe-26n-seg_class_names.json']:
  if (root/file).exists():shutil.copy2(root/file,out/Path(file).name)
 names=json.loads((root/'datasets/yoloe-26n-seg_class_names.json').read_text(encoding='utf-8'));report['classNames']=names
 if a.image:jobs=[('custom',a.image.resolve())]
 else:
  files=sorted((root/'datasets/coco2017val_5000').glob('*.jpg'));assert len(files)==9
  jobs=[(f.stem,f) for f in files];jobs.append(('repeat',files[0]));blank=out/'blank-input.png';assert cv2.imwrite(str(blank),np.full_like(cv2.imread(str(files[0])),114));jobs.append(('blank',blank))
 args=SimpleNamespace(conf=.001,eval_score_threshold=.001,iou=.45,full_output=True,debug=False)
 for kind,path in jobs:
  current.update(sample=kind);image=cv2.imread(str(path));assert image is not None;dest=out/(kind+'-input'+path.suffix)
  if path!=dest:shutil.copy2(path,dest)
  t=time.perf_counter();output,proto,scale,pad,*times=official.run_one(ax,post,ax.get_inputs()[0],image,args)
  predictions,boxes,masks,*posttimes=official.finish_post(output,proto,image,scale,pad,args,False)
  masks=np.asarray(masks,dtype=bool).reshape(-1,*image.shape[:2]);raw=store({'predictions':predictions,'boxes':boxes,'masks':masks})
  keep=predictions[:,4]>=.25;result=out/(kind+'-segmentation.png');assert cv2.imwrite(str(result),official.draw_predictions(image,predictions[keep],boxes[keep],masks[keep],names))
  detections=[{'classId':int(row[5]),'label':names[str(int(row[5]))],'score':float(row[4]),'box':box.tolist(),'maskPixels':int(mask.sum())} for row,box,mask in zip(predictions[keep],boxes[keep],masks[keep])]
  record={'kind':kind,'input':dest.name,'inputSha256':sha(dest),'size':list(image.shape[:2]),'scale':scale,'pad':list(pad),'evaluationDetections':len(predictions),'displayDetections':detections,'result':result.name,'resultSha256':sha(result),'rawResult':raw,'processSeconds':time.perf_counter()-t,'stagesMilliseconds':dict(zip(['preprocess','npuWithEvidence','cpuGraphWithEvidence','boxPostprocess','maskDecode'],times+posttimes))}
  report['samples'].append(record);save();print(json.dumps({'sample':kind,'displayDetections':len(detections),'evaluationDetections':len(predictions),'seconds':record['processSeconds']}),flush=True)
 report['completed']=True;save()
if __name__=='__main__':main()
