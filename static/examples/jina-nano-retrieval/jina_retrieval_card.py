"""Run text, image, fixed-duration audio and frame-directory retrieval on an AXCL card."""
import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,json,time
from pathlib import Path
import numpy as np
from jina_retrieval_core import Retrieval,media,MID,REV
from jina_retrieval_native_session import configure

def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 requests=json.loads(a.inputs.read_text(encoding='utf-8'));assert isinstance(requests,list) and 1<=len(requests)<=32
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 configure(Path(__file__).with_name('jina-retrieval-shapes.json'),out/'native-calls');engine=Retrieval(a.model_dir.resolve())
 result={'modelId':MID,'revision':REV,'provider':'AXCLNativeAPI','completed':False,'calls':[]}
 save=lambda:(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 save()
 for i,request in enumerate(requests):
  start=time.monotonic();kind=request.get('modality','text');role=request.get('role','query')
  if kind=='text':r=engine.text(request['text'],role)
  else:
   assert kind in ['image','audio','video'];path=Path(request['file']);path=path if path.is_absolute() else a.inputs.resolve().parent/path
   if kind=='video':
    assert path.is_dir(),'Video input is a directory of explicitly selected frames.'
    paths=sorted(p for p in path.iterdir() if p.suffix.lower() in ['.png','.jpg','.jpeg']);assert 1<=len(paths)<=15
   else:assert path.is_file();paths=[path]
   r=media(engine,paths,kind,role,request.get('audioSeconds',8))
  r.update(id=request.get('id',str(i)),requestSeconds=time.monotonic()-start);result['calls'].append(r);save()
  print(json.dumps({'id':r['id'],'modality':kind,'tokens':r['tokenCount'],'dimensions':len(r['embedding']),'seconds':r['requestSeconds']},ensure_ascii=False),flush=True)
 result['similarityMatrix']=[[float(np.dot(x['embedding'],y['embedding'])) for y in result['calls']] for x in result['calls']]
 result['completed']=True;save()
if __name__=='__main__':main()
