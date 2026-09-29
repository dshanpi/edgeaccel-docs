"""Official openWakeWord DSP with AXCL embedding/classifiers and recorded scores."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse,hashlib,json,shutil,sys,time,wave
from pathlib import Path
import axengine
import numpy as np

p=argparse.ArgumentParser()
p.add_argument('--model-dir',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--mode',choices=['wake-word','wake-word-npu-mel','mel-probe'],default='wake-word')
a=p.parse_args();root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
report={'modelId':'OpenWakeWord.AXERA','provider':'AXCLRTExecutionProvider','mode':a.mode,'completed':False,
        'sessions':[],'results':[],'cpuMel':a.mode=='wake-word','threshold':0.5,'chunkSeconds':0.08,'initialZeroScoreFrames':5,
        'blasThreads':1,'sourceSha256':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in ['scripts/openwakeword_ax.py','scripts/runtime.py']}}
report['timerClassMapping']={'1':'1_minute_timer','2':'5_minute_timer','3':'10_minute_timer','4':'20_minute_timer','5':'30_minute_timer','6':'1_hour_timer'}
report['timerMappingSource']='https://github.com/dscripka/openWakeWord/blob/368c03716d1e92591906a84949bc477f3a834455/openwakeword/__init__.py'
def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
original=axengine.InferenceSession
class MeasuredSession:
    def __init__(self,path,providers):
        assert providers==['AxEngineExecutionProvider']
        start=time.perf_counter();self.session=original(path,providers=['AXCLRTExecutionProvider'])
        self.record={'model':Path(path).relative_to(root).as_posix(),'loadSeconds':time.perf_counter()-start,
          'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.session.get_inputs()],
          'outputs':[{'name':m.name,'shape':list(m.shape)} for m in self.session.get_outputs()],
          'runMilliseconds':[],'allFinite':True,'outputHashes':[]}
        report['sessions'].append(self.record);save()
    def __getattr__(self,name):return getattr(self.session,name)
    def run(self,names,feeds):
        for m in self.session.get_inputs():
            v=feeds[m.name];assert v.shape==tuple(m.shape) and v.dtype==np.dtype(m.dtype),(m.name,v.shape,v.dtype)
            assert np.isfinite(v).all()
        start=time.perf_counter();values=self.session.run(names,feeds)
        self.record['runMilliseconds'].append((time.perf_counter()-start)*1000)
        self.record['allFinite'] &= all(np.isfinite(v).all() for v in values)
        assert self.record['allFinite']
        self.record['outputHashes'].append([hashlib.sha256(v.tobytes()).hexdigest() for v in values])
        return values
axengine.InferenceSession=MeasuredSession
sys.path.insert(0,str(root/'scripts'))
source=(root/'scripts/openwakeword_ax.py').read_text()
needle='return {\n        "audio": str(audio_path),'
assert source.count(needle)==1
source=source.replace(needle,'return {\n        "frame_scores": scores,\n        "audio": str(audio_path),')
ns={'__name__':'openwakeword_official_helpers','__file__':str(root/'scripts/openwakeword_ax.py')}
exec(compile(source,ns['__file__'],'exec'),ns)
weights=ns['load_mel_weights'](root/'config/openwakeword_mel_weights.npz')
audio_files=sorted((root/'audio/openwakeword').glob('*.wav'));assert len(audio_files)==3
silence=out/'silence-4s.wav'
with wave.open(str(silence),'wb') as f:
    f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(np.zeros(64000,dtype='<i2').tobytes())
audio_files.append(silence)
if a.mode=='mel-probe':
    session=ns['InferenceSession'](root/'models/650/openwakeword__melspectrogram.axmodel','axengine')
    for path in audio_files:
        samples,sr=ns['read_wav'](path);assert sr==16000
        samples=ns['pad_chunks'](samples);chunks=samples.reshape(-1,1280)
        peak=int(np.argmax(np.mean(chunks.astype(np.float64)**2,axis=1)))
        for index in sorted(set([0,peak])):
            start=index*1280;history=np.pad(samples[max(0,start-480):start],(max(0,480-start),0))
            frame=np.concatenate([history,chunks[index]]).astype(np.float32)[None,:]
            values=session.run({session.inputs[0].name:frame});value=ns['first_output'](session,values)
            repeated=ns['first_output'](session,session.run({session.inputs[0].name:frame}))
            cpu=ns['numpy_melspectrogram'](frame,weights)
            assert value.shape==cpu.shape and np.array_equal(value,repeated)
            np.savez_compressed(out/(path.stem+'-'+str(index)+'-mel.npz'),input=frame,npu=value,cpu=cpu)
            report['results'].append({'audio':path.name,'windowIndex':index,'inputNonzero':int(np.count_nonzero(frame)),
              'npuNonzero':int(np.count_nonzero(value)),'cpuNonzero':int(np.count_nonzero(cpu)),
              'npuRange':[float(value.min()),float(value.max())],'cpuRange':[float(cpu.min()),float(cpu.max())],
              'maxAbsDelta':float(np.max(np.abs(value.astype(np.float64)-cpu))),'repeatExact':True})
    report['nonzeroOutputObserved']=all(r['npuNonzero']>0 for r in report['results'] if r['inputNonzero']>0)
else:
    mel_backend='numpy' if a.mode=='wake-word' else 'model'
    sessions=ns['load_sessions'](root/'models/650','axengine',mel_backend)
    refs=ns['reference_by_audio'](root/'reference/local_inference_results.json')
    for path in audio_files:
        samples,sr=ns['read_wav'](path);assert sr==16000
        target=out/(path.stem+'-input.wav')
        if target!=path:shutil.copy2(path,target)
        start_counts=[len(s['outputHashes']) for s in report['sessions']]
        start=time.perf_counter();row=ns['infer_clip'](path,sessions,refs.get(path.name),0.5,0.15,mel_backend,weights);elapsed=time.perf_counter()-start
        middle_counts=[len(s['outputHashes']) for s in report['sessions']]
        repeat=ns['infer_clip'](path,sessions,refs.get(path.name),0.5,0.15,mel_backend,weights)
        assert row==repeat
        for s,begin,mid in zip(report['sessions'],start_counts,middle_counts):assert s['outputHashes'][begin:mid]==s['outputHashes'][mid:]
        row['audio']=path.name;row['audioSha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        row.update(durationSeconds=len(samples)/sr,pipelineSeconds=elapsed,realTimeFactor=elapsed/(len(samples)/sr),repeatExact=True)
        row['detectionScores']={key:[max(frame[1:]) if key=='timer_v0.1' else max(frame) for frame in values] for key,values in row['frame_scores'].items()}
        row['thresholdWindows']={key:[i for i,value in enumerate(values) if value>=0.5] for key,values in row['detectionScores'].items()}
        row['triggeredModels']=[key for key,values in row['thresholdWindows'].items() if values]
        report['results'].append(row);save()
        print(path.name,row['max_scores'],row['triggeredModels'],flush=True)
    report['functionalChecks']={'alexaDetected':next(r for r in report['results'] if r['audio']=='alexa_test.wav')['expected_detected'],
      'mycroftDetected':next(r for r in report['results'] if r['audio']=='hey_mycroft_test.wav')['expected_detected'],
      'silenceNoTrigger':not report['results'][-1]['triggeredModels']}
report['completed']=True;save()
print(json.dumps({'completed':True,'mode':a.mode,'calls':{s['model']:len(s['runMilliseconds']) for s in report['sessions']}}))
