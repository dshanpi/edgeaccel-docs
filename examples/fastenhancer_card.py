"""Run the official FastEnhancer streaming DSP with explicit AXCL neural core."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,hashlib,json,shutil,subprocess,sys,time,wave
from pathlib import Path
import axengine
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
p.add_argument('--rate',choices=['16k','48k'],required=True);a=p.parse_args()
root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
report={'modelId':'fastenhancer.axera','provider':'AXCLRTExecutionProvider','variant':a.rate,'completed':False,'sessions':[],'results':[],
 'upstreamScriptSha256':hashlib.sha256((root/'python/fastenhancer_sdk/inference.py').read_bytes()).hexdigest()}
def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
original=axengine.InferenceSession
class MeasuredSession:
    def __init__(self,path):
        start=time.perf_counter();self.session=original(path,providers=['AXCLRTExecutionProvider'])
        self.record={'model':Path(path).relative_to(root).as_posix(),'loadSeconds':time.perf_counter()-start,
          'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.session.get_inputs()],
          'outputs':[{'name':m.name,'shape':list(m.shape)} for m in self.session.get_outputs()],
          'runMilliseconds':[],'allFinite':True,'outputHashes':[]}
        report['sessions'].append(self.record);save()
    def run(self,names,feeds):
        for m in self.session.get_inputs():
            value=feeds[m.name];assert value.shape==tuple(m.shape) and value.dtype==np.dtype(m.dtype),(m.name,value.shape,value.dtype)
            assert np.isfinite(value).all()
        start=time.perf_counter();values=self.session.run(names,feeds)
        self.record['runMilliseconds'].append((time.perf_counter()-start)*1000)
        self.record['allFinite'] &= all(np.isfinite(v).all() for v in values);assert self.record['allFinite']
        self.record['outputHashes'].append([hashlib.sha256(v.tobytes()).hexdigest() for v in values]);return values
axengine.InferenceSession=MeasuredSession
sys.path.insert(0,str(root/'python'))
from fastenhancer_sdk import FastEnhancer
fe=FastEnhancer(str(root/'models'/a.rate/'model.axmodel'));rate=fe.sr
source=root/'samples/p232_013_original.wav';prepared=out/'official-input.wav'
with wave.open(str(source),'rb') as f:assert f.getframerate()==48000 and f.getnchannels()==1 and f.getsampwidth()==2
if rate==16000:
    subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-n','-i',str(source),'-ac','1','-ar','16000','-c:a','pcm_s16le',str(prepared)],check=True)
    report['resampling']='FFmpeg default swresample: mono 48000 Hz PCM16 -> mono 16000 Hz PCM16'
else:
    shutil.copy2(source,prepared);report['resampling']='None; original 48000 Hz PCM16 samples'
report['sourceAudioSha256']=hashlib.sha256(source.read_bytes()).hexdigest()
def readwav(path):
    with wave.open(str(path),'rb') as f:
        assert f.getframerate()==rate and f.getnchannels()==1 and f.getsampwidth()==2
        return np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768.0
def writewav(path,value):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((np.clip(value,-1,1)*32767).astype('<i2').tobytes())
for name,input_audio in [('official',readwav(prepared)),('silence',np.zeros(rate*2,np.float32))]:
    input_path=out/(name+'-input.wav')
    if name=='silence':writewav(input_path,input_audio)
    start_index=len(fe.session.record['outputHashes']);start=time.perf_counter();result=fe.enhance(input_audio);elapsed=time.perf_counter()-start
    mid=len(fe.session.record['outputHashes']);repeated=fe.enhance(input_audio)
    assert np.array_equal(result,repeated) and np.isfinite(result).all() and result.shape==input_audio.shape
    assert fe.session.record['outputHashes'][start_index:mid]==fe.session.record['outputHashes'][mid:]
    output_path=out/(name+'-output.wav');writewav(output_path,result)
    np.savez_compressed(out/(name+'-raw.npz'),input=input_audio,output=result)
    rms_in=float(np.sqrt(np.mean(input_audio.astype(np.float64)**2)));rms_out=float(np.sqrt(np.mean(result.astype(np.float64)**2)))
    row={'name':name,'sampleRate':rate,'samples':len(result),'durationSeconds':len(result)/rate,'inputSha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),
      'outputSha256':hashlib.sha256(output_path.read_bytes()).hexdigest(),'pipelineSeconds':elapsed,'realTimeFactor':elapsed/(len(result)/rate),
      'npuCallsPerPass':mid-start_index,'repeatExact':True,'allFinite':True,'inputRms':rms_in,'outputRms':rms_out,
      'outputPeak':float(np.max(np.abs(result))),'outputClippedFraction':float(np.mean(np.abs(result)>=1)),
      'rmsChangePercent':100*(rms_out/rms_in-1) if rms_in else None}
    report['results'].append(row);save();print(name,json.dumps(row),flush=True)
report['completed']=True;save()
