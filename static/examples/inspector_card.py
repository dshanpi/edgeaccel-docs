"""Run the fixed official image-inspection pipeline through AXCL and save real results."""
import argparse,concurrent.futures,dataclasses,enum,hashlib,importlib.metadata,json,sys,threading,time
from pathlib import Path
import axengine,cv2,numpy as np
from PIL import Image,ImageDraw,ImageOps

REVISION='e7e143272e4f9e95d97849bac58c5c67629efed1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def serial(value):
    if isinstance(value,enum.Enum):return value.value
    if dataclasses.is_dataclass(value):return {f.name:serial(getattr(value,f.name)) for f in dataclasses.fields(value) if f.name!='figure_images'}
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items() if k!='img'}
    if isinstance(value,(tuple,list)):return [serial(v) for v in value]
    if isinstance(value,np.generic):return value.item()
    return value
def desc(a):
    a=np.ascontiguousarray(a);return {'shape':list(a.shape),'dtype':str(a.dtype),'sha256':hashlib.sha256(a.tobytes()).hexdigest()}

def deskew_small_angle(image):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    points=np.column_stack(np.where(gray<200))[:,::-1].astype(np.float32)
    if len(points)<10:return image,0.0
    angle=float(cv2.minAreaRect(points)[-1]);angle=(angle+45)%90-45
    if abs(angle)<.5 or abs(angle)>15:return image,0.0
    height,width=image.shape[:2];matrix=cv2.getRotationMatrix2D((width/2,height/2),angle,1.0)
    return cv2.warpAffine(image,matrix,(width,height),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE),angle

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--manifest',type=Path);p.add_argument('--image',type=Path);a=p.parse_args()
    root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);cv2.setNumThreads(2)
    mf=a.manifest or (root/'.validation-download.json' if (root/'.validation-download.json').exists() else Path(__file__).with_name('inspector-download-manifest.json'))
    manifest=json.loads(mf.read_text(encoding='utf-8'));assert manifest['complete'] and manifest['revision']==REVISION
    for f in manifest['files']:assert (root/f['path']).stat().st_size==f['size'] and sha(root/f['path'])==f['verifiedHashes']['sha256'],f['path']
    report={'modelId':'pp-nsfw_Inspector','revision':REVISION,'provider':'AXCLRTExecutionProvider','completed':False,'qualityValidated':False,'sessions':[],'samples':[],
            'settings':{'serialNpu':True,'perceptionWorkers':1,'cvThreads':2,'shortUrlExpansion':'disabled-offline','preprocess':'official-with-xy-normalized-small-angle-deskew'},
            'versions':{n:importlib.metadata.version(n) for n in ['numpy','Pillow','opencv-python-headless','pyzbar','pyahocorasick','google-re2','opencc-python-reimplemented','pyclipper']}}
    active={'sample':None,'slice':None,'operation':None};count=0;lock=threading.RLock();original_session=axengine.InferenceSession
    def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def png(img,label):
        nonlocal count
        count+=1;file=out/f'{count:04d}-{label}.png';img.convert('RGB').save(file);return {'file':file.name,'sha256':sha(file),'pixels':desc(np.asarray(img.convert('RGB')))}
    def raw(arrays):
        nonlocal count
        count+=1;file=out/f'{count:04d}-tensors.npz';np.savez_compressed(file,**arrays);return {'file':file.name,'sha256':sha(file),'arrays':{k:desc(v) for k,v in arrays.items()}}
    class Session:
        def __init__(self,path,*args,**kwargs):
            with lock:
                start=time.perf_counter();self.engine=original_session(path,providers=['AXCLRTExecutionProvider']);assert 'AXCLRTExecutionProvider' in self.engine.get_providers()
                schema=lambda xs:[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in xs]
                self.rec={'model':str(Path(path).relative_to(root)),'weightSha256':sha(path),'provider':self.engine.get_providers(),'loadSeconds':time.perf_counter()-start,'inputs':schema(self.engine.get_inputs()),'outputs':schema(self.engine.get_outputs()),'allFinite':True,'runMilliseconds':[],'calls':[]};report['sessions'].append(self.rec);save()
        def get_inputs(self):return self.engine.get_inputs()
        def get_outputs(self):return self.engine.get_outputs()
        def run(self,names,feed):
            with lock:
                for x in self.get_inputs():assert feed[x.name].shape==tuple(x.shape) and np.isfinite(feed[x.name]).all(),x.name
                start=time.perf_counter();values=self.engine.run(names,feed);ms=(time.perf_counter()-start)*1000
                keys=names or [x.name for x in self.get_outputs()];arrays={**{'input-'+k:np.asarray(v) for k,v in feed.items()},**{'output-'+k:np.asarray(v) for k,v in zip(keys,values)}};assert all(np.isfinite(v).all() for v in arrays.values())
                c={**active,'milliseconds':ms,'raw':raw(arrays)};self.rec['calls'].append(c);self.rec['runMilliseconds'].append(ms);save();return values
    axengine.InferenceSession=Session;sys.path.insert(0,str(root))
    from src.preprocess.pipeline import run as preprocess
    from src.preprocess import image_processor
    def deskew(image):
        result,angle=deskew_small_angle(image);report['samples'][-1]['deskewAngleDegrees']=angle;return result
    image_processor._deskew=deskew
    from src.perception import ocr_extractor as ocr,nsfw_detector as nsfw,qr_detector as qr
    # Deterministic offline mode: still decode QR and apply domain rules, but do not follow URLs.
    qr._expand_short_url=lambda url,timeout=3:url
    original_rec=ocr._recognize_crop;original_full=ocr._run_ocr_full;original_layout=ocr._run_structure;original_nsfw=nsfw.detect
    current={};opcount=0
    def operation(kind):
        nonlocal opcount
        opcount+=1;old=active['operation'];active['operation']=f'{kind}-{opcount}';return old,active['operation']
    def recognize(crop):
        old,tag=operation('recognize');entry={'operation':tag,'input':png(Image.fromarray(crop[:,:,::-1]),'ocr-crop')};current['recognitions'].append(entry)
        try:
            text,score=original_rec(crop);entry.update(text=text,score=float(score));return text,score
        finally:active['operation']=old
    def full(arr,threshold):
        old,tag=operation('ocr');entry={'operation':tag,'input':png(Image.fromarray(arr),'ocr-input'),'threshold':threshold};current['ocrRuns'].append(entry)
        try:
            result=original_full(arr,threshold);entry['blocks']=serial(result);return result
        finally:active['operation']=old
    def layout(arr):
        old,tag=operation('layout');entry={'operation':tag,'input':png(Image.fromarray(arr),'layout-input')};current['layoutRuns'].append(entry)
        try:
            result=original_layout(arr);entry['regions']=serial(result);return result
        finally:active['operation']=old
    def detect(img):
        old,tag=operation('nsfw');entry={'operation':tag,'input':png(img,'nsfw-input')};current['nsfwRuns'].append(entry)
        try:
            result=original_nsfw(img);entry['result']=serial(result);return result
        finally:active['operation']=old
    ocr._recognize_crop=recognize;ocr._run_ocr_full=full;ocr._run_structure=layout;nsfw.detect=detect
    from src.perception import pipeline as perception
    perception.ThreadPoolExecutor=lambda max_workers:concurrent.futures.ThreadPoolExecutor(max_workers=1)
    from src.understanding.pipeline import run as understand
    from src.decision.pipeline import decide
    if a.image:
        source=a.image.resolve();jobs=[{'id':'custom','file':source.name,'sha256':sha(source)}];inputroot=source.parent
    else:
        inputroot=a.inputs.resolve();jobs=json.loads((inputroot/'inputs.json').read_text(encoding='utf-8'))['samples']
    for job in jobs:
        source=inputroot/job['file'];assert sha(source)==job['sha256'];active.update(sample=job['id'],slice=None,operation=None)
        with Image.open(source) as opened:fmt=opened.format;img=ImageOps.exif_transpose(opened).convert('RGB')
        sample={'id':job['id'],'sourceSha256':sha(source),'format':fmt,'input':png(img,'original'),'slices':[]};report['samples'].append(sample);start=time.perf_counter();pre=preprocess(img,fmt);sample.update(scene=serial(pre.scene_result),warnings=pre.warnings)
        for index,part in enumerate(pre.images):
            active['slice']=index;current={'index':index,'image':png(part,'processed'),'recognitions':[],'ocrRuns':[],'layoutRuns':[],'nsfwRuns':[]};sample['slices'].append(current)
            perc=perception.run(part,pre.scene_result);und=understand([b.text for b in perc.ocr.blocks]);decision=decide(pre.scene_result.scene,perc.nsfw,perc.qr,perc.ocr,und.rule_hits)
            current.update(perception=serial(perc),understanding=serial(und),decision=serial(decision))
            overlay=part.copy();draw=ImageDraw.Draw(overlay)
            for n,b in enumerate(perc.ocr.blocks,1):draw.rectangle(b.bbox,outline='#00a070',width=3);draw.text((b.bbox[0],max(0,b.bbox[1]-14)),str(n),fill='#00452c')
            for box in perc.ocr.figure_bboxes:draw.rectangle(box,outline='#e07b00',width=3)
            current['overlay']=png(overlay,'overlay');save()
        sample['pipelineSecondsWithTrace']=time.perf_counter()-start
        sample['decision']=min((s['decision'] for s in sample['slices']),key=lambda d:{'REJECT':0,'REVIEW':1,'PASS':2}[d['action']]);save();print(json.dumps({'sample':job['id'],'scene':sample['scene'],'decision':sample['decision']},ensure_ascii=True),flush=True)
    assert len(report['sessions'])==5 and all(s['allFinite'] and s['runMilliseconds'] for s in report['sessions']) if not a.image else all(s['runMilliseconds'] for s in report['sessions'])
    report['completed']=True;save()

if __name__=='__main__':main()
