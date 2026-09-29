"""Fixed Jina Nano Retrieval: serial native AXCL embeddings with explicit chunking."""
import hashlib,json,time
from pathlib import Path
import numpy as np
from ml_dtypes import bfloat16 as BF
from tokenizers import Tokenizer
from jinja2.sandbox import ImmutableSandboxedEnvironment
import jina_retrieval_native_session as native

MID='jina-embeddings-v5-omni-nano-retrieval'
REV='6a92e331bd8813a98e2eac602b6f9412a7eec709'
digest=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()

class Retrieval:
 def __init__(self,root):
  self.root=Path(root);tokenizer_dir=self.root/'jina_v5_omni_tokenizer'
  self.tokenizer=Tokenizer.from_file(str(tokenizer_dir/'tokenizer.json'))
  self.tokenizer.no_truncation()
  self.tokenizer.no_padding()
  assert self.tokenizer.token_to_id('<|end_of_text|>')==128001
  assert self.tokenizer.token_to_id('<image>')==128259
  self.template=ImmutableSandboxedEnvironment().from_string((tokenizer_dir/'chat_template.jinja').read_text(encoding='utf-8'))
  self.embedding=np.memmap(self.root/'model.embed_tokens.weight.bfloat16.bin',dtype=BF,mode='r',shape=(128260,768))
  self.calls=[]
 def load(self,name):return native.InferenceSession(self.root/name,providers=['AXCLNativeAPI'])
 def encode(self,prompt,features=None,placeholder=128259):
  started=time.monotonic();ids=self.tokenizer.encode(prompt,add_special_tokens=True).ids
  assert ids[-1]==128001 and ids.count(128001)==1
  assert 0<len(ids)<=1024,'This fixed package provides eight 128-token prefill groups.'
  data=np.asarray(self.embedding[ids],dtype=BF).copy()
  if features is not None:
   positions=[i for i,t in enumerate(ids) if t==placeholder];feature_array=np.asarray(features,dtype=np.float32).reshape(-1,768)
   assert len(positions)==len(feature_array)
   data[positions]=feature_array.astype(BF)
  caches=[(np.zeros((1,1024,768),dtype=BF),np.zeros((1,1024,768),dtype=BF)) for _ in range(12)]
  chunks=[]
  for chunk,offset in enumerate(range(0,len(ids),128)):
   valid=min(128,len(ids)-offset);group=chunk+1
   hidden=np.zeros((1,128,768),dtype=BF);hidden[0,:valid]=data[offset:offset+valid]
   mask=np.full((1,128,offset+128),-65536,dtype=BF);mask[:,:valid,:offset+valid]=0
   indices=np.arange(offset,offset+128,dtype=np.uint32)[None,:]
   details=[]
   for layer in range(12):
    session=self.load(f'llama_p128_l{layer}_together.axmodel')
    kc,vc=caches[layer]
    k=np.ascontiguousarray(kc[:,:offset]) if offset else np.zeros((1,1,768),dtype=BF)
    v=np.ascontiguousarray(vc[:,:offset]) if offset else np.zeros((1,1,768),dtype=BF)
    feed={'K_cache':k,'V_cache':v,'indices':indices,'input':hidden,'mask':mask}
    names=[n.name for n in session.get_outputs(group)]
    outputs=dict(zip(names,session.run(None,feed,shape_group=group)))
    ko,vo=outputs['K_cache_out'],outputs['V_cache_out'];hidden=outputs['output']
    kc[:,offset:offset+valid]=ko[:,:valid];vc[:,offset:offset+valid]=vo[:,:valid]
    details.append({'layer':layer,'inputKSha256':digest(k),'inputVSha256':digest(v),'outputKSha256':digest(ko),'outputVSha256':digest(vo)})
   chunks.append({'group':group,'offset':offset,'validTokens':valid,'layers':details})
  post=self.load('llama_post.axmodel');names=[n.name for n in post.get_outputs()]
  values=dict(zip(names,post.run(None,{'input':np.ascontiguousarray(hidden[:,valid-1:valid,:])})))
  vector=values['output_norm'].astype(np.float32).reshape(768);norm=float(np.linalg.norm(vector));assert norm>0 and np.isfinite(vector).all()
  vector=vector/norm
  result={'prompt':prompt,'tokenIds':ids,'tokenCount':len(ids),'chunks':chunks,'rawNorm':norm,'normalizedNorm':float(np.linalg.norm(vector)),'embedding':vector.tolist(),'embeddingSha256':digest(vector),'seconds':time.monotonic()-started,'providerActual':'AXCLNativeAPI'}
  self.calls.append(result);return result
 def text(self,text,role):
  assert role in ['query','document'];r=self.encode(('Query: ' if role=='query' else 'Document: ')+text);r.update(modality='text',text=text,role=role);return r
 def media_prompt(self,modality,count,role):
  assert role in ['query','document'];prefix='Query: ' if role=='query' else 'Document: '
  content=prefix+('<|audio_start|>'+'<|audio_pad|>'*count+'<|audio_end|>' if modality=='audio' else '<|vision_start|>'+'<image>'*count+'<|vision_end|>')
  prompt=self.template.render(messages=[{'role':'user','content':content}],add_generation_prompt=False)
  return prompt.replace('<|vision_start|>','').replace('<|vision_end|>','')

def image_pixels(path):
 from PIL import Image
 image=Image.open(path).convert('RGB').resize((256,256),Image.Resampling.BICUBIC)
 a=(np.asarray(image,dtype=np.float32)/np.float32(255)-np.float32(.5))/np.float32(.5)
 return np.ascontiguousarray(np.stack([a,a]).reshape(1,2,8,2,16,8,2,16,3).transpose(0,2,5,3,6,8,1,4,7).reshape(256,1536))

def media(engine,paths,modality,role='query',audio_seconds=8):
 started=time.monotonic();rows=[];features=[]
 if modality in ['image','video']:
  assert len(paths)==1 if modality=='image' else len(paths)>0
  for path in paths:
   x=image_pixels(path);s=engine.load('jina_v5_omni_nano_vision_256x256.axmodel');f=s.run(None,{'pixel_values':x})[0];assert f.shape==(1,64,768)
   features.append(f);rows.append({'file':Path(path).name,'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'preprocessedSha256':digest(x)})
  value=np.concatenate(features,axis=1);placeholder=128259
 else:
  assert modality=='audio' and len(paths)==1 and audio_seconds in [8,30]
  import torch,soundfile as sf
  from transformers import WhisperFeatureExtractor
  torch.set_num_threads(1);samples,rate=sf.read(paths[0],dtype='float32');assert samples.ndim==1 and rate==16000 and 0<len(samples)<=audio_seconds*rate
  extractor=WhisperFeatureExtractor(feature_size=128)
  v=extractor(samples,sampling_rate=rate,padding='max_length',max_length=audio_seconds*rate,return_tensors='np',return_attention_mask=True)
  x=np.ascontiguousarray(v['input_features'],dtype=np.float32);assert x.shape==(1,128,audio_seconds*100)
  s=engine.load(f'jina_v5_omni_nano_audio_{audio_seconds}s.axmodel');value=s.run(None,{'input_features':x})[0]
  assert value.shape==(1,audio_seconds*25,768);placeholder=engine.tokenizer.token_to_id('<|audio_pad|>')
  assert placeholder==128256
  rows.append({'file':Path(paths[0]).name,'sha256':hashlib.sha256(Path(paths[0]).read_bytes()).hexdigest(),'preprocessedSha256':digest(x),'sampleRate':rate,'samples':len(samples),'realMelFrames':int(v['attention_mask'].sum()),'compiledMelFrames':audio_seconds*100})
 prompt=engine.media_prompt(modality,value.shape[1],role);r=engine.encode(prompt,value,placeholder)
 r.update(modality=modality,role=role,inputs=rows,featureTokens=value.shape[1],totalSeconds=time.monotonic()-started)
 return r
