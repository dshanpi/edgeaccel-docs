"""AXCL SigLIP encoder cosine matching with fixed local preprocessing."""
import argparse,hashlib,json,os,time
from pathlib import Path
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
import axengine
import numpy as np
import torch
from PIL import Image
from transformers import AutoProcessor

p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True)
p.add_argument('--output',type=Path,required=True);p.add_argument('--image',type=Path)
p.add_argument('--text',action='append');a=p.parse_args()
root,out=a.model_dir.resolve(),a.output.resolve()
assert not out.exists(),'Choose a new output directory'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
source=root/'python/inference_axmodel.py'
assert sha(source)=='e9279f26dcdb3ed390fb7e82dee136200d5234bb46cbcbd684bc20f6f867d2ac'
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
torch.set_num_threads(2)
texts=a.text or ['a photo of 2 cats','a photo of 2 dogs','Two cats resting on a pink couch.',
                 'A red car parked on a city street.','A sunset over the beach.','A plate of fresh vegetables.']
processor=AutoProcessor.from_pretrained(root/'tokenizer',local_files_only=True,trust_remote_code=False)
limit=processor.tokenizer.model_max_length
for text in texts:
    assert len(processor.tokenizer(text)['input_ids'])<=limit,'Shorten text to fit the model context'
image_path=(a.image or root/'000000039769.jpg').resolve()
img=Image.open(image_path).convert('RGB')
inputs=processor(text=texts,images=img,padding='max_length',return_tensors='pt')
out.mkdir(parents=True);img.save(out/'input.png')
r={'modelId':'siglip-so400m-patch14-384','provider':'AXCLRTExecutionProvider','completed':False,
   'sourceSha256':sha(source),'inputImageSha256':sha(image_path),'savedImageSha256':sha(out/'input.png'),
   'texts':texts,'textContext':limit,'embeddingDimensions':1152,'scoreType':'normalized vector cosine; no random sigmoid head',
   'processorFiles':{str(f.relative_to(root)):sha(f) for f in (root/'tokenizer').iterdir() if f.is_file()},
   'sessions':[]}
raw={}
def run(kind,weight,feeds):
    t=time.perf_counter();sess=axengine.InferenceSession(str(root/weight),providers=['AXCLRTExecutionProvider'])
    record={'model':weight,'weightSha256':sha(root/weight),'loadSeconds':time.perf_counter()-t,
            'allFinite':True,'runMilliseconds':[],'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in sess.get_inputs()],
            'outputs':[{'name':m.name,'shape':list(m.shape)} for m in sess.get_outputs()]}
    assert len(sess.get_inputs())==1 and len(sess.get_outputs())>=2
    meta=sess.get_inputs()[0];outputs=[]
    for feed in feeds:
        assert feed.shape==tuple(meta.shape) and feed.dtype==np.dtype(meta.dtype),(meta.name,feed.shape,feed.dtype,meta.shape,meta.dtype)
        t=time.perf_counter();values=sess.run(None,{meta.name:feed});record['runMilliseconds'].append((time.perf_counter()-t)*1000)
        assert all(np.isfinite(v).all() for v in values)
        vector=values[1].reshape(1,1152);outputs.append(vector.copy())
    r['sessions'].append(record)
    return np.concatenate(outputs)

pixels=inputs['pixel_values'].numpy().astype(np.float32)
tokens=inputs['input_ids'].numpy().astype(np.int32)
vision=run('vision','ax650/siglip_vision_u16_fcu8.axmodel',[pixels,pixels])
text=run('text','ax650/siglip_text_u16.axmodel',[tokens[i:i+1] for i in range(len(texts))]+[tokens[0:1]])
assert np.linalg.norm(vision,axis=1).min()>0 and np.linalg.norm(text,axis=1).min()>0
v=vision/np.linalg.norm(vision,axis=1,keepdims=True);t=text/np.linalg.norm(text,axis=1,keepdims=True)
scores=(v[0:1]@t[:len(texts)].T)[0]
r.update(scores=scores.tolist(),descendingOrder=np.argsort(-scores,kind='stable').tolist(),
         imageRepeatExact=bool(np.array_equal(vision[0],vision[1])),textRepeatExact=bool(np.array_equal(text[0],text[-1])),
         pixelShape=list(pixels.shape),tokenShape=list(tokens.shape))
np.savez_compressed(out/'embeddings.npz',visionRaw=vision,textRaw=text,visionNormalized=v,textNormalized=t,pixels=pixels,tokens=tokens)
r['embeddingFileSha256']=sha(out/'embeddings.npz');r['completed']=True
(out/'deployment-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print([(texts[i],float(scores[i])) for i in r['descendingOrder']],flush=True)
