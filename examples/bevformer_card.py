"""BEVFormer AXCL example: official six-view inputs and original LiDAR box geometry."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import cv2,numpy as np

COLORS=[(80,200,30),(0,200,255),(160,60,220),(220,120,0),(200,0,100),(150,190,200),(180,90,240),(0,150,220),(20,60,255),(60,180,255)]
EDGES=[(0,1),(0,3),(0,4),(1,2),(1,5),(3,2),(3,7),(4,5),(4,7),(2,6),(5,6),(6,7)]
def sha(x):return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def preprocess(root,scene,index):
 d=root/'inference_data'/scene;meta=json.loads((d/f'meta_{index:06d}.json').read_text());assert meta['num_cams']==6
 norm=meta['img_norm_cfg'];mean=np.array(norm['mean'],np.float32);std=np.array(norm['std'],np.float32);images=[];raw=[]
 for c in range(6):
  img=cv2.imread(str(d/f'cam_{c:02d}_{index:06d}.png'));assert img is not None;h,w=meta['img_shape'][c][:2]
  if img.shape[:2]!=(h,w):img=cv2.resize(img,(w,h))
  raw.append(img.copy());img=cv2.cvtColor(img,cv2.COLOR_BGR2RGB) if norm['to_rgb'] else img
  images.append(((img.astype(np.float32)-mean)/std).transpose(2,0,1))
 return np.ascontiguousarray(np.stack(images)[None]),np.array(meta['lidar2img'],np.float32)[None],np.array(meta['can_bus'],np.float32)[None],raw,meta

def decode(cls,box,config,threshold=.3):
 coder=config['model']['bbox_coder'];scores=1/(1+np.exp(-cls[-1,0]));flat=scores.reshape(-1);order=np.argsort(flat)[::-1][:coder['max_num']];labels=order%coder['num_classes'];q=order//coder['num_classes'];v=box[-1,0,q];boxes=np.column_stack([v[:,0],v[:,1],v[:,4],np.exp(v[:,2]),np.exp(v[:,3]),np.exp(v[:,5]),np.arctan2(v[:,6],v[:,7]),v[:,8],v[:,9]])
 region=np.array(coder['post_center_range']);valid=(flat[order]>threshold)&(boxes[:,:3]>=region[:3]).all(1)&(boxes[:,:3]<=region[3:]).all(1);boxes=boxes[valid];values=flat[order][valid];labels=labels[valid];q=q[valid];boxes[:,2]-=boxes[:,5]/2
 # Fixed display threshold and upstream per-class circle NMS; no adaptive threshold.
 radii=[2.,3.,2.5,4.,3.,1.,1.5,1.,.5,.3];keep=[]
 for i in np.argsort(values)[::-1]:
  if any(labels[i]==labels[k] and np.linalg.norm(boxes[i,:2]-boxes[k,:2])<radii[int(labels[i])] for k in keep):continue
  keep.append(i)
 return {'boxes':boxes[keep],'scores':values[keep],'labels':labels[keep],'queries':q[keep]}

def corners(boxes):
 # Original MMDetection3D v0.17.1 LiDARInstance3DBoxes: x_size,y_size,z_size,
 # bottom-centred boxes, row vectors right-multiplied by the z rotation.
 base=np.array([[0,0,0],[0,0,1],[0,1,1],[0,1,0],[1,0,0],[1,0,1],[1,1,1],[1,1,0]],np.float32)-np.array([.5,.5,0],np.float32)
 xyz=boxes[:,None,3:6]*base;c=np.cos(boxes[:,6]);s=np.sin(boxes[:,6]);out=xyz.copy();out[:,:,0]=xyz[:,:,0]*c[:,None]+xyz[:,:,1]*s[:,None];out[:,:,1]=-xyz[:,:,0]*s[:,None]+xyz[:,:,1]*c[:,None];return out+boxes[:,None,:3]

def project_segments(xyz,matrix,width,height):
 projected=np.column_stack([xyz,np.ones(8)])@matrix.T;lines=[]
 for i,j in EDGES:
  a,b=projected[i,:3].copy(),projected[j,:3].copy()
  if a[2]<.1 and b[2]<.1:continue
  if a[2]<.1:a=a+(.1-a[2])/(b[2]-a[2])*(b-a)
  if b[2]<.1:b=b+(.1-b[2])/(a[2]-b[2])*(a-b)
  points=np.stack([a[:2]/a[2],b[:2]/b[2]]);assert np.isfinite(points).all()
  # Clip in floating point before converting to int to avoid behind-camera overflow.
  start,end=points;delta=end-start;lo,hi=0.,1.
  for axis,limit in [(0,width-1),(1,height-1)]:
   if abs(delta[axis])<1e-12:
    if not 0<=start[axis]<=limit:lo,hi=1.,0.;break
   else:
    t0,t1=sorted([(0-start[axis])/delta[axis],(limit-start[axis])/delta[axis]]);lo=max(lo,t0);hi=min(hi,t1)
  if lo<=hi:lines.append(np.rint([start+lo*delta,start+hi*delta]).astype(np.int32).tolist())
 return lines

def render(raw,matrix,result,config,title):
 boxes=result['boxes'];vertices=corners(boxes);views=[];segments=[]
 for cam,img in enumerate(raw):
  img=img.copy();cam_segments=[]
  for i,xyz in enumerate(vertices):
   lines=project_segments(xyz,matrix[0,cam],img.shape[1],img.shape[0]);cam_segments.append(lines)
   for a,b in lines:cv2.line(img,tuple(a),tuple(b),COLORS[int(result['labels'][i])],2,cv2.LINE_AA)
  cv2.rectangle(img,(0,0),(img.shape[1],30),(20,25,30),-1);cv2.putText(img,f'CAM {cam}',(12,23),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),2);views.append(img);segments.append(cam_segments)
 tilew,tileh=640,384;views=[cv2.resize(im,(tilew,tileh)) for im in views];six=np.vstack([np.hstack([views[i] for i in [2,0,1]]),np.hstack([views[i] for i in [4,3,5]])]);size=768;bev=np.full((size,size,3),248,np.uint8);region=config['model']['bbox_coder']['pc_range']
 def xy(point):return (int(round((region[4]-point[1])/(region[4]-region[1])*(size-1))),int(round((region[3]-point[0])/(region[3]-region[0])*(size-1))))
 for meters in range(-50,51,10):cv2.line(bev,xy((meters,region[1])),xy((meters,region[4])),(220,220,220),1);cv2.line(bev,xy((region[0],meters)),xy((region[3],meters)),(220,220,220),1)
 for i,xyz in enumerate(vertices):
  pts=np.array([xy(xyz[k]) for k in [0,3,7,4]],np.int32);color=COLORS[int(result['labels'][i])];cv2.polylines(bev,[pts],True,color,2);cv2.circle(bev,xy(boxes[i,:2]),2,color,-1)
 cv2.circle(bev,xy((0,0)),6,(20,20,20),-1);cv2.arrowedLine(bev,xy((0,0)),xy((7,0)),(20,20,20),3);cv2.putText(bev,'BEV: forward up / left left',(15,30),cv2.FONT_HERSHEY_SIMPLEX,.65,(20,20,20),2)
 full=np.hstack([six,bev]);cv2.rectangle(full,(0,full.shape[0]-32),(full.shape[1],full.shape[0]),(20,25,30),-1);cv2.putText(full,title,(12,full.shape[0]-10),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),2);return full,vertices,segments

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--first-only',action='store_true');p.add_argument('--repeat',action='store_true');a=p.parse_args();a.model_dir=a.model_dir.resolve();a.output.mkdir(parents=True,exist_ok=False)
 manifest_path=a.model_dir/'.validation-download.json'
 if not manifest_path.exists():manifest_path=Path(__file__).resolve().parent/'download-manifest.json'
 manifest=json.loads(manifest_path.read_text());assert manifest['complete'] and manifest['modelId']=='bevformer' and manifest['revision']=='b5f3bf44f7430371c77d7719edd6569fd772ad77'
 for f in manifest['files']:assert hashlib.sha256((a.model_dir/f['path']).read_bytes()).hexdigest()==f['verifiedHashes']['sha256']
 import axengine
 start=time.perf_counter();session=axengine.InferenceSession(str(a.model_dir/'ax650/compiled.axmodel'),providers=['AXCLRTExecutionProvider']);load=time.perf_counter()-start;assert session.get_providers() in ('AXCLRTExecutionProvider',['AXCLRTExecutionProvider']);inputs=session.get_inputs();outputs=session.get_outputs();schema={'inputs':[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in inputs],'outputs':[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in outputs]};save(a.output/'schema.json',schema)
 assert {x.name for x in inputs}=={'img','can_bus','lidar2img','prev_bev'}
 config=json.loads((a.model_dir/'inference_config.json').read_text());index=json.loads((a.model_dir/'inference_data/scene_index.json').read_text());results=[];times=[]
 runs=[('main',list(index['scenes']))]+([('repeat',[next(iter(index['scenes']))])] if a.repeat else [])
 if a.first_only:runs=[('main',[next(iter(index['scenes']))])]
 for run,scenes in runs:
  for scene in scenes:
   prev=None;prev_pos=None;prev_angle=None
   for frame in index['scenes'][scene]['samples'][:1 if a.first_only else 3]:
    begin=time.perf_counter();img,lidar,can,raw,meta=preprocess(a.model_dir,scene,frame);pos=can[0,:3].copy();angle=float(can[0,-1]);delta=can.copy()
    if prev is None:delta[0,:3]=0;delta[0,-1]=0;prev=np.zeros(tuple(next(x.shape for x in inputs if x.name=='prev_bev')),np.float32)
    else:delta[0,:3]-=prev_pos;delta[0,-1]-=prev_angle
    feed={'img':img,'lidar2img':lidar,'can_bus':delta,'prev_bev':prev};prev_pos=pos;prev_angle=angle
    for x in inputs:assert tuple(feed[x.name].shape)==tuple(x.shape) and feed[x.name].dtype==x.dtype and np.isfinite(feed[x.name]).all(),(x.name,feed[x.name].shape,x.shape)
    started=time.perf_counter();values=session.run(None,feed);ms=1000*(time.perf_counter()-started);out={x.name:np.asarray(v).copy() for x,v in zip(outputs,values,strict=True)};assert all(np.isfinite(v).all() for v in out.values())
    # Output names are verified against the actual schema before this runner is used.
    assert set(out)=={'bev_embed','outputs_classes','outputs_coords'},set(out)
    name=f'{run}-{scene[:8]}-{frame:06d}';np.savez_compressed(a.output/(name+'.npz'),**{'in_'+k:v for k,v in feed.items()},**{'out_'+k:v for k,v in out.items()});prev=out['bev_embed'].reshape(feed['prev_bev'].shape)
    result=decode(out['outputs_classes'],out['outputs_coords'],config);vis,vertices,segments=render(raw,lidar,result,config,f'{run} | {scene[:8]} frame {frame} | AXCL | score > 0.30 | {len(result["scores"])} boxes');assert cv2.imwrite(str(a.output/(name+'.jpg')),vis)
    r={'name':name,'run':run,'scene':scene,'frame':frame,'threshold':.3,'nms':'official class circle radii','geometry':'MMDetection3D v0.17.1 original dimensions and yaw; no 0.9 scale or -80 degree offset','result':{k:v.tolist() for k,v in result.items()},'corners':vertices.tolist(),'projectedSegments':segments,'inputHashes':{k:sha(v) for k,v in feed.items()},'outputHashes':{k:sha(v) for k,v in out.items()},'milliseconds':ms,'pipelineSecondsIncludingTrace':time.perf_counter()-begin};save(a.output/(name+'.json'),r);results.append(r);times.append(ms);print(json.dumps({'sample':name,'detections':len(result['scores']),'milliseconds':ms}),flush=True)
 save(a.output/'deployment-result.json',{'modelId':'bevformer','revision':manifest['revision'],'completed':True,'provider':'AXCLRTExecutionProvider','loadSeconds':load,'sessions':[{'model':'ax650/compiled.axmodel','allFinite':True,'runMilliseconds':times,'inputs':schema['inputs'],'outputs':schema['outputs']}],'samples':results})
