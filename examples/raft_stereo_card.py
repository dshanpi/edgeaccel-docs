"""Run both supported RAFT-Stereo AX650 variants on the official stereo pairs."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import axengine
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser()
p.add_argument('--model-dir',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--variant',choices=['r1','r4'],required=True)
a=p.parse_args();root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
namespace={'__name__':'raft_official_helpers'}
exec(compile((root/'infer.py').read_text(),str(root/'infer.py'),'exec'),namespace)
variant={'r1':('ax650/raft_steoro256x640_r1.axmodel',640,256),'r4':('ax650/raft_steoro384x1280_r4.axmodel',1280,384)}[a.variant]
weight,width,height=variant
report={'modelId':'RAFT-stereo','variant':a.variant,'provider':'AXCLRTExecutionProvider','completed':False,'sessions':[],'results':[],
        'upstreamScriptSha256':hashlib.sha256((root/'infer.py').read_bytes()).hexdigest(),
        'visualization':{'quantity':'absolute horizontal disparity in original-image pixels','colormap':'jet','range':[0,256],'clippedForColorOnly':True}}
def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
start=time.perf_counter();session=axengine.InferenceSession(str(root/weight),providers=['AXCLRTExecutionProvider'])
meta={'model':weight,'loadSeconds':time.perf_counter()-start,
      'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in session.get_inputs()],
      'outputs':[{'name':m.name,'shape':list(m.shape)} for m in session.get_outputs()],
      'runMilliseconds':[],'allFinite':True}
report['sessions'].append(meta);save()
sources=sorted((root/'examples/left').glob('*.png'));assert len(sources)==10
for source in sources:
    right=root/'examples/right'/source.name;assert right.is_file()
    left_input,(orig_h,orig_w)=namespace['load_and_preprocess_image'](str(source),width,height)
    right_input,right_hw=namespace['load_and_preprocess_image'](str(right),width,height)
    assert (orig_h,orig_w)==right_hw
    feeds={'x1':left_input,'x2':right_input}
    for m in session.get_inputs():assert feeds[m.name].shape==tuple(m.shape) and feeds[m.name].dtype==np.dtype(m.dtype),(m.name,m.shape,m.dtype)
    values=[];times=[]
    for repeat in range(2):
        start=time.perf_counter();outputs=session.run(None,feeds);times.append((time.perf_counter()-start)*1000)
        assert all(np.isfinite(v).all() for v in outputs)
        values.append(outputs)
    assert all(np.array_equal(x,y) for x,y in zip(values[0],values[1]))
    names=[m.name for m in session.get_outputs()];raw=values[0][names.index('output')]
    assert raw.ndim==4 and raw.shape[:2]==(1,1)
    flow=namespace['resize_disp'](raw[0,0],orig_w,orig_h)
    flow*=orig_w/width;disparity=np.abs(flow)
    assert np.isfinite(disparity).all()
    np.savez_compressed(out/(source.stem+'-raw.npz'),raw=raw,disparity=disparity)
    cv2.imwrite(str(out/(source.stem+'-left.png')),cv2.imread(str(source)))
    cv2.imwrite(str(out/(source.stem+'-right.png')),cv2.imread(str(right)))
    plt.imsave(out/(source.stem+'-disparity.png'),disparity,cmap='jet',vmin=0,vmax=256)
    meta['runMilliseconds'].extend(times)
    report['results'].append({'pair':source.name,'leftSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'rightSha256':hashlib.sha256(right.read_bytes()).hexdigest(),'inputSize':[width,height],'originalSize':[orig_w,orig_h],
        'allFinite':True,'repeatExact':True,'runMilliseconds':times,'rawSha256':hashlib.sha256(raw.tobytes()).hexdigest(),
        'disparityPercentiles':{str(q):float(np.percentile(disparity,q)) for q in [0,25,50,75,95,100]},
        'colorClippedFraction':float(np.mean(disparity>256))})
    save();print(a.variant,source.name,times,flush=True)
report['completed']=True;save()
