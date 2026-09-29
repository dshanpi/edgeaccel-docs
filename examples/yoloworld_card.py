"""Run the official aarch64 AXCL YOLO-World SDK with explicit card selection."""
import argparse,ctypes,hashlib,json,os,shutil,sys,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();root,out=a.model_dir.resolve(),a.output.resolve();assert not out.exists(),'Choose a new output directory'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
expected={'pyyoloworld/pyaxdev.py':'ed34c73b5fd7f97638496f261508fdddecd3eb7730040fe0272b08cad438e2b1',
          'pyyoloworld/pyyoloworld.py':'cb082eb9c4d912ea4c8cf12150bd019b02b1021641b2420d0a1bfe82d982ddbb',
          'install/lib/axcl_aarch64/libyoloworld.so':'21600304ae9e8997ab10a641980b7b4a7788985b3478cf49b09e9643f7bdc5b8'}
for name,digest in expected.items():assert sha(root/name)==digest
lib=root/'install/lib/axcl_aarch64/libyoloworld.so'
elf=lib.read_bytes()[:64];assert elf[:6]==b'\x7fELF\x02\x01' and int.from_bytes(elf[18:20],'little')==183,'Use official aarch64 library'
target=root/'pyyoloworld/aarch64/libyoloworld.so';target.parent.mkdir(exist_ok=True)
if target.exists():assert sha(target)==sha(lib)
else:shutil.copy2(lib,target)
sys.path.insert(0,str(root/'pyyoloworld'))
import pyaxdev
from pyyoloworld import YOLOWORLD
assert Path(pyaxdev._lib._name).resolve()==target.resolve()
# Relative paths fit the vendor ABI's 128-byte fixed path fields.
os.chdir(root)
configured=['models/clip_b1_u16_ax650.axmodel','models/yolo_u16_ax650.axmodel']
out.mkdir(parents=True)
r={'modelId':'YOLO-World-V2','provider':'AXCL C API','completed':False,'sourceHashes':expected,
   'deviceType':'axcl_device','deviceId':0,'configuredWeightFiles':[{'path':x,'sha256':sha(root/x)} for x in configured],
   'vocabSha256':sha(root/'vocab.txt'),'sessions':[],
   'coverageScope':'Official native SDK pipeline; individual engine calls are not instrumented.',
   'threshold':0.1,'samples':[],'nativeCalls':[]}
def save():(out/'deployment-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
pyaxdev.sys_init(pyaxdev.AxDeviceType.axcl_device,0)
yw=None
try:
    start=time.perf_counter()
    yw=YOLOWORLD({'dev_type':pyaxdev.AxDeviceType.axcl_device,'devid':0,'text_encoder_path':configured[0],
                  'yoloworld_path':configured[1],'tokenizer_path':'vocab.txt','threshold':0.1})
    r['loadSeconds']=time.perf_counter()-start
    sets=[['person','dog','car','horse'],['man','shoes','ball','person']]
    for file in ['host.jpg','football.jpg']:
        img=Image.open(root/file).convert('RGB');pixels=np.ascontiguousarray(np.asarray(img,dtype=np.uint8))
        img.save(out/(Path(file).stem+'-input.png'))
        for set_index,classes in enumerate(sets):
            t=time.perf_counter();yw.set_classes(classes);encode_ms=(time.perf_counter()-t)*1000
            r['nativeCalls'].append({'function':'yw_set_classes','classes':classes,'milliseconds':encode_ms})
            detections=[];times=[]
            for repeat in [1,2]:
                t=time.perf_counter();dets=yw.detect(pixels);ms=(time.perf_counter()-t)*1000
                assert len(dets)<=32 and all(0<=d['label']<4 and np.isfinite(d['score']) and d['w']>0 and d['h']>0 for d in dets)
                times.append(ms);detections.append(dets)
                r['nativeCalls'].append({'function':'yw_detect','image':file,'setIndex':set_index,'repeat':repeat,'milliseconds':ms,'detectionCount':len(dets)})
            prefix=Path(file).stem+'-set'+str(set_index+1);canvas=img.copy();draw=ImageDraw.Draw(canvas)
            for d in detections[0]:
                x,y,w,h=d['x'],d['y'],d['w'],d['h'];draw.rectangle((x,y,x+w,y+h),outline='red',width=2)
                draw.text((x+2,max(0,y-12)),f"{classes[d['label']]}:{d['score']:.2f}",fill='red')
            canvas.save(out/(prefix+'-result.png'))
            row={'image':file,'inputSha256':sha(root/file),'imageSize':list(img.size),'classes':classes,'prefix':prefix,
                 'detections':detections[0],'repeatDetections':detections[1],'repeatExact':detections[0]==detections[1],
                 'setClassesMilliseconds':encode_ms,'runMilliseconds':times}
            r['samples'].append(row);save();print(file,classes,len(detections[0]),'repeat',row['repeatExact'],flush=True)
    r['nativeOutputFinite']=True;r['completed']=True;save()
finally:
    if yw is not None and yw.handle:
        pyaxdev.check_error(pyaxdev._lib.yw_destroy(yw.handle));yw.handle=None
    pyaxdev.sys_deinit(pyaxdev.AxDeviceType.axcl_device,0)
