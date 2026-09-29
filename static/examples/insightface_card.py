"""Exercise all five fixed Insightface buffalo_l models on a fictional fixture."""
import argparse,gc,hashlib,importlib,io,json,pickle,re,shutil,sys,time,types
from pathlib import Path
import axengine
import cv2
import numpy as np
import skimage

SOURCE_HASHES={
 'insightface/model_zoo/retinaface.py':'23b4f2fa9e4f6cc359429d7d97e9bd725aa0fba70b0ebf9dc6acb1a85ef56e73',
 'insightface/model_zoo/landmark.py':'02dc0b19834ad07d75f434370731a9016dafa7fd486cdec897df3c2cfeae11ac',
 'insightface/model_zoo/attribute.py':'ab889bba9d68930ac48336fb24d6d9c6b7397b0e9a2cb6e1e2223ae3edc4cbd3',
 'insightface/model_zoo/arcface_onnx.py':'71ac61d5d585f53d4e6a651eb89fa9871100bf1ec5e3fdec255b6192719fea8c',
 'insightface/utils/face_align.py':'a8b34ddd06716f5ca7e7501415cbd3789ccbce18db9e557b35e537695290d922',
 'insightface/utils/transform.py':'50a42236e1041d3c3788cb9b60ed3f018dca88de2d1253333cef0aa1ca86ef07',
 'insightface/app/common.py':'eee1b5cf2f2de795b1dc65ddc01538d2befd41d5e46355affc5c50bb0d744a89'}
MEAN_SHA='39ffecf84ba73f0d0d7e49380833ba88713c9fcdec51df4f7ac45a48b8f4cc51'
FIXTURE_SHA='16c9acc754c595d92be86b2ea452f603b92d952ad068fc24265406636640b7d4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()

def memory():
 value=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])
 assert value>512*1024,'Host MemAvailable below 512 MiB'
 return value

class ArrayUnpickler(pickle.Unpickler):
 def find_class(self,module,name):
  allowed={('numpy.core.multiarray','_reconstruct'):np.core.multiarray._reconstruct,
           ('numpy','ndarray'):np.ndarray,('numpy','dtype'):np.dtype}
  if (module,name) not in allowed:raise pickle.UnpicklingError('Unexpected pickle global')
  return allowed[(module,name)]

def json_value(v):
 if isinstance(v,np.ndarray):return v.tolist()
 if isinstance(v,np.generic):return v.item()
 raise TypeError(type(v).__name__)

def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True)
 p.add_argument('--image',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();root,out=a.model_dir.resolve(),a.output.resolve()
 assert not out.exists(),'Choose a new output directory'
 for name,value in SOURCE_HASHES.items():assert sha(root/name)==value, name
 assert sha(a.image)==FIXTURE_SHA,'This reference test uses the supplied fictional-people.png fixture'
 mean_path=root/'insightface/data/objects/meanshape_68.pkl';assert sha(mean_path)==MEAN_SHA
 mean=ArrayUnpickler(io.BytesIO(mean_path.read_bytes())).load()
 assert isinstance(mean,np.ndarray) and mean.shape==(68,3) and mean.dtype.kind=='f' and np.isfinite(mean).all()
 assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
 # Import only the fixed model and geometry modules, bypassing the optional SDK
 # application registry. No changes to their preprocessing/postprocessing code.
 for suffix,relative in [('', 'insightface'),('.model_zoo','insightface/model_zoo'),('.utils','insightface/utils'),('.app','insightface/app'),('.data','insightface/data')]:
  pkg=types.ModuleType('_card_insightface'+suffix);pkg.__path__=[str(root/relative)];sys.modules[pkg.__name__]=pkg
 def get_object(name):
  assert name=='meanshape_68.pkl';return mean.copy()
 sys.modules['_card_insightface.data'].get_object=get_object
 Face=importlib.import_module('_card_insightface.app.common').Face
 classes={name:getattr(importlib.import_module('_card_insightface.model_zoo.'+module),name)
          for name,module in [('RetinaFace','retinaface'),('Landmark','landmark'),('Attribute','attribute'),('ArcFaceONNX','arcface_onnx')]}
 cv2.setNumThreads(4)
 image=cv2.imread(str(a.image));assert image is not None and image.shape==(1024,1536,3)
 out.mkdir(parents=True);shutil.copy2(a.image,out/'input.png');np.save(out/'mean-shape.npy',mean,allow_pickle=False)
 report={'modelId':'Insightface','provider':'AXCLRTExecutionProvider','completed':False,'sourceHashes':SOURCE_HASHES,
  'inputSha256':sha(a.image),'meanShapePickleSha256':MEAN_SHA,'syntheticInput':True,
  'versions':{'numpy':np.__version__,'opencv':cv2.__version__,'scikitImage':skimage.__version__},
  'settings':{'detectionThreshold':0.5,'nmsThreshold':0.4,'opencvThreads':4,'faceOrder':'left-to-right',
              'attributeGroundTruth':False,'identityRecognitionPerformed':False},'sessions':[],'samples':[]}
 def save(): (out/'deployment-result.json').write_text(json.dumps(report,default=json_value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 current={'sample':'','faceIndex':None}
 class Session:
  def __init__(self,name):
   memory();path=root/'models/buffalo_l'/name;t=time.perf_counter()
   self.engine=axengine.InferenceSession(str(path),providers=['AXCLRTExecutionProvider'])
   def schema(xs):return [{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in xs]
   self.rec={'model':'models/buffalo_l/'+name,'weightSha256':sha(path),'loadSeconds':time.perf_counter()-t,
    'provider':self.engine.get_providers(),'inputs':schema(self.engine.get_inputs()),'outputs':schema(self.engine.get_outputs()),
    'allFinite':True,'runMilliseconds':[],'calls':[]}
   report['sessions'].append(self.rec);save()
  def get_inputs(self):return self.engine.get_inputs()
  def get_outputs(self):return self.engine.get_outputs()
  def run(self,names,feeds):
   memory();assert len(feeds)==1
   x=next(iter(feeds.values()));cfg=self.get_inputs()[0]
   assert list(x.shape)==list(cfg.shape) and x.dtype==np.uint8 and np.isfinite(x).all()
   t=time.perf_counter();ys=self.engine.run(names,feeds);ms=(time.perf_counter()-t)*1000
   assert len(ys)==len(self.get_outputs()) and all(np.isfinite(y).all() for y in ys)
   for y,cfg in zip(ys,self.get_outputs()):assert list(y.shape)==list(cfg.shape)
   name=Path(self.rec['model']).stem+f'-{len(self.rec["calls"])+1:02d}.npz'
   np.savez_compressed(out/name,input=x,**{'output'+str(i):y for i,y in enumerate(ys)})
   row={**current,'rawFile':name,'rawSha256':sha(out/name),'inputHash':digest(x),'outputHashes':[digest(y) for y in ys]}
   self.rec['calls'].append(row);self.rec['runMilliseconds'].append(ms);save()
   return [y.copy() for y in ys] # Landmark modifies its output in place.
 jobs=[('original',image),('repeat',image.copy()),('blank',np.zeros_like(image))]
 faces_by_sample={}
 session=Session('det_10g.axmodel');model=classes['RetinaFace'](str(root/session.rec['model']),session=session)
 model.prepare(0,det_thresh=.5,nms_thresh=.4)
 for kind,img in jobs:
  current.update(sample=kind,faceIndex=None);before=memory();t=time.perf_counter();boxes,kps=model.detect(img)
  order=np.argsort(boxes[:,0]);boxes,kps=boxes[order],kps[order]
  assert np.isfinite(boxes).all() and np.isfinite(kps).all() and len(boxes)<=10
  faces=[Face(bbox=b[:4].copy(),det_score=b[4],kps=k.copy()) for b,k in zip(boxes,kps)]
  faces_by_sample[kind]=faces
  report['samples'].append({'kind':kind,'faceCount':len(faces),'faces':faces,'stageSeconds':{'detection':time.perf_counter()-t},
                           'availableBeforeKiB':before,'availableAfterKiB':memory()});save()
 del model,session;gc.collect()
 assert len(faces_by_sample['original'])>0,'No faces detected in fixture'
 for name,cls in [('2d106det.axmodel','Landmark'),('1k3d68.axmodel','Landmark'),('genderage.axmodel','Attribute'),('w600k_r50.axmodel','ArcFaceONNX')]:
  session=Session(name);model=classes[cls](str(root/session.rec['model']),session=session)
  model.prepare(0)
  for (kind,img),sample in zip(jobs,report['samples']):
   t=time.perf_counter()
   for i,face in enumerate(faces_by_sample[kind]):
    current.update(sample=kind,faceIndex=i);model.get(img,face)
    for value in face.values():assert np.isfinite(value).all()
   sample['stageSeconds'][name]=time.perf_counter()-t;save()
  del model,session;gc.collect()
 embeddings=[f.embedding for f in faces_by_sample['original']]
 report['cosineMatrix']=[[float(np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y))) for y in embeddings] for x in embeddings]
 assert np.isfinite(report['cosineMatrix']).all()
 report['completed']=True;save();print(json.dumps({'faces':[s['faceCount'] for s in report['samples']],
  'calls':{Path(s['model']).name:len(s['calls']) for s in report['sessions']},'cosineMatrix':report['cosineMatrix']}),flush=True)

if __name__=='__main__':main()
