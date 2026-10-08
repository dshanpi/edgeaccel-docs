import hashlib,json,time
from pathlib import Path
import numpy as np
from jina_omni_core import BF

digest=lambda x:hashlib.sha256(x.tobytes()).hexdigest()
def fresh(e):
 for s in e.sessions+[e.post]:s._sess._unload()
 e.loaded=[]
 e.sessions=[e.load(f'jina_embeddings_v5_omni_p128_l{i}_together.axmodel') for i in range(12)]
 e.post=e.load('jina_embeddings_v5_omni_post.axmodel')

def encode_features(e,prompt,features,task):
 ids=e.tokenizer.encode(prompt,add_special_tokens=True).ids
 assert ids[-1]==128001 and ids.count(128001)==1 and 0<len(ids)<=256
 positions=[i for i,x in enumerate(ids) if x==128256]
 assert 0<len(positions)<=200 and features.shape==(1,len(positions),768)
 all_hidden=np.asarray(e.embedding[ids]).copy()
 for i,token in enumerate(ids):
  if token in [128256,128257,128258,128259]:all_hidden[i]=e.task_tokens[task][token-128256]
 all_hidden[positions]=features[0].astype(BF)
 caches={};chunks=[]
 for chunk,offset in enumerate(range(0,len(ids),128)):
  fresh(e);valid=min(128,len(ids)-offset);group=chunk+1
  hidden=np.zeros((1,128,768),dtype=BF);hidden[0,:valid]=all_hidden[offset:offset+valid]
  mask=np.full((1,128,128+offset),-65536,dtype=BF)
  mask[0,:valid,:offset+valid]=0
  indices=np.zeros((1,128),dtype=np.uint32);indices[0,:valid]=np.arange(offset,offset+valid,dtype=np.uint32)
  rows=[]
  for i,s in enumerate(e.sessions):
   k,v=caches[i] if chunk else (np.zeros((1,1,768),dtype=BF),np.zeros((1,1,768),dtype=BF))
   feed={'K_cache':k,'V_cache':v,'indices':indices,'input':hidden,'mask':mask,**e.adapters[task][i]}
   started=time.monotonic();values=s.run(None,feed,shape_group=group)
   outputs=dict(zip([n.name for n in s.get_outputs(group)],values))
   row={'layer':i,'shapeGroup':group,'seconds':time.monotonic()-started,'inputCacheShape':list(k.shape),'inputKSha256':digest(k),'inputVSha256':digest(v),'outputKSha256':digest(outputs['K_cache_out']),'outputVSha256':digest(outputs['V_cache_out'])}
   if not chunk:
    caches[i]=(np.ascontiguousarray(outputs['K_cache_out']),np.ascontiguousarray(outputs['V_cache_out']))
    assert caches[i][0].shape==caches[i][1].shape==(1,128,768)
   hidden=np.ascontiguousarray(outputs['output']);assert np.isfinite(hidden[0,:valid].astype(np.float32)).all()
   rows.append(row)
  chunks.append({'index':chunk,'offset':offset,'validTokens':valid,'loadedModels':list(e.loaded),'layers':rows})
 values=e.post.run(None,{'input':np.ascontiguousarray(hidden[:,valid-1:valid,:])})
 raw=dict(zip([n.name for n in e.post.get_outputs()],values))['output_norm'].reshape(768).astype(np.float32)
 assert np.isfinite(raw).all();raw_norm=float(np.linalg.norm(raw));assert raw_norm>1e-8
 vector=raw/raw_norm
 return {'task':task,'taskTokensSha256':e.task_token_hashes[task],'specialTokenIdsApplied':[128256,128257,128258,128259],'inputType':'document','prompt':prompt,'tokenIds':ids,'tokenCount':len(ids),'featureTokens':len(positions),'chunks':chunks,'rawNorm':raw_norm,'normalizedNorm':float(np.linalg.norm(vector)),'embedding':vector.tolist(),'embeddingSha256':digest(vector),'postOutput':'output_norm','freshModelsPerChunk':True}
