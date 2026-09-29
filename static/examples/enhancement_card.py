"""Run a declared official image enhancement example with the AXCL backend."""
import argparse
import hashlib
import json
import os
import runpy
import shutil
import sys
import time
from pathlib import Path
import axengine
import numpy as np
from PIL import Image

p=argparse.ArgumentParser()
p.add_argument('--model-dir',type=Path,required=True)
p.add_argument('--cases',type=Path,required=True)
p.add_argument('--case',required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
case=next(c for c in json.loads(a.cases.read_text()) if c['name']==a.case)
model=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
input_dir=out/'inputs';input_dir.mkdir();work=out/'outputs';work.mkdir()
input_file=model/case['input'];shutil.copy2(input_file,input_dir/input_file.name)
entry=model/case['entry'];weight=model/case['weight']
values={'model':str(model),'weight':str(weight),'input':str(input_file),'inputdir':str(input_dir),'out':str(work),
        'weight_literal':repr(str(weight)),'input_literal':repr(str(input_file)),'output_literal':repr(str(work/'comparison.png'))}
backup=entry.with_suffix('.py.upstream')
source=(backup if backup.exists() else entry).read_text(encoding='utf-8')
for old,new in case['patches']:
    replacement=new.format(**values)
    if old in source:
        assert source.count(old)==1
        if not backup.exists():backup.write_text(source,encoding='utf-8')
        source=source.replace(old,replacement)
    else:assert replacement in source,'Unexpected source version'
if case['patches']:entry.write_text(source,encoding='utf-8')
record={'modelId':case['modelId'],'case':case['name'],'provider':'AXCLRTExecutionProvider',
        'input':{'file':case['input'],'sha256':hashlib.sha256(input_file.read_bytes()).hexdigest()},'sessions':[],'outputs':[]}
def save():
    (out/'enhancement-result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
real_session=axengine.InferenceSession
class CardSession:
    def __init__(self,path,*args,**kwargs):
        file=Path(path).resolve()
        assert file.is_relative_to(model) and file.is_file()
        relative=file.relative_to(model).as_posix()
        assert relative in case['weights']
        kwargs.pop('providers',None)
        start=time.monotonic()
        self.inner=real_session(str(file),providers=['AXCLRTExecutionProvider'],**kwargs)
        self.data={'weight':relative,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'loadSeconds':time.monotonic()-start,
                   'inputs':[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in self.inner.get_inputs()],'calls':[]}
        record['sessions'].append(self.data);save()
    def __getattr__(self,key):return getattr(self.inner,key)
    def run(self,*args,**kwargs):
        start=time.monotonic()
        try:
            output=self.inner.run(*args,**kwargs)
            assert all(np.isfinite(v).all() for v in output),'Nonfinite model output'
        except Exception as exc:
            self.data['error']=repr(exc);save();raise
        self.data['calls'].append({'seconds':time.monotonic()-start,'outputs':[{'shape':list(v.shape),'dtype':str(v.dtype),'min':float(v.min()),'max':float(v.max())} for v in output]});save()
        return output
axengine.InferenceSession=CardSession
sys.path.insert(0,str(entry.parent))
sys.argv=[str(entry)]+[value.format(**values) for value in case['args']]
os.chdir(work);np.random.seed(20260923)
start=time.monotonic()
try:
    runpy.run_path(str(entry),run_name='__main__')
    record['seconds']=time.monotonic()-start
    assert all('error' not in s for s in record['sessions'])
    assert {s['weight'] for s in record['sessions'] if s['calls']}==set(case['weights']),'A required model stage did not execute'
    for file in sorted(work.rglob('*')):
        if file.suffix.lower() not in ['.png','.jpg','.jpeg','.gif']:continue
        with Image.open(file) as im:
            im.load();size=list(im.size);frames=getattr(im,'n_frames',1)
        record['outputs'].append({'file':file.relative_to(out).as_posix(),'size':size,'frames':frames,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    assert record['outputs'],'No new output image'
    record['exitCode']=0
except BaseException as exc:
    record.update(exitCode=1,error=repr(exc));raise
finally:
    save();print(json.dumps(record,ensure_ascii=False),flush=True)
