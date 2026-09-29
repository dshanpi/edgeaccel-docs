#!/usr/bin/env python3
"""Run fixed LibDet SDK and compatible official weights on AXCL device 0."""
import argparse,ctypes,hashlib,json,math,platform,sys,time
from pathlib import Path
import cv2
import numpy as np

SDK_REVISION='0a50691f9581143c28be91c0e7247250fbc52daf'
SDK_HASHES={'lib/aarch64/libdet.so':'2d4c794896dee3be2c0291a0119e5dd3dcf2fc5459a750f3148ae2473f8b5d7d','lib/pyaxdev.py':'b78a4c3d64bba38a70f8a606789aaac61bf5920c49c8582334c15ec16034aad6','lib/pydet.py':'7729a399ca1c6fb77999f4979731a913f815ee0e7789690ecce116c0054ccd53'}
VARIANTS={
 'yolov8s':{'arg':'yolov8_dir','repo':'AXERA-TECH/YOLOv8','revision':'6380cf5da7db0efa8414ea0e3dbbc801fe22d9a0','file':'ax650/yolov8s.axmodel','sha256':'65da17e48e6d057fb18a1acf1e583c1534f9691944014357e35839479e3818a9','modelType':1,'classes':80,'keypoints':0},
 'yolo11s':{'arg':'yolo11_dir','repo':'AXERA-TECH/YOLO11','revision':'e178719ba1b03eaf07c981f859027f3278c1cb29','file':'ax650/yolo11s.axmodel','sha256':'bad83368e9d68ae9740e9bb72c34e6b8173635faca7eb366e5484f578fa10fa2','modelType':3,'classes':80,'keypoints':0},
 'yolo11x':{'arg':'yolo11_dir','repo':'AXERA-TECH/YOLO11','revision':'e178719ba1b03eaf07c981f859027f3278c1cb29','file':'ax650/yolo11x.axmodel','sha256':'18e3cd31f8a04750480f5e9c2d98a2684a51c6b5596da2def971427841e65d8b','modelType':3,'classes':80,'keypoints':0},
 'yolo11x-pose':{'arg':'pose_dir','repo':'AXERA-TECH/YOLO11-Pose','revision':'156938308275ed3dbe3772898d8766a399aeb173','file':'ax650/yolo11x-pose.axmodel','sha256':'f7f6afc79375cab17abde9094e3c7b94ef0357a1eef431cfb239d0edb265e4a1','modelType':4,'classes':1,'keypoints':17}}
FIXTURES={'bus.jpg':'33b198a1d2839bb9ac4c65d61f9e852196793cae9a0781360859425f6022b69c','football.jpg':'e7c4b752ef447bfec409888cea8709be15c01d0f6bf91bd16b7762deb90950dc','ssd_horse.jpg':'ed22f6b4c8c33e50e391e089ede14e8fa9402c623b09dbcf010e804770698fbb'}
COCO=('person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,fire hydrant,stop sign,parking meter,bench,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee,skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,tennis racket,bottle,wine glass,cup,fork,knife,spoon,bowl,banana,apple,sandwich,orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch,potted plant,bed,dining table,toilet,tv,laptop,mouse,remote,keyboard,cell phone,microwave,oven,toaster,sink,refrigerator,book,clock,vase,scissors,teddy bear,hair drier,toothbrush').split(',')
SKELETON=[(0,1),(0,2),(1,3),(2,4),(5,6),(5,7),(7,9),(6,8),(8,10),(5,11),(6,12),(11,12),(11,13),(13,15),(12,14),(14,16)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pixelsha(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def write(p,r):p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def png(out,name,a):
    f=out/name;assert cv2.imwrite(str(f),a);return {'file':name,'sha256':sha(f),'shape':list(a.shape),'bgrPixelSha256':pixelsha(a)}
def draw(im,objects):
    rendered=im.copy();h,w=im.shape[:2];thickness=max(1,round(min(h,w)/400));font=max(.45,min(h,w)/1300)
    for n,o in enumerate(objects,1):
        x,y,bw,bh=o['boxXYWH'];cv2.rectangle(rendered,(x,y,bw,bh),(0,220,0),thickness)
        cv2.putText(rendered,f"{n}:{o['class']} {o['score']:.2f}",(max(0,x),max(14,y-5)),cv2.FONT_HERSHEY_SIMPLEX,font,(0,180,0),thickness,cv2.LINE_AA)
        pts=o['keypoints'];valid=lambda pt:0<=pt[0]<w and 0<=pt[1]<h
        if pts:
            for i,j in SKELETON:
                if valid(pts[i]) and valid(pts[j]):cv2.line(rendered,tuple(pts[i]),tuple(pts[j]),(255,160,0),thickness,cv2.LINE_AA)
            for point in pts:
                if valid(point):cv2.circle(rendered,tuple(point),thickness+1,(0,0,255),-1,cv2.LINE_AA)
    return rendered

def main():
    p=argparse.ArgumentParser();p.add_argument('--sdk-dir',type=Path,required=True)
    for opt in ['yolov8-dir','yolo11-dir','pose-dir','input-dir']:p.add_argument('--'+opt,type=Path)
    p.add_argument('--variant',choices=['all',*VARIANTS],default='all');p.add_argument('--image',type=Path,action='append');p.add_argument('--output',type=Path,required=True);p.add_argument('--threshold',type=float,default=.25);a=p.parse_args()
    assert 0<a.threshold<1 and platform.machine() in ['aarch64','arm64'];sdk=a.sdk_dir.resolve();out=a.output.resolve();assert not out.exists(),'Choose a new output directory'
    for name,digest in SDK_HASHES.items():assert sha(sdk/name)==digest,'SDK version mismatch: '+name
    assert not Path('/home/axera/libdet.axera/build/libdet.so').exists(),'Remove the loader ambiguity before using this example'
    elf=(sdk/'lib/aarch64/libdet.so').read_bytes()[:20];assert elf[:4]==b'\x7fELF' and int.from_bytes(elf[18:20],'little')==183
    variants=list(VARIANTS) if a.variant=='all' else [a.variant];weights={}
    for name in variants:
        v=VARIANTS[name];directory=getattr(a,v['arg']);assert directory is not None,'Missing --'+v['arg'].replace('_','-');f=directory.resolve()/v['file'];assert sha(f)==v['sha256'] and len(str(f).encode())<256;weights[name]=f
    samples=[]
    if a.image:
        for i,f in enumerate(a.image,1):
            im=cv2.imread(str(f));assert im is not None;samples.append((f'custom-{i}',im,{'kind':'custom','filename':f.name,'sha256':sha(f)}))
    else:
        assert a.input_dir is not None,'Pass --input-dir or --image'
        for filename,digest in FIXTURES.items():
            f=a.input_dir/filename;assert sha(f)==digest;im=cv2.imread(str(f));assert im is not None;samples.append((Path(filename).stem,im,{'kind':'official-image','filename':filename,'sha256':digest}))
        samples.append(('football-repeat',samples[1][1].copy(),{'kind':'repeat','of':'football'}));samples.append(('blank',np.full((480,640,3),114,np.uint8),{'kind':'generated','value':114}))
    assert all(0<im.shape[0]<=4096 and 0<im.shape[1]<=4096 for _,im,_ in samples)
    out.mkdir(parents=True);sys.path.insert(0,str(sdk/'lib'));import pyaxdev;import pydet
    assert Path(pyaxdev._lib._name).resolve()==sdk/'lib/aarch64/libdet.so'
    sizes={cls.__name__:ctypes.sizeof(cls) for cls in [pydet.DetInit,pydet.DetImage,pydet.ObjectItem,pydet.ObjectResult]};assert sizes=={'DetInit':304,'DetImage':24,'ObjectItem':284,'ObjectResult':18180}
    assert pydet.DetInit.model_path.offset==12 and pydet.DetInit.threshold.offset==276 and pydet.ObjectItem.score.offset==276 and pydet.ObjectItem.label.offset==280
    record={'modelId':'libdet.axera','revision':SDK_REVISION,'provider':'AXCL C API','deviceType':'axcl_device','deviceId':0,'sessions':[],'completed':False,'sourceHashes':SDK_HASHES,'abiSizes':sizes,'threshold':a.threshold,'configuredWeightFiles':[str(weights[n]) for n in variants],
        'coverageScope':'native SDK pipeline and raw result structure; model input/output tensor trace not captured','versions':{'python':sys.version,'numpy':np.__version__,'opencv':cv2.__version__},'variants':[]}
    write(out/'deployment-result.json',record);initialized=False
    try:
        pyaxdev.sys_init(pyaxdev.AxDeviceType.axcl_device,0);initialized=True
        for name in variants:
            v=VARIANTS[name];det=None;vr={'variant':name,'weight':v,'samples':[]};t=time.perf_counter()
            try:
                det=pydet.AXDet(str(weights[name]),v['modelType'],v['classes'],v['keypoints'],a.threshold,dev_type=pyaxdev.AxDeviceType.axcl_device,devid=0);vr['loadMilliseconds']=(time.perf_counter()-t)*1000
                for sample,im,origin in samples:
                    rgb=np.ascontiguousarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));ih=pixelsha(rgb);h,w=im.shape[:2]
                    image=pydet.DetImage(w,h,3,int(rgb.strides[0]),rgb.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)));result=pydet.ObjectResult()
                    t=time.perf_counter();code=pyaxdev._lib.ax_det(det.handle,ctypes.byref(image),ctypes.byref(result));elapsed=(time.perf_counter()-t)*1000;pyaxdev.check_error(code)
                    assert pixelsha(rgb)==ih and 0<=result.num_objs<=64;objects=[]
                    for i in range(result.num_objs):
                        obj=result.objects[i];assert math.isfinite(obj.score) and a.threshold-1e-5<=obj.score<=1 and 0<=obj.label<v['classes'] and obj.num_kpt==v['keypoints']
                        box=list(obj.box);assert 0<=box[0]<w and 0<=box[1]<h and box[2]>=0 and box[3]>=0 and box[0]+box[2]<=w and box[1]+box[3]<=h
                        objects.append({'boxXYWH':box,'score':obj.score,'label':obj.label,'class':COCO[obj.label],'keypoints':[[obj.kpts[j][0],obj.kpts[j][1]] for j in range(obj.num_kpt)]})
                    prefix=name+'-'+sample;raw=out/(prefix+'-native.bin');raw.write_bytes(bytes(result))
                    sr={'name':sample,'origin':origin,'input':png(out,prefix+'-input.png',im),'sdkInputRgbSha256':ih,'nativeMilliseconds':elapsed,'returnCode':code,'objects':objects,'rawResult':{'file':raw.name,'sha256':sha(raw),'bytes':len(bytes(result))},'overlay':png(out,prefix+'-result.png',draw(im,objects))}
                    vr['samples'].append(sr);print(name,sample,'objects',len(objects),'ms',elapsed,flush=True)
            finally:
                if det is not None and det.handle:
                    handle=det.handle;det.handle=None;pyaxdev.check_error(pyaxdev._lib.ax_det_deinit(handle))
            if not a.image:
                assert vr['samples'][1]['objects']==vr['samples'][3]['objects'];vr['repeatExact']=True
            record['variants'].append(vr);write(out/'deployment-result.json',record)
    finally:
        if initialized:pyaxdev.sys_deinit(pyaxdev.AxDeviceType.axcl_device,0)
    record['nativeOutputFinite']=True;record['completed']=True;write(out/'deployment-result.json',record)

if __name__=='__main__':main()
