"""H-GTCRN offline WAV enhancement with explicit AXCL and silence-safe WPE."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse,hashlib,json,sys,time,types,wave
from pathlib import Path
import axengine
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
sys.path.insert(0,str(root/'python'))
from h_gtcrn_core_sdk import ModelSession
source=(root/'python/audio_demo.py').read_text()
needle='eps = 1e-3 * np.mean(np.max(np.max(np.abs(X) ** 2, axis=-1), axis=0))'
assert source.count(needle)==1
patched=source.replace(needle,needle+'\n    eps = max(float(eps), 1e-12)')
report={'modelId':'H-GTCRN.AXERA','provider':'AXCLRTExecutionProvider','completed':False,'sessions':[],'results':[],
 'upstreamScriptSha256':hashlib.sha256(source.encode()).hexdigest(),'wpePatch':'Floor energy-dependent WPE epsilon at 1e-12 to prevent division by zero on silence.',
 'timingScope':'Full offline main call, CPU WPE/IVA/STFT/ISTFT, AXCL, checks and WAV save; excludes initial model load and second pass.'}
def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
start=time.perf_counter();sdk=ModelSession(str(root/'models/model.axmodel'),providers=['AXCLRTExecutionProvider'])
session_record={'model':'models/model.axmodel','loadSeconds':time.perf_counter()-start,
 'inputs':[{'name':v.name,'shape':list(v.shape),'dtype':str(v.dtype)} for v in sdk.session.get_inputs()],
 'outputs':[{'name':v.name,'shape':list(v.shape)} for v in sdk.session.get_outputs()],
 'runMilliseconds':[],'allFinite':True,'inputHashes':[],'outputHashes':[]}
report['sessions'].append(session_record);save()
original_run=sdk.run_named
def measured(feeds):
    for m in sdk.session.get_inputs():
        v=feeds[m.name];assert v.shape==tuple(m.shape) and v.dtype==np.dtype(m.dtype);assert np.isfinite(v).all()
    session_record['inputHashes'].append(hashlib.sha256(feeds['feat'].tobytes()).hexdigest())
    start=time.perf_counter();values=original_run(feeds);session_record['runMilliseconds'].append((time.perf_counter()-start)*1000)
    session_record['allFinite'] &= all(np.isfinite(v).all() for v in values.values());assert session_record['allFinite']
    session_record['outputHashes'].append(hashlib.sha256(values['mask'].tobytes()).hexdigest())
    return values
sdk.run_named=measured
def module(text):
    m=types.ModuleType('official_hgtcrn');m.__file__=str(root/'python/audio_demo.py');exec(compile(text,m.__file__,'exec'),m.__dict__)
    def reuse(path):
        assert Path(path).resolve()==root/'models/model.axmodel';return sdk
    m.ModelSession=reuse
    return m
baseline=module(source);fixed=module(patched)
def run(m,path,name):
    captured=[];original=m.write_wav
    def capture(path,value,sr=16000):
        assert np.isfinite(value).all();captured.append(value.copy());return original(path,value,sr)
    m.write_wav=capture
    sys.argv=['audio_demo.py','--model',str(root/'models/model.axmodel'),'--input-wav',str(path),'--output',str(out/(name+'.wav'))]
    start=time.perf_counter()
    try:
        with np.errstate(divide='raise',invalid='raise',over='raise'):m.main()
    finally:m.write_wav=original
    assert len(captured)==1
    return captured[0],time.perf_counter()-start
official=root/'samples/Samples1_noisy.wav'
with wave.open(str(official)) as f:
    assert f.getframerate()==16000 and f.getsampwidth()==2 and f.getnchannels()==2
    pcm=np.frombuffer(f.readframes(f.getnframes()),'<i2').reshape(-1,2)
def pcm_wav(path,values):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1 if values.ndim==1 else values.shape[1]);f.setsampwidth(2);f.setframerate(16000);f.writeframes(values.astype('<i2').tobytes())
stereo=out/'stereo-input.wav';stereo.write_bytes(official.read_bytes())
for index,name in enumerate(['mono-left','mono-right']):pcm_wav(out/(name+'-input.wav'),pcm[:,index])
silence=out/'silence-input.wav';pcm_wav(silence,np.zeros((32000,2),np.int16))
before=len(session_record['runMilliseconds'])
try:run(baseline,silence,'silence-unpatched')
except FloatingPointError as e:report['unpatchedSilence']={'error':str(e),'beforeNpu':len(session_record['runMilliseconds'])==before}
else:raise AssertionError('Expected zero-input failure did not reproduce')
reference,_=run(baseline,stereo,'stereo-unpatched')
baseline_input=session_record['inputHashes'][-1];baseline_output=session_record['outputHashes'][-1]
for name in ['stereo','mono-left','mono-right','silence']:
    path=out/(name+'-input.wav');start_index=len(session_record['outputHashes'])
    result,elapsed=run(fixed,path,name+'-output');repeat,repeat_elapsed=run(fixed,path,name+'-repeat')
    assert np.array_equal(result,repeat) and session_record['inputHashes'][start_index]==session_record['inputHashes'][start_index+1]
    assert session_record['outputHashes'][start_index]==session_record['outputHashes'][start_index+1]
    if name=='stereo':
        report['nonzeroBaselineExact']=bool(np.array_equal(reference,result) and session_record['inputHashes'][start_index]==baseline_input and session_record['outputHashes'][start_index]==baseline_output)
        assert report['nonzeroBaselineExact']
    with wave.open(str(path)) as f:channels=f.getnchannels();samples=f.getnframes()
    assert len(result)==samples
    row={'name':name,'sourceFile':official.name if name=='stereo' else 'derived-'+name,'channels':channels,'samples':samples,'sampleRate':16000,
     'durationSeconds':samples/16000,'pipelineSeconds':elapsed,'repeatPipelineSeconds':repeat_elapsed,'realTimeFactor':elapsed/(samples/16000),
     'npuCallsPerPass':1,'repeatExact':True,'allFinite':True,'outputRms':float(np.sqrt(np.mean(result.astype(np.float64)**2))),
     'outputPeak':float(np.max(np.abs(result))),'outputClippedFraction':float(np.mean(np.abs(result)>=1)),
     'inputSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'outputSha256':hashlib.sha256((out/(name+'-output.wav')).read_bytes()).hexdigest()}
    if name=='silence':assert row['outputPeak']==0
    np.savez_compressed(out/(name+'-raw.npz'),output=result)
    report['results'].append(row);save();print('RESULT',json.dumps(row),flush=True)
report['referenceComparisons']=[]
def pcm(path):
    with wave.open(str(path)) as f:
        assert f.getframerate()==16000 and f.getnchannels()==1 and f.getsampwidth()==2
        return np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(np.float64)/32768
actual_pcm=pcm(out/'stereo-output.wav')
for file in ['Samples1_core_ref_enhanced.wav','Samples1_board_enhanced.wav']:
    path=root/'samples'/file;ref=pcm(path);assert ref.shape==actual_pcm.shape
    cosine=float(np.dot(ref,actual_pcm)/(np.linalg.norm(ref)*np.linalg.norm(actual_pcm)))
    report['referenceComparisons'].append({'reference':file,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
     'cosine':cosine,'meanAbsoluteDelta':float(np.mean(np.abs(ref-actual_pcm))),'maxAbsoluteDelta':float(np.max(np.abs(ref-actual_pcm))),
     'scope':'PCM16 sample-by-sample, no alignment or scaling; supplied upstream output, not independent clean speech ground truth.'})
report['completed']=True;save()
