"""Run fixed official GTCRN DSP using AXCL, preserving every recurrent state."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse,hashlib,importlib.util,json,shutil,time
from pathlib import Path
import axengine
import librosa
import numpy as np
import soundfile as sf
import torch

p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
torch.set_num_threads(1)
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
report={'modelId':'gtcrn.axera','provider':'AXCLRTExecutionProvider','completed':False,'sessions':[],'results':[],
 'upstreamScriptSha256':hashlib.sha256((root/'demo_gtcrn_ax.py').read_bytes()).hexdigest(),
 'dsp':'Official denoise_audio unchanged: librosa default resampling, STFT sqrt periodic Hann, ISTFT sqrt symmetric Hann, length=None.',
 'timingScope':'First full denoise_audio call per input, including file read, resampling, DSP, AXCL, hash checks, logging and WAV save; excludes initial model load and second pass. First resampling may include JIT startup.'}
def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

class MeasuredSession:
    def __init__(self,path):
        start=time.perf_counter();self.session=axengine.InferenceSession(str(path),providers=['AXCLRTExecutionProvider'])
        self.record={'model':path.relative_to(root).as_posix(),'loadSeconds':time.perf_counter()-start,
         'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.session.get_inputs()],
         'outputs':[{'name':m.name,'shape':list(m.shape)} for m in self.session.get_outputs()],
         'allFinite':True,'runMilliseconds':[],'outputHashes':[]}
        assert len(self.session.get_inputs())==15 and len(self.session.get_outputs())==15
        report['sessions'].append(self.record);save()
    def run(self,names,feeds):
        for m in self.session.get_inputs():
            v=feeds[m.name];assert v.shape==tuple(m.shape) and v.dtype==np.dtype(m.dtype),(m.name,v.shape,v.dtype)
            assert np.isfinite(v).all()
        start=time.perf_counter();values=self.session.run(names,feeds)
        self.record['runMilliseconds'].append((time.perf_counter()-start)*1000)
        self.record['allFinite'] &= all(np.isfinite(v).all() for v in values);assert self.record['allFinite']
        h=hashlib.sha256()
        for v in values:h.update(v.tobytes())
        self.record['outputHashes'].append(h.hexdigest())
        return values

spec=importlib.util.spec_from_file_location('official_gtcrn',root/'demo_gtcrn_ax.py');official=importlib.util.module_from_spec(spec);spec.loader.exec_module(official)
model=root/'models/gtcrn_650.axmodel';session=MeasuredSession(model)
def reuse_session(path):
    assert Path(path).resolve()==model
    return session
official.InferenceSession=reuse_session
# Disable only the progress display; all official signal and cache operations stay unchanged.
official.tqdm=lambda iterable,**kwargs:iterable
silence=out/'silence-source.wav';sf.write(silence,np.zeros(32000,np.float32),16000,subtype='PCM_16')
sources=[root/'test_wavs'/n for n in ['mix.wav','input_1_en.wav','input_2_far.wav','input_3_ch.wav']]+[silence]
for source in sources:
    name='silence' if source==silence else source.stem
    input_audio,sr=sf.read(source,dtype='float32');assert input_audio.ndim==1
    first_start=len(session.record['outputHashes']);started=time.perf_counter()
    result=official.denoise_audio(str(model),str(source),str(out/(name+'-output.wav')))
    elapsed=time.perf_counter()-started;mid=len(session.record['outputHashes'])
    started=time.perf_counter();repeat=official.denoise_audio(str(model),str(source),str(out/(name+'-repeat.wav')))
    repeat_seconds=time.perf_counter()-started
    assert np.isfinite(result).all() and np.array_equal(result,repeat)
    assert session.record['outputHashes'][first_start:mid]==session.record['outputHashes'][mid:]
    assert (out/(name+'-output.wav')).read_bytes()==(out/(name+'-repeat.wav')).read_bytes()
    actual=input_audio if sr==16000 else librosa.resample(input_audio,orig_sr=sr,target_sr=16000)
    # A PCM16 listening copy; exact float32 samples used by STFT remain in raw.npz.
    sf.write(out/(name+'-input.wav'),actual,16000,subtype='PCM_16')
    np.savez_compressed(out/(name+'-raw.npz'),input=actual,output=result)
    assert 0<=len(actual)-len(result)<256,(len(actual),len(result))
    assert mid-first_start==len(actual)//256+1
    rms=lambda x:float(np.sqrt(np.mean(x.astype(np.float64)**2)))
    row={'name':name,'sourceFile':source.name,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
     'sourceSampleRate':sr,'sourceSamples':len(input_audio),'sampleRate':16000,'inputSamples':len(actual),'outputSamples':len(result),
     'tailSamplesOmitted':len(actual)-len(result),'inputDurationSeconds':len(actual)/16000,'outputDurationSeconds':len(result)/16000,
     'pipelineSeconds':elapsed,'repeatPipelineSeconds':repeat_seconds,'realTimeFactor':elapsed/(len(actual)/16000),'npuCallsPerPass':mid-first_start,
     'repeatExact':True,'allFinite':True,'inputRms':rms(actual),'outputRms':rms(result),'outputPeak':float(np.max(np.abs(result))),
     'outputClippedFraction':float(np.mean(np.abs(result)>=1)),
     'inputSha256':hashlib.sha256((out/(name+'-input.wav')).read_bytes()).hexdigest(),
     'outputSha256':hashlib.sha256((out/(name+'-output.wav')).read_bytes()).hexdigest()}
    report['results'].append(row);save();print('RESULT',json.dumps(row),flush=True)
report['completed']=True;save()
