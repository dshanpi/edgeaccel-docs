"""Run fixed official CAM++ extraction and chunking with AXCL."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import time
from pathlib import Path

import axengine
import numpy as np
import soundfile as sf
import torch
import torchaudio

p=argparse.ArgumentParser()
p.add_argument('--model-dir',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--audio',type=Path,action='append')
a=p.parse_args()
root,out=a.model_dir.resolve(),a.output.resolve()
assert not out.exists(),'Choose a new output directory'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda v:hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()
source=root/'python/campplus_sdk/inference.py'
assert sha(source)=='489a464c2d70143f0d4503ac010aa7a9a38eda2a86f3632f9d8e670c220aa5b0'
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
torch.set_num_threads(2)
out.mkdir(parents=True)
report={'modelId':'campplus.AXERA','provider':'AXCLRTExecutionProvider','completed':False,
        'sourceSha256':sha(source),'torchVersion':torch.__version__,'torchaudioVersion':torchaudio.__version__,
        'sessions':[],'samples':[],'pairs':[],'featureScope':'Official extract uses the first 360 frames after circle-padding to at least 57900 samples; chunk mode uses official 1.5s/0.75s windows.'}
current=0
features=[]
embeddings=[]
original_session=axengine.InferenceSession


def save():
    (out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


class Measured:
    def __init__(self,path,providers=None):
        assert providers=='AxEngineExecutionProvider'
        t=time.perf_counter()
        self.engine=original_session(path,providers=['AXCLRTExecutionProvider'])
        self.record={'model':str(Path(path).resolve().relative_to(root)),'weightSha256':sha(Path(path)),
                     'loadSeconds':time.perf_counter()-t,'allFinite':True,'runMilliseconds':[],'calls':[],
                     'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.engine.get_inputs()],
                     'outputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.engine.get_outputs()]}
        report['sessions'].append(self.record)

    def get_inputs(self):return self.engine.get_inputs()

    def run(self,names,feeds):
        for m in self.engine.get_inputs():
            assert feeds[m.name].shape==tuple(m.shape) and feeds[m.name].dtype==np.dtype(m.dtype)
            assert np.isfinite(feeds[m.name]).all()
        t=time.perf_counter();values=self.engine.run(names,feeds);ms=(time.perf_counter()-t)*1000
        assert len(values)==1 and values[0].shape==(1,192) and np.isfinite(values[0]).all()
        assert np.linalg.norm(values[0])>0
        self.record['runMilliseconds'].append(ms)
        self.record['calls'].append({'sampleIndex':current,'inputSha256':digest(next(iter(feeds.values()))),'outputSha256':digest(values[0])})
        features.append(next(iter(feeds.values())).copy());embeddings.append(values[0].copy())
        return values


spec=importlib.util.spec_from_file_location('verified_campplus_inference',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
axengine.InferenceSession=Measured
try:
    model=module.CampplusModel(str(root/'models'))
    files=[p.resolve() for p in a.audio] if a.audio else sorted((root/'samples').glob('*.wav'))
    assert files
    whole=[]
    for mode in ['extract','chunked']:
        for idx,audio in enumerate(files+[files[0]]):
            current+=1;features=[];embeddings=[]
            info=sf.info(audio);assert info.samplerate==16000 and info.channels==1 and 0<info.duration<=60,'Use 16kHz mono WAV within60s'
            saved=out/f'input-{current}.wav';shutil.copy2(audio,saved)
            wav=module.load_wav(str(audio))
            assert wav.shape==(1,info.frames) and np.isfinite(wav.numpy()).all()
            chunks=module.chunk(0,info.duration) if mode=='chunked' else None
            assert chunks or mode=='extract','Audio too short for official chunk mode'
            t=time.perf_counter()
            result=model(wav.numpy()[0],16000,chunks=chunks) if mode=='chunked' else model.extract(wav)
            elapsed=time.perf_counter()-t
            raw=out/f'raw-{current}.npz'
            np.savez_compressed(raw,features=np.concatenate(features),embeddings=result)
            assert np.array_equal(result,np.concatenate(embeddings))
            row={'input':audio.name,'mode':mode,'repeat':idx==len(files),'audioFile':saved.name,'audioSha256':sha(saved),
                 'audioSeconds':info.duration,'chunks':chunks,'embeddingShape':list(result.shape),
                 'processSeconds':elapsed,'rtf':elapsed/info.duration,'calls':len(embeddings),'rawFile':raw.name,'rawSha256':sha(raw)}
            report['samples'].append(row)
            if mode=='extract' and idx<len(files):whole.append((audio.name,result.copy()))
            save();print(json.dumps(row,ensure_ascii=False),flush=True)
    for i in range(len(whole)):
        for j in range(i+1,len(whole)):
            report['pairs'].append({'left':whole[i][0],'right':whole[j][0],'cosine':module.cosine_similarity(whole[i][1],whole[j][1])})
    report['completed']=True;save()
finally:
    axengine.InferenceSession=original_session
