"""Exercise the official GCRN chunked DSP with an explicit AXCL provider."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,hashlib,json,shutil,sys,time,wave
from pathlib import Path
import axengine
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
report={'modelId':'GCRN','provider':'AXCLRTExecutionProvider','completed':False,'sessions':[],'results':[],
 'upstreamSha256':{name:hashlib.sha256((root/'python/gcrn_sdk'/name).read_bytes()).hexdigest() for name in ['audio.py','inference.py','runtime.py']},
 'timingScope':'One complete enhance call, including zero-input warmup, chunk DSP, AXCL and recording; excludes model load, WAV read/save and second pass.'}
def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
original=axengine.InferenceSession
class MeasuredSession:
    def __init__(self,path):
        start=time.perf_counter();self.session=original(path,providers=['AXCLRTExecutionProvider'])
        self.record={'model':Path(path).relative_to(root).as_posix(),'loadSeconds':time.perf_counter()-start,
         'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.session.get_inputs()],
         'outputs':[{'name':m.name,'shape':list(m.shape)} for m in self.session.get_outputs()],
         'allFinite':True,'runMilliseconds':[],'outputHashes':[]}
        report['sessions'].append(self.record);save()
    def get_inputs(self):return self.session.get_inputs()
    def get_outputs(self):return self.session.get_outputs()
    def run(self,names,feeds):
        for m in self.get_inputs():
            value=feeds[m.name];assert value.shape==tuple(m.shape) and value.dtype==np.dtype(m.dtype);assert np.isfinite(value).all()
        start=time.perf_counter();values=self.session.run(names,feeds);self.record['runMilliseconds'].append((time.perf_counter()-start)*1000)
        self.record['allFinite'] &= all(np.isfinite(v).all() for v in values);assert self.record['allFinite']
        self.record['outputHashes'].append([hashlib.sha256(v.tobytes()).hexdigest() for v in values]);return values
axengine.InferenceSession=MeasuredSession
sys.path.insert(0,str(root/'python'))
from gcrn_sdk import GCRNDenoiser
from gcrn_sdk.audio import read_wav,write_wav
denoiser=GCRNDenoiser(root/'models/model.axmodel',backend='axengine');rec=report['sessions'][0]
source=root/'test_audio/mix.wav';pcm,sr=read_wav(source);assert sr==16000 and len(pcm)>128000
report['sourceSha256']=hashlib.sha256(source.read_bytes()).hexdigest()
def input_wav(path,values):
    with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes(values.astype('<i2').tobytes())
outputs={}
for name,values in [('official',pcm),('silence',np.zeros(32000,np.int16)),('below-4s',pcm[:63999]),('exact-4s',pcm[:64000]),('above-4s',pcm[:64001])]:
    input_path=out/(name+'-input.wav')
    if name=='official':shutil.copy2(source,input_path)
    else:input_wav(input_path,values)
    first=len(rec['outputHashes']);start=time.perf_counter();result=denoiser.enhance(values);elapsed=time.perf_counter()-start;mid=len(rec['outputHashes'])
    start=time.perf_counter();repeat=denoiser.enhance(values);repeat_seconds=time.perf_counter()-start
    assert np.array_equal(result,repeat) and np.isfinite(result).all() and result.shape==values.shape
    assert rec['outputHashes'][first:mid]==rec['outputHashes'][mid:]
    blocks=(len(values)+63999)//64000;assert mid-first==blocks+1
    output_path=out/(name+'-output.wav');write_wav(output_path,result,sr)
    np.savez_compressed(out/(name+'-raw.npz'),input=values.astype(np.float32)/32768,output=result)
    boundaries=[{'sample':i,'seconds':i/sr,'inputAdjacentJump':float((int(values[i])-int(values[i-1]))/32768),
      'outputAdjacentJump':float(result[i]-result[i-1])} for i in range(64000,len(values),64000)]
    row={'name':name,'sampleRate':sr,'samples':len(result),'durationSeconds':len(result)/sr,'pipelineSeconds':elapsed,'repeatPipelineSeconds':repeat_seconds,
      'realTimeFactor':elapsed/(len(result)/sr),'dataChunks':blocks,'warmupCallsPerPass':1,'npuCallsPerPass':mid-first,
      'repeatExact':True,'allFinite':True,'outputRms':float(np.sqrt(np.mean(result.astype(np.float64)**2))),
      'outputPeak':float(np.max(np.abs(result))),'outputClippedFraction':float(np.mean(np.abs(result)>=1)),
      'inputSha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),'outputSha256':hashlib.sha256(output_path.read_bytes()).hexdigest(),'boundaries':boundaries}
    outputs[name]=result;report['results'].append(row);save();print('RESULT',json.dumps(row),flush=True)
report['chunkChecks']={'exact4sEqualsOfficialFirstChunk':bool(np.array_equal(outputs['exact-4s'],outputs['official'][:64000])),
 'above4sPreservesFirstChunk':bool(np.array_equal(outputs['above-4s'][:64000],outputs['exact-4s']))}
assert all(report['chunkChecks'].values())
report['completed']=True;save()
