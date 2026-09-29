"""Run fixed-revision AXERA EdgeTAM prompts with explicit AXCL inference."""
import argparse
import hashlib
import json
import sys
import time
import types
from pathlib import Path
import axengine
import cv2
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--model-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root, out = a.model_dir.resolve(), a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
report = {'modelId': 'EdgeTAM', 'provider': 'AXCLRTExecutionProvider', 'completed': False,
          'sessions': [], 'results': [], 'sourceChanges': [
              'Skip unused ONNX-only albumentations construction; AX resize path unchanged.',
              'Skip unused no_mem_embed random initialization; image features do not read this field.',
              'Treat an all-zero input mask as absent; a partly-zero nonempty mask uses the mask encoder.']}
def save():
    (out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
original_session = axengine.InferenceSession
class MeasuredSession:
    def __init__(self, path):
        start=time.perf_counter()
        self.session=original_session(path,providers=['AXCLRTExecutionProvider'])
        self.record={'model':Path(path).relative_to(root).as_posix(),'loadSeconds':time.perf_counter()-start,
                     'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.session.get_inputs()],
                     'outputs':[{'name':m.name,'shape':list(m.shape)} for m in self.session.get_outputs()],
                     'runMilliseconds':[],'allFinite':True,'outputHashes':[]}
        report['sessions'].append(self.record);save()
    def run(self,names,feeds):
        for meta in self.session.get_inputs():
            v=feeds[meta.name]
            assert list(v.shape)==list(meta.shape) and v.dtype==np.dtype(meta.dtype),(meta.name,v.shape,v.dtype)
            assert np.isfinite(v).all()
        start=time.perf_counter();values=self.session.run(names,feeds)
        self.record['runMilliseconds'].append((time.perf_counter()-start)*1000)
        self.record['allFinite'] &= all(np.isfinite(v).all() for v in values)
        self.record['outputHashes'].append([hashlib.sha256(v.tobytes()).hexdigest() for v in values])
        save();assert self.record['allFinite']
        return values
axengine.InferenceSession=MeasuredSession
sys.path.insert(0,str(root))
transforms=(root/'utils/transforms.py').read_text()
predictor_source=(root/'utils/EdgeTAM_image_predictor.py').read_text()
report['sourceSha256']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['utils/transforms.py','utils/EdgeTAM_image_predictor.py']}
# Remove only construction of the unused ONNX branch, without importing new dependencies.
start=transforms.index('        self.transforms = A.Compose([')
end=transforms.index('        self.onnx = onnx',start)
transforms=transforms[:start]+'        assert not onnx, "This runner supports the AXCL path only"\n'+transforms[end:]
assert transforms.count('import albumentations as A')==1
assert transforms.count('from scipy.stats import truncnorm')==1
transforms=transforms.replace('import albumentations as A','').replace('from scipy.stats import truncnorm','')
assert predictor_source.count('trunc_normal_(self.no_mem_embed, std=0.02)')==1
assert predictor_source.count('self.no_mem_embed')==2
predictor_source=predictor_source.replace('trunc_normal_(self.no_mem_embed, std=0.02)','pass  # Unused random embedding initialization omitted.')
assert predictor_source.count('if mask_input.all() == 0:')==1
predictor_source=predictor_source.replace('if mask_input.all() == 0:','if not np.any(mask_input):')
module=types.ModuleType('utils.transforms');module.__file__=str(root/'utils/transforms.py')
exec(compile(transforms,module.__file__,'exec'),module.__dict__);sys.modules['utils.transforms']=module
namespace={'__name__':'edgetam_axcl_predictor'}
exec(compile(predictor_source,str(root/'utils/EdgeTAM_image_predictor.py'),'exec'),namespace)
predictor=namespace['ImagePredictor'](str(root/'axmodel'))
source=root/'examples/images/truck.jpg';image=cv2.imread(str(source));assert image is not None
rgb=cv2.cvtColor(image,cv2.COLOR_BGR2RGB);height,width=image.shape[:2]
cv2.imwrite(str(out/'input.png'),image)
predictor.set_image(rgb)
first={key:([v.copy() for v in value] if isinstance(value,list) else value.copy()) for key,value in predictor._features.items()}
predictor.set_image(rgb)
assert np.array_equal(first['image_embed'],predictor._features['image_embed'])
assert all(np.array_equal(x,y) for x,y in zip(first['high_res_feats'],predictor._features['high_res_feats']))
del first
report['encoderRepeatExact']=True
cases=[('whole-truck-box',None,None,[75,275,1725,850],None),
       ('window-point',[[500,375]],[1],None,None),
       ('two-positive-points',[[500,375],[1125,625]],[1,1],None,None),
       ('positive-negative-points',[[500,375],[1125,625]],[1,0],None,None),
       ('wheel-box-negative',[[575,750]],[0],[425,600,700,875],None),
       ('refine-window-mask',[[500,375],[1125,625]],[1,0],None,'window-point')]
logits_by_case={}
for label,points,labels,box,mask_from in cases:
    mask=np.zeros((1,256,256),np.float32) if mask_from is None else logits_by_case[mask_from].copy()
    if mask_from:
        assert np.any(mask)
        # Include a neutral zero logit to exercise a nonempty, partly-zero input mask.
        mask[:,0,0]=0
        assert np.any(mask) and not np.all(mask)
        np.save(out/(label+'-input-logits.npy'),mask)
    kw={'point_coords':np.array(points,np.float32) if points else None,
        'point_labels':np.array(labels,np.float32) if labels else None,
        'box':np.array(box,np.float32) if box else None,'mask_input':mask,'multimask_output':False}
    before=len(predictor.prompt_mask_encoder.record['runMilliseconds'])
    values=predictor.predict(**kw);repeat=predictor.predict(**kw)
    assert all(np.array_equal(x,y) for x,y in zip(values,repeat))
    masks,scores,logits=values
    index=int(np.argmax(scores))
    if masks.ndim==3:
        assert len(scores)==1 and masks.shape==(1,height,width),masks.shape
        selected=masks[0].astype(np.uint8)*255
    else:
        assert masks.shape==(1,height,width,len(scores)),masks.shape
        selected=masks[0,:,:,index].astype(np.uint8)*255
    logits_by_case[label]=logits[index:index+1].copy()
    called=len(predictor.prompt_mask_encoder.record['runMilliseconds'])-before
    assert called==(2 if mask_from else 0)
    np.savez_compressed(out/(label+'-raw.npz'),masks=masks,scores=scores,logits=logits)
    cv2.imwrite(str(out/(label+'-mask.png')),selected)
    overlay=image.copy();pixels=selected>0
    overlay[pixels]=(.55*overlay[pixels]+.45*np.array([255,144,30])).astype(np.uint8)
    if box:cv2.rectangle(overlay,tuple(box[:2]),tuple(box[2:]),(0,255,0),3)
    if points:
        for point,flag in zip(points,labels):cv2.drawMarker(overlay,tuple(point),(0,255,0) if flag else (0,0,255),cv2.MARKER_STAR,24,3)
    cv2.imwrite(str(out/(label+'-overlay.png')),overlay)
    report['results'].append({'label':label,'image':'examples/images/truck.jpg','imageSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'points':points,'pointLabels':labels,'boxXYXY':box,'maskInputFrom':mask_from,'maskEncoderCalls':called,
        'selectedMask':index,'predictedScores':scores.tolist(),'maskPixels':int(np.count_nonzero(selected)),
        'maskFraction':float(np.count_nonzero(selected)/(height*width)),'repeatExact':True,'stem':label})
    save()
assert all(s['runMilliseconds'] and s['allFinite'] for s in report['sessions'])
report['completed']=True;save()
print(json.dumps({'completed':True,'prompts':len(report['results']),'calls':{s['model']:len(s['runMilliseconds']) for s in report['sessions']}}))
