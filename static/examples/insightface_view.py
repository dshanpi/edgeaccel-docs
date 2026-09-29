"""Draw the actual recorded Insightface coordinates; does not run inference."""
import argparse,json
from pathlib import Path
import cv2
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--result-dir',type=Path,required=True)
p.add_argument('--output',type=Path);a=p.parse_args()
r=json.loads((a.result_dir/'deployment-result.json').read_text(encoding='utf-8'))
assert r['modelId']=='Insightface' and r['completed'] and r['syntheticInput']
img=cv2.imread(str(a.result_dir/'input.png'));assert img is not None
faces=next(s for s in r['samples'] if s['kind']=='original')['faces']
out=a.output or a.result_dir;out.mkdir(parents=True,exist_ok=True)
colors=[(255,220,0),(0,190,255)]
for field,title,name in [('kps','Detection + 5 landmarks','detection.png'),
 ('landmark_2d_106','106-point landmarks','landmarks-106.png'),
 ('landmark_3d_68','3D 68-point model: image-plane projection','landmarks-68.png')]:
 canvas=np.zeros((img.shape[0]+100,img.shape[1],3),np.uint8);canvas[100:]=img
 cv2.putText(canvas,title,(25,40),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2,cv2.LINE_AA)
 cv2.putText(canvas,'Actual AXCL output | AI-generated fictional test input',(25,78),cv2.FONT_HERSHEY_SIMPLEX,.7,(200,200,200),1,cv2.LINE_AA)
 for i,face in enumerate(faces):
  color=colors[i%len(colors)];x1,y1,x2,y2=np.rint(face['bbox']).astype(int);y1+=100;y2+=100
  cv2.rectangle(canvas,(x1,y1),(x2,y2),color,2)
  label=f'Face {i+1} | score {face["det_score"]:.3f}'
  cv2.rectangle(canvas,(x1,y1-30),(x1+290,y1), (0,0,0),cv2.FILLED)
  cv2.putText(canvas,label,(x1+3,y1-8),cv2.FONT_HERSHEY_SIMPLEX,.6,color,1,cv2.LINE_AA)
  for x,y,*_ in face[field]:cv2.circle(canvas,(round(x),round(y)+100),3,color,cv2.FILLED,cv2.LINE_AA)
 assert cv2.imwrite(str(out/name),canvas)
 print(out/name)
