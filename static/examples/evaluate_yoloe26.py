"""Evaluate numeric-ID samples from yoloe26_card.py against COCO annotations."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval
from pycocotools import mask as maskutils

CATEGORIES=[1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,18,19,20,21,22,23,24,25,27,28,31,32,33,34,35,36,37,38,39,40,41,42,43,44,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,67,70,72,73,74,75,76,77,78,79,80,81,82,84,85,86,87,88,89,90]
def main():
 p=argparse.ArgumentParser();p.add_argument('--result',type=Path,required=True);p.add_argument('--annotations',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 assert not a.output.exists();report=json.loads((a.result/'deployment-result.json').read_text(encoding='utf-8'));assert report['completed'] and report['modelId']=='yoloe-26n-seg'
 samples=[s for s in report['samples'] if s['kind'].isdigit()];ids=[int(s['kind']) for s in samples];assert ids and len(ids)==len(set(ids))
 gt=COCO(str(a.annotations));assert set(ids)<=set(gt.getImgIds());predictions={'bbox':[],'segm':[]}
 for s in samples:
  file=a.result/s['rawResult']['file'];assert hashlib.sha256(file.read_bytes()).hexdigest()==s['rawResult']['sha256'];data=np.load(file,allow_pickle=False)
  assert len(data['predictions'])==len(data['boxes'])==len(data['masks'])
  for row,box,mask in zip(data['predictions'],data['boxes'],data['masks']):
   assert np.isfinite(row).all() and np.isfinite(box).all();base={'image_id':int(s['kind']),'category_id':CATEGORIES[int(row[5])],'score':float(row[4])};x1,y1,x2,y2=box
   predictions['bbox'].append({**base,'bbox':[float(x1),float(y1),float(x2-x1),float(y2-y1)]})
   encoded=maskutils.encode(np.asfortranarray(mask.astype(np.uint8)));predictions['segm'].append({**base,'segmentation':encoded})
 metrics={}
 for kind,rows in predictions.items():
  if rows:det=gt.loadRes(rows)
  else:
   det=COCO();det.dataset={'images':[gt.imgs[i] for i in ids],'categories':list(gt.cats.values()),'annotations':[]};det.createIndex()
  e=COCOeval(gt,det,kind);e.params.imgIds=ids;e.evaluate();e.accumulate();e.summarize()
  metrics[kind]={'AP50_95':float(e.stats[0]),'AP50':float(e.stats[1]),'AP75':float(e.stats[2]),'AR100':float(e.stats[8]),'predictionCount':len(rows)}
 result={'imageIds':ids,'imageCount':len(ids),'scope':'Only the listed images; not a full-dataset claim. Repeat and synthetic blank are excluded.','settings':report['settings'],'annotationSha256':hashlib.sha256(a.annotations.read_bytes()).hexdigest(),'metrics':metrics}
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Saved',a.output)
if __name__=='__main__':main()
