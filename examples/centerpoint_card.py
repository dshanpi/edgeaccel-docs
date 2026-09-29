"""CenterPoint AXCL example with fixed weights, recorded tensors and LiDAR BEV output."""
import argparse,hashlib,importlib.util,json,sys,time
from pathlib import Path
import cv2,numpy as np
sys.dont_write_bytecode=True
COLORS=[(80,220,80),(0,180,255),(170,80,255),(230,180,30),(210,100,200),(220,220,20),(70,90,250),(255,130,50),(60,100,255),(100,220,240)]
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(x):return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
def upstream(root):
 spec=importlib.util.spec_from_file_location('centerpoint_upstream',root/'inference_axmodel.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def decode(outputs,config,u,threshold=.5):
 # Export already applies exp(dim), sigmoid(score), argmax(class). The training
 # targets and nuScenes Box use width,length,height without a channel permutation.
 boxes=[];scores=[];labels=[];origins=[];offset=0
 for task,t in enumerate(config['tasks']):
  reg,height,dim,rot,vel,score,cls=[x[0] for x in outputs[task*7:task*7+7]];h,w=score.shape;yy,xx=np.indices((h,w),dtype=np.float32);cfg=config['test_cfg'];mask=score>cfg['score_threshold'];x=(xx+reg[0])*cfg['out_size_factor']*cfg['voxel_size'][0]+cfg['pc_range'][0];y=(yy+reg[1])*cfg['out_size_factor']*cfg['voxel_size'][1]+cfg['pc_range'][1]
  assert np.all((cls>=0)&(cls<t['num_class']))
  b=np.stack([x[mask],y[mask],height[0][mask],dim[0][mask],dim[1][mask],dim[2][mask],np.arctan2(rot[0],rot[1])[mask],vel[0][mask],vel[1][mask]],axis=1).astype(np.float32);boxes.append(b);scores.append(score[mask].astype(np.float32));labels.append((cls[mask]+offset).astype(np.int32));origins.extend([[task,int(v)] for v in np.flatnonzero(mask)]);offset+=t['num_class']
 boxes=np.concatenate(boxes);scores=np.concatenate(scores);labels=np.concatenate(labels);origins=np.array(origins,np.int32).reshape(-1,2)
 # Retain the repository's class-agnostic aligned BEV NMS, explicitly recorded.
 keep=u.nms_bev(boxes,scores,labels,config['test_cfg']['nms']['nms_iou_threshold']);keep=keep[scores[keep]>threshold]
 if len(keep)>config['test_cfg']['max_per_img']:keep=keep[np.argsort(-scores[keep])[:config['test_cfg']['max_per_img']]]
 return {'boxes':boxes[keep],'scores':scores[keep],'labels':labels[keep],'origins':origins[keep]}

def footprint(box):
 x,y,z,w,l,h,theta,vx,vy=map(float,box);yaw=-theta-np.pi/2;c,s=np.cos(yaw),np.sin(yaw);xy=np.array([[l/2,w/2],[l/2,-w/2],[-l/2,-w/2],[-l/2,w/2]])
 return xy@np.array([[c,s],[-s,c]])+np.array([x,y])

def render(points,result,config,path,label):
 side=900;limit=51.2;scale=side/(2*limit)
 def pixels(xy):return np.rint(np.column_stack([side/2+xy[:,0]*scale,side/2-xy[:,1]*scale])).astype(np.int32)
 raw=np.full((side,side,3),(24,24,24),np.uint8)
 for dist in range(-50,51,10):
  a=int(round(side/2+dist*scale));cv2.line(raw,(a,0),(a,side-1),(48,48,48),1);cv2.line(raw,(0,a),(side-1,a),(48,48,48),1)
 p=pixels(points[:,:2]);valid=(p>=0).all(1)&(p<side).all(1);p=p[valid];raw[p[:,1],p[:,0]]=(160,180,195);overlay=raw.copy();corners=[]
 for box,score,label_id in zip(result['boxes'],result['scores'],result['labels']):
  xy=footprint(box);corners.append(xy.tolist());pix=pixels(xy);color=COLORS[int(label_id)];cv2.polylines(overlay,[pix],True,color,1,cv2.LINE_AA);center=pixels(box[None,:2])[0];front=pixels(xy[:2].mean(0)[None])[0];cv2.line(overlay,tuple(center),tuple(front),color,1,cv2.LINE_AA)
 canvas=np.full((1010,1800,3),24,np.uint8);canvas[50:950,:900]=raw;canvas[50:950,900:]=overlay
 cv2.putText(canvas,'Input LiDAR | x right, y up | +/-51.2 m',(18,32),cv2.FONT_HERSHEY_SIMPLEX,.65,(235,235,235),1,cv2.LINE_AA);cv2.putText(canvas,f'AXCL detections | score > 0.50 | {len(result["scores"])} boxes',(918,32),cv2.FONT_HERSHEY_SIMPLEX,.65,(235,235,235),1,cv2.LINE_AA)
 cv2.putText(canvas,label,(18,973),cv2.FONT_HERSHEY_SIMPLEX,.55,(235,235,235),1,cv2.LINE_AA)
 for i,name in enumerate(config['class_names']):cv2.putText(canvas,name,(18+i*176,999),cv2.FONT_HERSHEY_SIMPLEX,.40,COLORS[i],1,cv2.LINE_AA)
 assert cv2.imwrite(str(path),canvas);return corners

def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--limit',type=int,default=50);p.add_argument('--repeat',action='store_true');a=p.parse_args();assert 1<=a.limit<=50;a.output.mkdir(exist_ok=False,parents=True)
 root=a.model_dir;mp=root/'.validation-download.json';mp=mp if mp.exists() else Path(__file__).with_name('download-manifest.json');manifest=json.loads(mp.read_text());assert manifest['complete'] and manifest['revision']=='186e6a83fac0f4e89b6989628d1e214e4746e877'
 for f in manifest['files']:assert hashlib.sha256((root/f['path']).read_bytes()).hexdigest()==f['verifiedHashes']['sha256'],f['path']
 u=upstream(root);config=json.loads((root/'extracted_data/config.json').read_text());index=json.loads((root/'extracted_data/sample_index.json').read_text());assert len(index['samples'])==50
 import axengine,numba
 t=time.perf_counter();session=axengine.InferenceSession(str(root/'ax650/centerpoint.axmodel'),providers=['AXCLRTExecutionProvider']);load=time.perf_counter()-t;provider=session.get_providers();assert provider=='AXCLRTExecutionProvider' or provider==['AXCLRTExecutionProvider']
 info=lambda x:{'name':x.name,'shape':list(x.shape),'dtype':x.dtype.name};ins=[info(x) for x in session.get_inputs()];outs=[info(x) for x in session.get_outputs()];assert [x['name'] for x in ins]==['input.1','indices_input'] and len(outs)==42;record={'modelId':'centerpoint','revision':manifest['revision'],'completed':False,'provider':'AXCLRTExecutionProvider','loadSeconds':load,'numpyVersion':np.__version__,'numbaVersion':numba.__version__,'geometry':'box=[x,y,z,w,l,h,theta,vx,vy]; displayed yaw=-theta-pi/2; original dimensions','postprocess':'repository aligned class-agnostic BEV NMS IoU .2, candidate>.1, final>.5','samples':[],'sessions':[{'model':'ax650/centerpoint.axmodel','inputs':ins,'outputs':outs,'allFinite':True,'runMilliseconds':[]}]}
 jobs=[('main',i) for i in range(a.limit)]+([('repeat',i) for i in range(min(3,a.limit))] if a.repeat else [])
 for run,i in jobs:
  start=time.perf_counter();sample=index['samples'][i];points=np.fromfile(root/'extracted_data'/sample['points_path'],dtype=np.float32).reshape(-1,5);assert len(points)==sample['num_points'] and np.isfinite(points).all() and np.all(points[:,4]==0)
  vox,coords,counts=u.preprocess_pointpillars(points,config);features,indices=u.create_pillars_input(vox,coords,counts,config);feeds={'input.1':features,'indices_input':indices}
  for x in ins:assert list(feeds[x['name']].shape)==x['shape'] and feeds[x['name']].dtype.name==x['dtype']
  pre=time.perf_counter()-start;t=time.perf_counter();values=session.run(None,feeds);ms=(time.perf_counter()-t)*1000;assert all(np.isfinite(v).all() and list(v.shape)==x['shape'] and v.dtype.name==x['dtype'] for x,v in zip(outs,values))
  result=decode(values,config,u);name=f'{run}-{i:03d}';raw={'in_'+k:v for k,v in feeds.items()};raw.update({'out_'+x['name']:v for x,v in zip(outs,values)});np.savez_compressed(a.output/(name+'.npz'),**raw);corners=render(points,result,config,a.output/(name+'.jpg'),f'{name} | {len(points)} points | AXCL {ms:.3f} ms');entry={'name':name,'run':run,'index':i,'token':sample['token'],'pointCount':len(points),'voxelCount':len(vox),'preprocessSeconds':pre,'milliseconds':ms,'pipelineSecondsIncludingTrace':time.perf_counter()-start,'allFinite':True,'tensorHashes':{k:sha(v) for k,v in raw.items()},'result':{k:v.tolist() for k,v in result.items()},'footprints':corners};save(a.output/(name+'.json'),entry);record['samples'].append(entry);record['sessions'][0]['runMilliseconds'].append(ms);print(json.dumps({'name':name,'count':len(result['scores']),'milliseconds':ms,'preprocessSeconds':pre}),flush=True)
 record['completed']=True;save(a.output/'deployment-result.json',record)
if __name__=='__main__':main()
