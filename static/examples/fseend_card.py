"""Run both fixed official LS-EEND streaming variants on an AXCL card."""
import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import axengine
import numpy as np
import soundfile as sf

p=argparse.ArgumentParser()
p.add_argument('--model-dir',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--audio',type=Path)
a=p.parse_args();root,out=a.model_dir.resolve(),a.output.resolve()
assert not out.exists(),'Choose a new output directory'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda v:hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()
hashes={'__init__.py':'14554ffd7ba206e7d2eae3ef62e5d53532fcf2666fd9da42d08f87476881e124',
 'diarize.py':'3e88fe9267e3cfe18dc70d5b26a6af232d4927d7afbaa9f2a83c2b8567bb042c',
 'feature.py':'f37e521523ea864ccf8b262cbb55da7c7843fd3c836f1697da40f643b933b413',
 'postprocess.py':'d383300e20440a4d09512d4066a746476c6d1e5cc9267ecd51700715a95a10b3',
 'session.py':'16e7d2478303ab3a2da75451b571e9b10a08a0a75cdc4155ded6dcf3d223f559'}
for name,value in hashes.items():assert sha(root/'python/ls_eend_sdk'/name)==value
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
out.mkdir(parents=True)
audio=(a.audio or root/'samples/mix_0000176.wav').resolve()
shutil.copy2(audio,out/'input.wav')
shutil.copy2(root/'samples/ground_truth_4spk_mix176.rttm',out/'reference.rttm')
silence=out/'silence.wav';sf.write(silence,np.zeros(24000,dtype=np.float32),8000,subtype='PCM_16')
report={'modelId':'FS-EEND.AXERA','provider':'AXCLRTExecutionProvider','completed':False,
 'sourceHashes':hashes,'audioSha256':sha(audio),'referenceSha256':sha(out/'reference.rttm'),
 'referenceApplies':not bool(a.audio),'settings':{'maxSpeakers':4,'threshold':.5,'median':11,'convDelayFrames':9,'frameSeconds':.1},
 'sessions':[],'samples':[]}
current=0;frame=0;raw_preds=[]
original=axengine.InferenceSession


def save():
    (out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def chain(values):
    h=hashlib.sha256()
    for name,value in values:
        h.update(name.encode());h.update(np.ascontiguousarray(value).tobytes())
    return h.hexdigest()


class Measured:
    def __init__(self,path,providers=None):
        assert providers==['AXCLRTExecutionProvider']
        t=time.perf_counter();self.engine=original(path,providers=providers)
        self.record={'model':str(Path(path).resolve().relative_to(root)),'weightSha256':sha(Path(path)),
                     'loadSeconds':time.perf_counter()-t,'allFinite':True,'runMilliseconds':[],'calls':[],
                     'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.engine.get_inputs()],
                     'outputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.engine.get_outputs()]}
        report['sessions'].append(self.record);save()
    def get_inputs(self):return self.engine.get_inputs()
    def get_outputs(self):return self.engine.get_outputs()
    def run(self,names,feeds):
        global frame
        frame+=1
        for m in self.engine.get_inputs():
            assert feeds[m.name].shape==tuple(m.shape) and feeds[m.name].dtype==np.dtype(m.dtype)
            assert np.isfinite(feeds[m.name]).all()
        if frame<=10:
            assert all(not np.any(feeds[f'dec{i}_kv']) for i in range(2)),'Decoder changed before first emitted frame'
        assert np.allclose(feeds['inv_count'],np.float32(1/frame),rtol=0,atol=0)
        assert np.allclose(feeds['dec_inv_count'],np.float32(1/max(frame-9,1)),rtol=0,atol=0)
        t=time.perf_counter();values=self.engine.run(names,feeds);ms=(time.perf_counter()-t)*1000
        assert all(np.isfinite(v).all() for v in values)
        self.record['runMilliseconds'].append(ms)
        self.record['calls'].append({'sampleIndex':current,'frame':frame,'inputHash':chain(feeds.items()),
          'outputHash':chain((m.name,v) for m,v in zip(self.engine.get_outputs(),values)),
          'featureHash':digest(feeds['feat']),'predHash':digest(values[0])})
        raw_preds.append(values[0].copy())
        return values


sys.path.insert(0,str(root/'python'))
from ls_eend_sdk import StreamingDiarizer, wav_to_features, to_activity, to_segments, write_rttm
axengine.InferenceSession=Measured
try:
    for variant in ['simu','ami']:
        model=StreamingDiarizer(root/'models'/variant/'streaming_step.axmodel',providers=['AXCLRTExecutionProvider'])
        assert model.slots=={'simu':10,'ami':6}[variant]
        for label,wav in [('official' if not a.audio else 'custom',audio),('repeat',audio),('silence',silence)]:
            current+=1;frame=0;raw_preds=[]
            t=time.perf_counter();features,duration=wav_to_features(wav);prep=time.perf_counter()-t
            assert features.shape[1]==345 and len(features)>9 and np.isfinite(features).all() and 0<duration<=600
            t=time.perf_counter();logits=model.run(features,progress=500);elapsed=time.perf_counter()-t
            activity=to_activity(logits,max_speakers=4,threshold=.5,median=11)
            segments=to_segments(activity,duration=duration)
            rttm=out/f'{variant}-{label}.rttm';write_rttm(segments,rttm,uri=wav.stem)
            raw=out/f'{variant}-{label}.npz'
            np.savez_compressed(raw,features=features,allPreds=np.concatenate(raw_preds).reshape(len(features),model.slots),logits=logits,activity=activity)
            row={'variant':variant,'kind':label,'input':wav.name,'audioSha256':sha(wav),'audioSeconds':duration,
                 'featureFrames':len(features),'emittedFrames':len(logits),'outputChannels':model.slots,
                 'preprocessingSeconds':prep,'inferenceSeconds':elapsed,'rtf':elapsed/duration,
                 'segments':segments,'activeSpeakers':int(activity.any(axis=0).sum()),
                 'rawFile':raw.name,'rawSha256':sha(raw),'rttmFile':rttm.name,'rttmSha256':sha(rttm)}
            report['samples'].append(row);save();print(json.dumps(row,ensure_ascii=False),flush=True)
    report['completed']=True;save()
finally:
    axengine.InferenceSession=original
