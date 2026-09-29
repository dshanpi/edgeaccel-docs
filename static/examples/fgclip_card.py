"""Run the fixed FG-CLIP2 official encoders through AXCL."""
import argparse,ast,hashlib,json,os,time
from pathlib import Path
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
import axengine
import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor,AutoTokenizer

p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True)
p.add_argument('--output',type=Path,required=True);p.add_argument('--image',type=Path)
p.add_argument('--text',action='append');a=p.parse_args()
root,out=a.model_dir.resolve(),a.output.resolve();assert not out.exists(),'Choose a new output directory'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
source=root/'run_axmodel.py'
assert sha(source)=='cf0ab16c7af21c3bd8dbbc22bc5affff4f2e8417b09267f85c44ac2feb5c5153'
helpers={'__name__':'fgclip_official_helpers'}
exec(compile(source.read_text('utf-8'),str(source),'exec'),helpers)
# Extract the exact four official candidate strings without executing the main block.
tree=ast.parse(source.read_text('utf-8'))
official=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=='captions' for t in n.targets) and isinstance(n.value,ast.List))
texts=[s.lower() for s in (a.text or official)]
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
torch.set_num_threads(2)
processor=AutoImageProcessor.from_pretrained(root/'fg-clip2-base',use_fast=True,local_files_only=True,trust_remote_code=False)
tokenizer=AutoTokenizer.from_pretrained(root/'fg-clip2-base',local_files_only=True,trust_remote_code=False)
for text in texts:assert len(tokenizer(text)['input_ids'])<=196,'Shorten text to fit 196 tokens'
tokens=tokenizer(texts,padding='max_length',max_length=196,truncation=False,return_tensors='pt')['input_ids'].numpy().astype(np.int32)
image_path=(a.image or root/'bedroom.jpg').resolve();img=Image.open(image_path).convert('RGB')
patches=helpers['determine_max_value'](img)
inputs=processor(images=img,max_num_patches=patches,return_tensors='pt')
feeds={'pixel_values':inputs['pixel_values'].numpy().astype(np.float32),
       'pixel_attention_mask':inputs['pixel_attention_mask'].numpy().astype(np.int32)}
out.mkdir(parents=True);img.save(out/'input.png')
r={'modelId':'FG-CLIP','provider':'AXCLRTExecutionProvider','completed':False,'sourceSha256':sha(source),
   'inputImageSha256':sha(image_path),'savedImageSha256':sha(out/'input.png'),'originalImageSize':list(img.size),
   'processorClass':type(processor).__name__,'tokenizerClass':type(tokenizer).__name__,
   'processorFiles':{str(f.relative_to(root)):sha(f) for f in (root/'fg-clip2-base').iterdir() if f.is_file()},
   'texts':texts,'maxNumPatches':patches,'textContext':196,'sessions':[],
   'preprocessedShapes':{k:list(v.shape) for k,v in feeds.items()},'inputTokenIds':tokens.tolist()}
def save(): (out/'deployment-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def run(weight,requests):
    t=time.perf_counter();sess=axengine.InferenceSession(str(root/weight),providers=['AXCLRTExecutionProvider'])
    record={'model':weight,'weightSha256':sha(root/weight),'loadSeconds':time.perf_counter()-t,
            'allFinite':True,'runMilliseconds':[],'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in sess.get_inputs()],
            'outputs':[{'name':m.name,'shape':list(m.shape)} for m in sess.get_outputs()]}
    r['sessions'].append(record);save();results=[]
    for feed in requests:
        for m in sess.get_inputs():assert feed[m.name].shape==tuple(m.shape) and feed[m.name].dtype==np.dtype(m.dtype),(m.name,feed[m.name].shape,feed[m.name].dtype,m.shape,m.dtype)
        t=time.perf_counter();values=sess.run(None,feed);record['runMilliseconds'].append((time.perf_counter()-t)*1000)
        assert all(np.isfinite(v).all() for v in values)
        results.append(values[0].copy())
    return np.concatenate(results)
vision=run('image_encoder.axmodel',[feeds,feeds])
text=run('text_encoder.axmodel',[{'input_ids':tokens[i:i+1]} for i in range(len(texts))]+[{'input_ids':tokens[:1]}])
assert vision.shape[0]==2 and text.shape[0]==len(texts)+1 and vision.shape[1]==text.shape[1]
dot=vision[:1]@text[:len(texts)].T
logits=dot*np.exp(4.75)-16.75
distribution=torch.from_numpy(logits).softmax(dim=-1).numpy()[0]
r.update(embeddingDimensions=vision.shape[1],dotScores=dot[0].tolist(),candidateDistribution=distribution.tolist(),
         descendingOrder=np.argsort(-dot[0],kind='stable').tolist(),imageRepeatExact=bool(np.array_equal(vision[0],vision[1])),
         textRepeatExact=bool(np.array_equal(text[0],text[-1])),visionNorms=np.linalg.norm(vision,axis=1).tolist(),
         textNorms=np.linalg.norm(text,axis=1).tolist(),logitScale=4.75,logitBias=-16.75)
np.savez_compressed(out/'embeddings.npz',visionRaw=vision,textRaw=text,tokens=tokens,**feeds)
r['embeddingFileSha256']=sha(out/'embeddings.npz');r['completed']=True;save()
print([(texts[i],float(dot[0,i]),float(distribution[i])) for i in r['descendingOrder']],flush=True)
