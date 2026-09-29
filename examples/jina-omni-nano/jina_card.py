"""Encode text, images and up-to-eight-second mono audio with Jina Omni Nano on an AXCL card."""
import os
os.environ['OMP_NUM_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,hashlib,json,time
from pathlib import Path
from math import gcd
import numpy as np
from PIL import Image
from jinja2.sandbox import ImmutableSandboxedEnvironment
from jina_omni_core import NanoText,BF
from jina_omni_audio import encode_features
from jina_native_bridge_session import configure

def image_features(path):
 image=Image.open(path).convert('RGB').resize((256,256),Image.Resampling.BICUBIC)
 array=(np.asarray(image,dtype=np.float32)/np.float32(255)-np.float32(.5))/np.float32(.5)
 return np.ascontiguousarray(np.stack([array,array]).reshape(1,2,8,2,16,8,2,16,3).transpose(0,2,5,3,6,8,1,4,7).reshape(256,1536))

def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 base=Path(__file__).resolve().parent;root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 requests=json.loads(a.inputs.read_text(encoding='utf-8'));assert isinstance(requests,list) and 1<=len(requests)<=32
 configure(base/'jina-native-shapes.json',out/'native-calls');engine=NanoText(root)
 template=ImmutableSandboxedEnvironment().from_string((root/'chat_template.jinja').read_text(encoding='utf-8'))
 manifest=json.loads((base/'special-tokens/manifest.json').read_text());engine.task_tokens={};engine.task_token_hashes={}
 for f in manifest['files']:
  path=base/'special-tokens'/f['file'];assert path.stat().st_size==6144 and hashlib.sha256(path.read_bytes()).hexdigest()==f['sha256']
  engine.task_tokens[f['task']]=np.fromfile(path,dtype=BF).reshape(4,768);engine.task_token_hashes[f['task']]=f['sha256']
 report={'modelId':'jina-embeddings-v5-omni-nano','revision':'6181fa78a78812dde065f76ad0f73425aec43747','provider':'AXCLNativeAPI','completed':False,'results':[]}
 save=lambda:(out/'embeddings.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 save();extractor=None
 for i,request in enumerate(requests):
  task=request.get('task','retrieval');kind=request.get('modality','text');role=request.get('role','document');start=time.monotonic()
  assert task in ['retrieval','clustering','classification','text-matching'] and role in ['query','document']
  if kind=='text':
   engine.encode(request['text'],task,role);result=engine.calls[-1]
  else:
   assert kind in ['image','audio'] and task in ['retrieval','clustering'] and role=='document'
   path=Path(request['file']);path=path if path.is_absolute() else a.inputs.resolve().parent/path
   if kind=='image':
    value=image_features(path)
    pipeline=[('jina_v5_omni_nano_vision_tower_256x256.axmodel','pixel_values'),(f'jina_v5_omni_nano_vision_merger_{task}_256x256.axmodel','vision_raw_tokens')]
   else:
    import soundfile as sf
    from scipy.signal import resample_poly
    if extractor is None:
     import torch
     torch.set_num_threads(1)
     from transformers import WhisperFeatureExtractor
     extractor=WhisperFeatureExtractor(feature_size=128)
    samples,rate=sf.read(path,dtype='float32');assert samples.ndim==1 and 0<len(samples)<=8*rate,'Audio must be mono and no longer than 8 seconds.'
    if rate!=16000:
     divisor=gcd(rate,16000);samples=resample_poly(samples,16000//divisor,rate//divisor).astype(np.float32)
    features=extractor(samples,sampling_rate=16000,padding='max_length',max_length=128000,return_tensors='np',return_attention_mask=True)
    value=np.ascontiguousarray(features['input_features'],dtype=np.float32);frames=int(features['attention_mask'].sum());count=(((frames-1)//2+1)-2)//2+1
    assert value.shape==(1,128,800) and 0<count<=200
    pipeline=[('jina_v5_omni_nano_audio_tower_8s.axmodel','input_features'),(f'jina_v5_omni_nano_audio_projector_{task}_8s.axmodel','audio_raw_tokens')]
   for model,key in pipeline:
    session=engine.load(model);value=session.run(None,{key:value})[0];session._sess._unload()
   if kind=='image':
    prompt=template.render(messages=[{'role':'user','content':'Document: <|vision_start|><image><|vision_end|>'}],add_generation_prompt=False)
    prompt=prompt.replace('<|vision_start|>','').replace('<|vision_end|>','').replace('<image>','<image>'*64)
    engine.encode(str(path),task,role,prepared_prompt=prompt,features=value);result=engine.calls[-1]
   else:
    value=value[:,:count,:].copy();prompt=template.render(messages=[{'role':'user','content':'Document: <|audio_start|>'+'<|audio_pad|>'*count+'<|audio_end|>'}],add_generation_prompt=False)
    result=encode_features(engine,prompt,value,task)
   result['inputFileSha256']=hashlib.sha256(path.read_bytes()).hexdigest()
  result.update(id=request.get('id',str(i)),modality=kind,request=request,totalSeconds=time.monotonic()-start)
  report['results'].append(result);save();print(json.dumps({'id':result['id'],'task':task,'modality':kind,'dimensions':len(result['embedding']),'tokens':result['tokenCount'],'seconds':result['totalSeconds']},ensure_ascii=False),flush=True)
 report['similarityMatrix']=[[float(np.dot(x['embedding'],y['embedding'])) if x['task']==y['task'] else None for y in report['results']] for x in report['results']]
 report['completed']=True;save()
if __name__=='__main__':main()
