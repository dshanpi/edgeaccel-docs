"""Jina Omni Small on AXCL: four tasks, text/image/8-second audio, 256-token limit."""
import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
from jinja2.sandbox import ImmutableSandboxedEnvironment
from jina_small_media_core import SmallText,MID
from jina_small_native_session import configure

def image_pixels(path):
 from PIL import Image
 image=Image.open(path).convert('RGB').resize((256,256),Image.Resampling.BICUBIC)
 x=(np.asarray(image,dtype=np.float32)/np.float32(255)-np.float32(.5))/np.float32(.5)
 return np.ascontiguousarray(np.stack([x,x]).reshape(1,2,8,2,16,8,2,16,3).transpose(0,2,5,3,6,8,1,4,7).reshape(256,1536))

def encode_media(engine,path,kind,task,role):
 tag=task.replace('-','_');prefix='Query: ' if role=='query' else 'Document: '
 if kind=='image':
  x=image_pixels(path);raw=engine.load('jina_v5_omni_small_vision_tower_256x256.axmodel').run(None,{'pixel_values':x})[0]
  value=engine.load(f'jina_v5_omni_small_vision_merger_{tag}_256x256.axmodel').run(None,{'vision_raw_tokens':raw})[0]
  assert value.shape==(1,64,1024);placeholder=151655
  content=prefix+'<|vision_start|>'+'<|image_pad|>'*64+'<|vision_end|>'
 else:
  assert kind=='audio'
  import torch,soundfile as sf
  from transformers import WhisperFeatureExtractor
  torch.set_num_threads(1);samples,rate=sf.read(path,dtype='float32')
  if samples.ndim!=1 or rate!=16000 or not 0<len(samples)<=128000:raise ValueError('Audio must be 16kHz mono and no longer than 8 seconds.')
  inputs=WhisperFeatureExtractor(feature_size=128)(samples,sampling_rate=rate,padding='max_length',max_length=128000,return_tensors='np',return_attention_mask=True)
  x=np.ascontiguousarray(inputs['input_features'],dtype=np.float32);assert x.shape==(1,128,800)
  raw=engine.load('jina_v5_omni_small_audio_tower_800frames.axmodel').run(None,{'input_features':x})[0]
  value=engine.load(f'jina_v5_omni_small_audio_projector_{tag}_800frames.axmodel').run(None,{'audio_raw_tokens':raw})[0]
  assert value.shape==(1,200,1024);placeholder=151669
  content=prefix+'<|audio_start|>'+'<|audio_pad|>'*200+'<|audio_end|>'
 template=ImmutableSandboxedEnvironment().from_string((engine.root/'chat_template.jinja').read_text())
 prompt=template.render(messages=[{'role':'user','content':content}],add_generation_prompt=False)
 engine.encode(str(path.name),task,role,prepared_prompt=prompt,features=value,placeholder=placeholder)
 engine.calls[-1].update(inputFile=path.name,inputSha256=hashlib.sha256(path.read_bytes()).hexdigest(),preprocessedSha256=hashlib.sha256(x.tobytes()).hexdigest(),featureSha256=hashlib.sha256(value.tobytes()).hexdigest())

def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 requests=json.loads(a.inputs.read_text(encoding='utf-8'));assert isinstance(requests,list) and 1<=len(requests)<=32
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);configure(Path(__file__).with_name('jina-small-native-shapes.json'),out/'native-calls');engine=SmallText(a.model_dir.resolve())
 report={'modelId':MID,'revision':'3369e03364b29a2af7d1fd766d0e59f31b92d5b8','completed':False,'provider':'AXCLNativeAPI','calls':[]}
 save=lambda:(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 save()
 for i,r in enumerate(requests):
  start=time.monotonic();kind=r.get('modality','text');task=r.get('task','retrieval');role=r.get('role','query');assert task in engine.adapters and role in ['query','document']
  if kind=='text':engine.encode(r['text'],task,role)
  else:
   assert kind in ['image','audio'];path=Path(r['file']);path=path if path.is_absolute() else a.inputs.resolve().parent/path;assert path.is_file();encode_media(engine,path,kind,task,role)
  row=engine.calls[-1];row.update(id=r.get('id',str(i)),modality=kind,requestSeconds=time.monotonic()-start);report['calls'].append(row);save()
  print(json.dumps({'id':row['id'],'task':task,'tokens':row['tokenCount'],'dimensions':len(row['embedding']),'seconds':row['requestSeconds']}),flush=True)
 report['similarityMatrix']=[[float(np.dot(x['embedding'],y['embedding'])) for y in report['calls']] for x in report['calls']]
 report['completed']=True;save()
if __name__=='__main__':main()
