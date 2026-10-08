"""Build a fixed LibCLIP AXCL image index and query it in isolated processes."""
import argparse,ctypes,hashlib,json,os,shutil,subprocess,sys,tarfile,time
from pathlib import Path
import cv2,numpy as np
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
EXPECTED={'pyclip/pyaxdev.py':'ca653cd9dd2530a7430282d770d0e8d8816ff0ffec503160c0c27553085ea5b6','pyclip/pyclip.py':'2992fef9791b5d565d67c4e5d04bfbf50eaf17c9a1c9d3417332c89979343845','install/lib/axcl_aarch64/libclip.so':'5e097744bbd20a6c9fb43724b362579000fbc9117ffee212ad54dc66bf377f69','coco_1000.tar':'f3e18a198658270e19ced079de7a404e3478e69c2ef94fb47c87ddf056e6a541'}
DEFAULT_QUERIES=['一只狗','一只猫','一辆公共汽车','人们在滑雪','桌子上的食物','一架飞机','火星上的紫色独角兽']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,r):p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--query',action='append');p.add_argument('--phase',choices=['build','query','maintenance','reopen'],help=argparse.SUPPRESS);p.add_argument('--query-index',type=int,help=argparse.SUPPRESS);a=p.parse_args()
 root,out=a.model_dir.resolve(),a.output.resolve();result=out/'deployment-result.json';queries=a.query or DEFAULT_QUERIES
 if a.phase is None:
  assert not out.exists(),'Use a new output directory'
  command=[sys.executable,str(Path(__file__).resolve()),'--model-dir',str(root),'--output',str(out)]
  for query in queries:command+=['--query',query]
  phases=[('build',None)]+[('query',i) for i in range(len(queries))]+[('maintenance',None),('reopen',None)]
  for phase,index in phases:
   args=command+['--phase',phase]
   if index is not None:args+=['--query-index',str(index)]
   start=time.perf_counter();subprocess.run(args,check=True);elapsed=time.perf_counter()-start;r=read(result);r['phaseWallSeconds'].append({'phase':phase,'queryIndex':index,'seconds':elapsed});write(result,r)
  r=read(result);assert r['persistence']['reopenedExact'] and r['persistence']['all1000KeysPresentAfterReopen'];r['completed']=True;write(result,r);print('Completed LibCLIP with isolated query processes',flush=True);return
 assert a.phase!='build' or not out.exists(),'Use a new output directory'
 for name,digest in EXPECTED.items():
  if name!='coco_1000.tar' or a.phase=='build':assert SHA(root/name)==digest,name
 lib=root/'install/lib/axcl_aarch64/libclip.so';elf=lib.read_bytes()[:64];assert elf[:6]==b'\x7fELF\x02\x01' and int.from_bytes(elf[18:20],'little')==183
 target=root/'pyclip/aarch64/libclip.so';target.parent.mkdir(exist_ok=True)
 if target.exists():assert SHA(target)==SHA(lib)
 else:shutil.copy2(lib,target)
 sys.path.insert(0,str(root/'pyclip'));import pyaxdev;from pyclip import Clip,ClipImage,ClipResultItem
 assert Path(pyaxdev._lib._name).resolve()==target.resolve();os.chdir(root);db=out/'index';assert len(str(db).encode())<128,'Index path exceeds the 128-byte vendor ABI field'
 configured=['cnclip/cnclip_vit_l14_336px_text_u16.axmodel','cnclip/cnclip_vit_l14_336px_vision_u16u8.axmodel']
 if a.phase=='build':
  out.mkdir(parents=True);images=out/'images';images.mkdir();files=[]
  # Only regular JPEG members are copied under checked, unique basenames.
  with tarfile.open(root/'coco_1000.tar','r:') as archive:
   members=[m for m in archive.getmembers() if m.isfile() and Path(m.name).suffix.lower()=='.jpg'];names=[Path(m.name).name for m in members];assert len(names)==len(set(names))==1000
   for member in sorted(members,key=lambda m:Path(m.name).name):
    key=Path(member.name).name;assert len(key.encode())<64;destination=images/key
    with archive.extractfile(member) as src,destination.open('wb') as dst:shutil.copyfileobj(src,dst)
    files.append({'key':key,'archiveMember':member.name,'sha256':SHA(destination),'bytes':destination.stat().st_size})
  r={'modelId':'LibCLIP','provider':'AXCL C API','completed':False,'deviceType':'axcl_device','deviceId':0,'queryIsolation':'One new process per text query; build, image/index checks and reopening also run serially in separate processes.','sourceHashes':EXPECTED,'configuredWeightFiles':[{'path':f,'sha256':SHA(root/f)} for f in configured],'vocabSha256':SHA(root/'cnclip/cn_vocab.txt'),'versions':{'numpy':np.__version__,'opencv':cv2.__version__},'sessions':[],'coverageScope':'Official native SDK pipeline, without per-engine tensor tracing. API times exclude process/model initialization.','indexedImages':files,'queries':queries,'nativeCalls':[],'samples':[],'phaseWallSeconds':[]}
 else:r=read(result);assert not r['completed'];files=r['indexedImages'];images=out/'images'
 def save():write(result,r)
 def call(name,fn,**fields):
  t=time.perf_counter();value=fn();r['nativeCalls'].append({'function':name,'phase':a.phase,'queryIndex':a.query_index,'milliseconds':(time.perf_counter()-t)*1000,**fields});return value
 def pixels(key):
  image=cv2.imread(str(images/key));assert image is not None;return np.ascontiguousarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB),dtype=np.uint8)
 def valid_result(rows):
  assert len(rows)==1000 and len({k for k,v in rows})==1000 and {k for k,v in rows}=={f['key'] for f in files} and all(np.isfinite(v) for k,v in rows);assert all(rows[i][1]>=rows[i+1][1] for i in range(len(rows)-1));return [[k,float(v)] for k,v in rows]
 def gallery(rows,name):
  canvas=np.full((340,1400,3),248,np.uint8)
  for i,(key,score) in enumerate(rows[:5]):
   image=cv2.imread(str(images/key));h,w=image.shape[:2];scale=min(270/w,260/h);image=cv2.resize(image,(round(w*scale),round(h*scale)));h,w=image.shape[:2];canvas[5:5+h,i*280+5:i*280+5+w]=image
   cv2.putText(canvas,f'{i+1}. {key}',(i*280+5,285),cv2.FONT_HERSHEY_SIMPLEX,.45,(20,20,20),1,cv2.LINE_AA);cv2.putText(canvas,f'score={score:.6f}',(i*280+5,313),cv2.FONT_HERSHEY_SIMPLEX,.45,(20,20,20),1,cv2.LINE_AA)
  path=out/name;assert cv2.imwrite(str(path),canvas);return {'file':name,'sha256':SHA(path)}
 def match_image(image_data):
  # Pass the output array directly, matching POINTER(ClipResultItem), and keep
  # the contiguous RGB input alive until the native call has returned.
  image=ClipImage();image.data=image_data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte));image.width=image_data.shape[1];image.height=image_data.shape[0];image.channels=3;image.stride=image_data.strides[0];items=(ClipResultItem*1000)();pyaxdev.check_error(pyaxdev._lib.clip_match_image(clip.handle,ctypes.byref(image),items,1000));return [(x.key.decode('utf-8'),float(x.score)) for x in items]
 info={'dev_type':pyaxdev.AxDeviceType.axcl_device,'devid':0,'text_encoder_path':configured[0],'image_encoder_path':configured[1],'tokenizer_path':'cnclip/cn_vocab.txt','db_path':str(db),'isCN':1};clip=None;pyaxdev.sys_init(pyaxdev.AxDeviceType.axcl_device,0)
 try:
  clip=call('clip_create',lambda:Clip(info));save()
  if a.phase=='build':
   for index,f in enumerate(files):
    key=f['key'];assert not clip.contains_image(key);im=pixels(key);call('clip_add',lambda:clip.add_image(key,im),key=key);assert clip.contains_image(key)
    if (index+1)%100==0:save();print('Indexed',index+1,'/ 1000',flush=True)
  elif a.phase=='query':
   index=a.query_index;assert index==len(r['samples']) and 0<=index<len(r['queries']);text=r['queries'][index]
   feat=call('clip_get_text_feat',lambda:clip.get_text_feat(text),query=text).astype(np.float32);assert feat.shape==(768,) and np.isfinite(feat).all();fp=out/f'query-{index+1}-feature.npy';np.save(fp,feat)
   direct=valid_result(call('clip_match_text',lambda:clip.match_text(text,1000),query=text));byfeat=valid_result(call('clip_match_feat',lambda:clip.match_feat(feat,1000),query=text));repeat=valid_result(call('clip_match_text',lambda:clip.match_text(text,1000),query=text,repeat=True));assert direct==byfeat==repeat
   raw=out/f'query-{index+1}-all-results.json';write(raw,{'text':direct,'feature':byfeat,'repeat':repeat});r['samples'].append({'kind':'text','query':text,'isolatedProcess':True,'top5':direct[:5],'scoreSum':sum(v for k,v in direct),'featureNorm':float(np.linalg.norm(feat)),'featureFile':fp.name,'featureSha256':SHA(fp),'rawFile':raw.name,'rawSha256':SHA(raw),'matchFeatureExact':True,'repeatExact':True,'gallery':gallery(direct,f'query-{index+1}-top5.png')});print(json.dumps({'query':text,'top5':direct[:5]},ensure_ascii=False),flush=True)
  elif a.phase=='maintenance':
   text=r['queries'][0];before=valid_result(call('clip_match_text',lambda:clip.match_text(text,1000),query=text,beforeImage=True));assert before[:5]==r['samples'][0]['top5']
   key=files[0]['key'];im=pixels(key);matches=[]
   for repeat in [False,True]:matches.append(valid_result(call('clip_match_image',lambda:match_image(im),key=key,repeat=repeat)))
   raw=out/'image-query-all-results.json';write(raw,matches);r['imageQuery']={'key':key,'top5':matches[0][:5],'selfRank':next(i+1 for i,(k,v) in enumerate(matches[0]) if k==key),'repeatExact':matches[0]==matches[1],'rawFile':raw.name,'rawSha256':SHA(raw),'gallery':gallery(matches[0],'image-query-top5.png')}
   after_image=valid_result(call('clip_match_text',lambda:clip.match_text(text,1000),query=text,afterImage=True));assert after_image==before
   removed=before[0][0];call('clip_remove',lambda:clip.remove_image(removed),key=removed);assert not clip.contains_image(removed);after_removal=call('clip_match_text',lambda:clip.match_text(text,5),query=text,afterRemoval=True);assert all(k!=removed for k,v in after_removal)
   im=pixels(removed);call('clip_add',lambda:clip.add_image(removed,im),key=removed,restored=True);after_restore=call('clip_match_text',lambda:clip.match_text(text,5),query=text,afterRestore=True)
   ranking_exact=[k for k,v in after_restore]==[k for k,v in before[:5]];difference=max(abs(v-before[i][1]) for i,(k,v) in enumerate(after_restore));assert ranking_exact and difference<1e-5
   r['persistence']={'phase':'built-awaiting-process-reopen','removedKey':removed,'afterRemoval':after_removal,'afterRestore':after_restore,'restoredExact':[[k,float(v)] for k,v in after_restore]==before[:5],'restoredRankingExact':ranking_exact,'restoredScoreMaxAbsDifference':difference,'textUnchangedAfterImage':True}
  elif a.phase=='reopen':
   assert all(clip.contains_image(f['key']) for f in files);text=r['queries'][0];reopened=call('clip_match_text',lambda:clip.match_text(text,5),query=text,afterReopen=True);assert [[k,float(v)] for k,v in reopened]==r['samples'][0]['top5'];r['persistence'].update(phase='reopened-in-new-process',afterReopen=reopened,reopenedExact=True,all1000KeysPresentAfterReopen=True);r['nativeOutputFinite']=True
  save()
 finally:
  if clip is not None and clip.handle:call('clip_destroy',lambda:pyaxdev.check_error(pyaxdev._lib.clip_destroy(clip.handle)));clip.handle=None;save()
  pyaxdev.sys_deinit(pyaxdev.AxDeviceType.axcl_device,0)
if __name__=='__main__':main()
