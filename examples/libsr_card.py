#!/usr/bin/env python3
"""Fixed ARM64 LibSR SDK: serial 128x128 tiles, saved inputs and actual x2 outputs."""
import argparse,ctypes,hashlib,json,platform,sys,time
from pathlib import Path
import cv2
import numpy as np

REVISION='7748f88f9f6dd8e536f2db920ba76822826fd52a'
HASHES={
 'lib/aarch64/libsr.so':'374146847484b9c421e5d85688122c93f5389edccaf195851d3a7d15c3c0fd8c',
 'lib/pyaxdev.py':'d4280c4a1a50ab239011dab1099b928863ab773f6be66c6b1fe8c8749c126848',
 'lib/pysr.py':'7193e50f6528fe5ae7cc3dbd5b7cb93002db7cdb6e936fdc1cb4c6a834f9f37c',
 'edsr_x2_128.axmodel':'77997756612342ed8e422be4c47bbe9bf04511bdc5483d3d953d188e5018ddb9'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pixels(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def png(folder,name,a):
    assert a.dtype==np.uint8 and a.ndim==3 and a.shape[2]==3
    p=folder/name;assert cv2.imwrite(str(p),a)
    return {'file':name,'sha256':sha(p),'pixelSha256':pixels(a),'shape':list(a.shape),'colorOrder':'BGR'}

def panel(images,labels):
    h,w=images[0].shape[:2];assert all(a.shape==images[0].shape for a in images)
    canvas=np.full((h+32,w*len(images),3),245,np.uint8)
    for i,(a,label) in enumerate(zip(images,labels)):
        canvas[32:,i*w:(i+1)*w]=a
        cv2.putText(canvas,label,(i*w+5,22),cv2.FONT_HERSHEY_SIMPLEX,.55,(30,30,30),1,cv2.LINE_AA)
    return canvas

def default_samples(model):
    source=model/'Images/cat.jpg';assert sha(source)=='59b67bce343d435cb8f79b6abefc6eecc79924abcda6e7c7e39f8173bb932bc1'
    cat=cv2.imread(str(source));assert cat.shape==(360,480,3)
    y,x=np.indices((129,257));pattern=np.stack([(x%256),(y*2%256),((x//8+y//8)%2)*255],axis=-1).astype(np.uint8)
    pattern[0,:]=(255,255,255);pattern[-1,:]=(0,255,255);pattern[:,0]=(255,0,255);pattern[:,-1]=(255,255,0)
    return [('cat',cat,{'kind':'official-image','source':'Images/cat.jpg','sha256':sha(source)}),
      ('cat-repeat',cat.copy(),{'kind':'repeat','of':'cat'}),
      ('cat-odd',cat[70:199,160:291].copy(),{'kind':'crop','xyxy':[160,70,291,199],'source':'cat'}),
      ('cat-small',cat[80:143,180:245].copy(),{'kind':'crop','xyxy':[180,80,245,143],'source':'cat'}),
      ('pattern',pattern,{'kind':'generated-border-and-color-pattern'}),
      ('blank',np.zeros((129,131,3),np.uint8),{'kind':'generated-black'}),
      ('cat-downsample',cv2.resize(cat,(240,180),interpolation=cv2.INTER_AREA),{'kind':'controlled-area-downsample','reference':'cat','referenceShape':[360,480,3]})]

def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--image',type=Path,action='append');a=p.parse_args()
    model=a.model_dir.resolve();out=a.output.resolve();assert not out.exists(),'Choose a new output directory'
    assert platform.machine() in ['aarch64','arm64']
    for f,digest in HASHES.items():assert sha(model/f)==digest, f+' version mismatch'
    elf=(model/'lib/aarch64/libsr.so').read_bytes()[:20];assert elf[:4]==b'\x7fELF' and int.from_bytes(elf[18:20],'little')==183
    weight=str(model/'edsr_x2_128.axmodel');assert len(weight.encode())<256
    samples=default_samples(model) if not a.image else []
    for i,source in enumerate(a.image or [],1):
        source=source.resolve();im=cv2.imread(str(source));assert im is not None
        samples.append((f'custom-{i}',im,{'kind':'custom','filename':source.name,'sha256':sha(source)}))
    assert samples and all(0<im.shape[0]<=2160 and 0<im.shape[1]<=3840 for _,im,_ in samples)
    out.mkdir(parents=True);(out/'tiles').mkdir()
    sys.path.insert(0,str(model/'lib'));import pyaxdev;from pysr import SR
    assert Path(pyaxdev._lib._name).resolve()==model/'lib/aarch64/libsr.so'
    pyaxdev._lib.ax_sr_get_scale.argtypes=[ctypes.c_void_p];pyaxdev._lib.ax_sr_get_scale.restype=ctypes.c_int
    record={'modelId':'libsr.axera','revision':REVISION,'provider':'AXCL C API','deviceType':'axcl_device','deviceId':0,'completed':False,'sessions':[],
      'sourceHashes':HASHES,'configuredWeightFiles':['edsr_x2_128.axmodel'],'coverageScope':'native SDK with explicit serial tile calls; no per-engine tensor trace',
      'versions':{'python':sys.version,'numpy':np.__version__,'opencv':cv2.__version__},'tiling':{'size':128,'scale':2,'pad':'bottom/right zero','merge':'non-overlapping then crop to 2H x 2W','execution':'one tile per native call, sequential'},'samples':[]}
    write(out/'deployment-result.json',record);sr=None;initialized=False
    try:
        pyaxdev.sys_init(pyaxdev.AxDeviceType.axcl_device,0);initialized=True
        start=time.perf_counter();sr=SR({'dev_type':pyaxdev.AxDeviceType.axcl_device,'devid':0,'model_path':weight});record['loadMilliseconds']=(time.perf_counter()-start)*1000
        assert pyaxdev._lib.ax_sr_get_scale(sr.handle)==2
        for name,im,origin in samples:
            im=np.ascontiguousarray(im);h,w=im.shape[:2];ph=(h+127)//128*128;pw=(w+127)//128*128
            padded=np.zeros((ph,pw,3),np.uint8);padded[:h,:w]=im;merged=np.zeros((ph*2,pw*2,3),np.uint8)
            s={'name':name,'origin':origin,'input':png(out,name+'-input.png',im),'tiles':[]};start=time.perf_counter()
            for y in range(0,ph,128):
                for x in range(0,pw,128):
                    tile=padded[y:y+128,x:x+128].copy();before=pixels(tile);t=time.perf_counter();result=sr(tile);elapsed=(time.perf_counter()-t)*1000
                    assert result.shape==(256,256,3) and result.dtype==np.uint8 and pixels(tile)==before
                    merged[2*y:2*y+256,2*x:2*x+256]=result
                    s['tiles'].append({'xy':[x,y],'inputPixelSha256':before,'output':png(out,f'tiles/{name}-{x}-{y}.png',result),'nativeMilliseconds':elapsed})
            s['tileLoopSecondsIncludingTileSave']=time.perf_counter()-start;result=merged[:2*h,:2*w].copy()
            cubic=cv2.resize(im,(2*w,2*h),interpolation=cv2.INTER_CUBIC)
            s['output']=png(out,name+'-sr.png',result);s['bicubic']=png(out,name+'-bicubic.png',cubic)
            s['nativeMilliseconds']=sum(t['nativeMilliseconds'] for t in s['tiles']);s['outputMinMax']=[int(result.min()),int(result.max())]
            s['comparison']=png(out,name+'-comparison.png',panel([cubic,result],['Bicubic x2','LibSR x2']))
            # The same central source region is shown at 4x display zoom on both sides.
            cx,cy=w//2,h//2;half=min(40,w//2,h//2);x0,y0=cx-half,cy-half;x1,y1=cx+half,cy+half
            s['zoomSourceXYXY']=[x0,y0,x1,y1]
            crops=[cv2.resize(img[2*y0:2*y1,2*x0:2*x1],None,fx=4,fy=4,interpolation=cv2.INTER_NEAREST) for img in [cubic,result]]
            s['zoom']=png(out,name+'-zoom.png',panel(crops,['Bicubic crop (display 4x)','LibSR crop (display 4x)']))
            record['samples'].append(s);write(out/'deployment-result.json',record);print(name,im.shape,'->',result.shape,'native-ms',s['nativeMilliseconds'],flush=True)
        if not a.image:
            assert record['samples'][0]['output']['pixelSha256']==record['samples'][1]['output']['pixelSha256']
            record['repeatPixelExact']=True
    finally:
        if sr is not None and sr.handle:
            handle=sr.handle;sr.handle=None;pyaxdev.check_error(pyaxdev._lib.ax_sr_deinit(handle))
        if initialized:pyaxdev.sys_deinit(pyaxdev.AxDeviceType.axcl_device,0)
    record['nativeOutputFinite']=True;record['completed']=True;write(out/'deployment-result.json',record)

if __name__=='__main__':main()
