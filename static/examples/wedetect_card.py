"""Fixed WeDetect image/text pipeline on an explicit AXCL M.2 provider."""
import argparse,hashlib,importlib.metadata,json,shutil,sys,time
from pathlib import Path
import numpy as np
import axengine
from PIL import Image
from transformers import AutoTokenizer

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def desc(x):return {'shape':list(x.shape),'dtype':str(x.dtype),'sha256':hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()}
def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--image',type=Path);p.add_argument('--text',default='鞋,床,人,衣架');a=p.parse_args()
 root=a.model_dir.resolve();out=a.output.resolve();assert not out.exists()
 source=root/'axmodel_infer.py';assert sha(source)=='71aaf525eacd98abcbf9490e5f2868df6537777b92b0e88ef11da496f97c4c2b'
 assert 'AXCLRTExecutionProvider' in axengine.get_available_providers();sys.path.insert(0,str(root));import axmodel_infer as official
 out.mkdir(parents=True);report={'modelId':'WeDetect.axera','provider':'AXCLRTExecutionProvider','completed':False,
  'sourceSha256':sha(source),'versions':{k:importlib.metadata.version(k) for k in ['numpy','Pillow','transformers','tokenizers']},
  'settings':{'scoreThreshold':.3,'nmsIoU':.7,'classAgnosticNms':True,'maxDets':300,'classCount':4,'maxSeqLen':32},'sessions':[],'samples':[]}
 def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 current={}
 class Session:
  def __init__(self,name):
   path=root/'axmodel'/name;t=time.perf_counter();self.engine=axengine.InferenceSession(str(path),providers=['AXCLRTExecutionProvider'])
   schema=lambda xs:[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in xs]
   self.rec={'model':str(path.relative_to(root)),'weightSha256':sha(path),'provider':self.engine.get_providers(),'loadSeconds':time.perf_counter()-t,'inputs':schema(self.engine.get_inputs()),'outputs':schema(self.engine.get_outputs()),'allFinite':True,'runMilliseconds':[],'calls':[]};report['sessions'].append(self.rec);save()
  def run(self,feeds):
   for cfg in self.engine.get_inputs():assert list(feeds[cfg.name].shape)==list(cfg.shape) and str(feeds[cfg.name].dtype)==str(cfg.dtype) and np.isfinite(feeds[cfg.name]).all(),cfg.name
   t=time.perf_counter();ys=self.engine.run(None,feeds);elapsed=(time.perf_counter()-t)*1000
   assert len(ys)==len(self.engine.get_outputs()) and all(np.isfinite(x).all() for x in ys)
   arrays={**{'in_'+str(i):feeds[c.name] for i,c in enumerate(self.engine.get_inputs())},**{'out_'+str(i):v for i,v in enumerate(ys)}}
   meta={k:desc(v) for k,v in arrays.items()};key=hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest();file=out/('raw-'+key+'.npz')
   if not file.exists():np.savez_compressed(file,**arrays)
   self.rec['calls'].append({**current,'raw':file.name,'rawSha256':sha(file),'arrays':meta});self.rec['runMilliseconds'].append(elapsed);return ys
 tokenizer=AutoTokenizer.from_pretrained(str(root/'xlm-roberta-base'),local_files_only=True,trust_remote_code=False,use_fast=True)
 report['tokenizerClass']=type(tokenizer).__name__;report['tokenizerHashes']={p.name:sha(p) for p in (root/'xlm-roberta-base').iterdir() if p.is_file()}
 image_session=Session('wedetect_image_encoder_npu3_u16.axmodel');text_session=Session('wedetect_text_encoder_npu3_u16.axmodel')
 labels=[s.strip() for s in a.text.split(',')];assert len(labels)==4 and all(labels)
 image=(a.image or root/'assets/demo.jpeg').resolve()
 jobs=[('custom',image,labels)] if a.image else [('official',image,labels),('reordered',image,list(reversed(labels))),('repeat',image,labels)]
 if not a.image:
  blank=out/'blank-input.png'
  with Image.open(image) as im:Image.new('RGB',im.size,(114,114,114)).save(blank)
  jobs.append(('blank',blank,labels))
 for kind,path,texts in jobs:
  current.update(sample=kind);destination=out/(kind+'-input'+path.suffix)
  if destination!=path:shutil.copy2(path,destination)
  t=time.perf_counter();ids,mask=official.tokenize(texts,tokenizer,32);assert ids.shape==mask.shape==(4,32),'Use four short class names; each must fit 32 tokens'
  text_features=text_session.run({'input_ids':ids.astype(np.int32),'attention_mask':mask.astype(np.int32)})[0]
  image_tensor,ratio,(left,top)=official.preprocess_image(str(path),640)
  output=image_session.run({'images':image_tensor,'text_features':text_features.astype(np.float32)})
  assert len(output)==6
  boxes=[];scores=[];classes=[]
  for i,(side,stride) in enumerate([(80,8),(40,16),(20,32)]):
   b,s,_=official._decode_bboxes(output[2*i],output[2*i+1],side,side,stride,.3)
   if len(b):boxes.append(b);scores.append(s.max(1));classes.append(s.argmax(1))
  with Image.open(path) as im:size=im.size
  if boxes:
   boxes=np.concatenate(boxes);scores=np.concatenate(scores);classes=np.concatenate(classes)
   keep=official.nms(boxes,scores,.7,300);boxes=boxes[keep];scores=scores[keep];classes=classes[keep]
   boxes[:,[0,2]]-=left;boxes[:,[1,3]]-=top;boxes/=ratio;boxes[:,0::2]=np.clip(boxes[:,0::2],0,size[0]);boxes[:,1::2]=np.clip(boxes[:,1::2],0,size[1])
  else:boxes=np.empty((0,4));scores=np.empty(0);classes=np.empty(0,dtype=np.int64)
  result=out/(kind+'-detections.png');official.draw_boxes(str(path),boxes,[texts[c] for c in classes],scores,str(result),str(root/'wqy-microhei.ttc'))
  sample={'kind':kind,'input':destination.name,'inputSha256':sha(destination),'size':list(size),'labels':texts,'inputIds':ids.tolist(),'attentionMask':mask.tolist(),'ratio':ratio,'padding':[left,top],'detections':[{'label':texts[c],'classIndex':int(c),'score':float(s),'box':b.tolist()} for b,s,c in zip(boxes,scores,classes)],'image':result.name,'imageSha256':sha(result),'processSeconds':time.perf_counter()-t}
  report['samples'].append(sample);save();print(json.dumps(sample,ensure_ascii=False),flush=True)
 report['completed']=True;save()
if __name__=='__main__':main()
