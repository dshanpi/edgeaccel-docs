"""Official split OWLv2 AXCL pipeline and CPU ONNX comparison."""
import argparse,hashlib,importlib.util,json,os,time
from pathlib import Path
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import axengine
import numpy as np
import onnxruntime as ort
import torch
from PIL import Image,ImageDraw
from transformers import Owlv2Processor
p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--processor-dir',type=Path,required=True)
p.add_argument('--output',type=Path,required=True);p.add_argument('--image',type=Path,action='append');a=p.parse_args()
root,proc,out=a.model_dir.resolve(),a.processor_dir.resolve(),a.output.resolve()
assert not out.exists(),'Choose a new output directory'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
source_hashes={'run_split_owlv2_full_demo_ax.py':'2cdbfb239a9da5bf243b26edd65991cea7bd3c31b6b4ec4bad49bf141ed9127b',
               'run_split_owlv2_full_demo.py':'32486d887a86fb0b012992df18c62e1563e4ee45c4dde0a30fbef7d3e7f337fc'}
for name,digest in source_hashes.items():assert sha(root/name)==digest
spec=importlib.util.spec_from_file_location('owlv2_verified',root/'run_split_owlv2_full_demo_ax.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
torch.set_num_threads(2)
processor=Owlv2Processor.from_pretrained(proc,local_files_only=True,trust_remote_code=False)
labels,queries=helper.load_labels(root/'4cls_labels.json');assert len(labels)==len(queries)==4
text_inputs=processor.tokenizer(queries,padding='max_length',return_tensors='pt')
ids=text_inputs['input_ids'].numpy();mask=text_inputs['attention_mask'].numpy()
images=a.image or [root/'test_img/000000039769.jpg',root/'test_img/ssd_horse.jpg',root/'test_img/test.jpg']
out.mkdir(parents=True)
r={'modelId':'OWLViT2','provider':'AXCLRTExecutionProvider','completed':False,'sourceHashes':source_hashes,
   'processorFiles':{f.name:sha(f) for f in proc.iterdir() if f.is_file() and not f.name.startswith('.')},
   'classes':labels,'queries':queries,'inputIds':ids.tolist(),'attentionMask':mask.tolist(),
   'scoreThreshold':0.1,'iouThreshold':0.45,'topkPerClass':20,'sessions':[],'cpuSessions':[],'samples':[]}
def save(): (out/'deployment-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
class Session:
    def __init__(self,path,cpu=False):
        self.cpu=cpu;t=time.perf_counter()
        if cpu:
            options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
            options.enable_cpu_mem_arena=False
            self.session=ort.InferenceSession(str(root/path),sess_options=options,providers=['CPUExecutionProvider'])
        else:self.session=axengine.InferenceSession(str(root/path),providers=['AXCLRTExecutionProvider'])
        self.record={'model':path,'weightSha256':sha(root/path),'loadSeconds':time.perf_counter()-t,
                     'allFinite':True,'runMilliseconds':[],
                     'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':m.type if cpu else str(m.dtype)} for m in self.session.get_inputs()],
                     'outputs':[{'name':m.name,'shape':list(m.shape)} for m in self.session.get_outputs()]}
        r['cpuSessions' if cpu else 'sessions'].append(self.record)
    def run(self,feeds):
        for m in self.session.get_inputs():
            assert all(not isinstance(d,int) or d==v for d,v in zip(m.shape,feeds[m.name].shape)),(m.name,feeds[m.name].shape,m.shape)
            if not self.cpu:assert feeds[m.name].dtype==np.dtype(m.dtype),(m.name,feeds[m.name].dtype,m.dtype)
        t=time.perf_counter();values=self.session.run(None,feeds);self.record['runMilliseconds'].append((time.perf_counter()-t)*1000)
        assert all(np.isfinite(v).all() for v in values)
        return [v.copy() for v in values]
ax={kind:Session(f'axmodel/owlv2_{kind}_4cls_640.axmodel') for kind in ['image','text','post']}
cpu={kind:Session(f'split_4cls/owlv2_{kind}_4cls.onnx',True) for kind in ['image','text','post']}
text_feed={'input_ids':ids.astype(np.int32),'attention_mask':mask.astype(np.int32)}
query=ax['text'].run(text_feed)[0];repeat_query=ax['text'].run(text_feed)[0]
cpu_query=cpu['text'].run({'input_ids':ids.astype(np.int64),'attention_mask':mask.astype(np.int64)})[0]
r['textRepeatExact']=bool(np.array_equal(query,repeat_query))
np.savez_compressed(out/'text-vectors.npz',card=query,repeat=repeat_query,cpu=cpu_query,ids=ids,mask=mask)
def post(values,logits,img):
    _,boxes,objectness=values
    return helper.postprocess_detections(logits,boxes,objectness,labels,queries,img.width,img.height,0.1,0.45,20)
def draw(img,dets,path):
    canvas=img.copy();d=ImageDraw.Draw(canvas)
    names=['person','car','cat','dog']
    for item in dets:
        x0,y0,x1,y1=item['box'];d.rectangle((x0,y0,x1,y1),outline='red',width=2)
        # English query text avoids dependence on an installed CJK font.
        label=item['label_en'].removeprefix('a photo of a ')
        d.text((x0+2,max(0,y0-12)),f"{label}:{item['score']:.3f}",fill='red')
    canvas.save(path)
for index,path in enumerate(images):
    img=Image.open(path).convert('RGB');prefix=f'sample{index+1}'
    img.save(out/(prefix+'-input.png'))
    pv=processor.image_processor(img,return_tensors='pt',size={'height':640,'width':640},image_mean=[0.,0.,0.],image_std=[1.,1.,1.])['pixel_values'].numpy()
    pixels=(pv*255).transpose(0,2,3,1).astype(np.uint8)
    cpu_pixels=processor.image_processor(img,return_tensors='pt',size={'height':640,'width':640})['pixel_values'].numpy().astype(np.float32)
    values=ax['image'].run({'pixel_values':pixels});repeat=ax['image'].run({'pixel_values':pixels})
    logits=ax['post'].run({'image_feats':values[0],'query_embeds':query,'input_ids':ids.astype(np.int32)})[0]
    repeat_logits=ax['post'].run({'image_feats':repeat[0],'query_embeds':query,'input_ids':ids.astype(np.int32)})[0]
    cv=cpu['image'].run({'pixel_values':cpu_pixels})
    cl=cpu['post'].run({'image_feats':cv[0],'query_embeds':cpu_query,'input_ids':ids.astype(np.int64)})[0]
    score_ranges={'card':[float(logits.min()),float(logits.max())],'cpu':[float(cl.min()),float(cl.max())]}
    print(path.name,'raw score ranges',score_ranges,flush=True)
    dets=post(values,logits,img);cpu_dets=post(cv,cl,img)
    draw(img,dets,out/(prefix+'-card.png'));draw(img,cpu_dets,out/(prefix+'-cpu.png'))
    np.savez_compressed(out/(prefix+'-raw.npz'),cardScores=logits,repeatScores=repeat_logits,cpuScores=cl,
                        cardBoxes=values[1],repeatBoxes=repeat[1],cpuBoxes=cv[1],
                        cardObjectness=values[2],repeatObjectness=repeat[2],cpuObjectness=cv[2],
                        cardPixels=pixels,cpuPixels=cpu_pixels)
    row={'name':path.name,'prefix':prefix,'inputSha256':sha(path),'imageSize':list(img.size),'detections':dets,'cpuDetections':cpu_dets,
         'repeatAllImageOutputsExact':all(np.array_equal(x,y) for x,y in zip(values,repeat)),
         'repeatPostExact':bool(np.array_equal(logits,repeat_logits)),
         'scoreMae':float(np.abs(logits.astype(np.float64)-cl).mean()),
         'scoreMaxAbsError':float(np.abs(logits.astype(np.float64)-cl).max()),
         'normalizedBoxMae':float(np.abs(values[1].astype(np.float64)-cv[1]).mean()),
         'rawSha256':sha(out/(prefix+'-raw.npz')),'rawScoreRanges':score_ranges,
         'cardScoresOutsideUnitInterval':int(np.count_nonzero((logits<0)|(logits>1))),
         'cpuScoresOutsideUnitInterval':int(np.count_nonzero((cl<0)|(cl>1)))}
    r['samples'].append(row);save()
    print(path.name,'card',len(dets),'CPU',len(cpu_dets),'scoreMAE',row['scoreMae'],flush=True)
r['completed']=True;save()
