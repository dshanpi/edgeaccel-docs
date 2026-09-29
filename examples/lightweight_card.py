#!/usr/bin/env python3
"""Run the three fixed Lightweight-Speech-Denoising AX650 models on AXCL."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,hashlib,json,re,shutil,subprocess,time,wave
from pathlib import Path
import numpy as np

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def readwav(path):
    with wave.open(str(path),'rb') as f:
        assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(16000,1,2)
        return np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').copy()
def writewav(path,pcm):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(pcm.astype('<i2').tobytes())

def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=a.model_dir.resolve();binary=a.binary.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    source=root/'test_wavs/mix.wav';pcm=readwav(source);assert len(pcm)>32000
    report={'modelId':'Lightweight-Speech-Denoising.axera','provider':'AXCL C API','completed':False,'sourceSha256':sha(source),'binarySha256':sha(binary),'sessions':[],'results':[],
      'timingScope':'Native processing loop: official CPU DSP, host/device copies, AXCL execution, finite checks, tensor SHA256 and stdout timings. Excludes load, file read/write and repeat.'}
    def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    save()
    for model,config,step in [('tiny_v5','tiny_v5',6),('conv_se','conv_se',6),('gtcrn','gtcrn_7input',1)]:
        weight='axmodels/ax650_'+model+'_setrain.axmodel';ini=root/'models'/(config+'_ax650_config.ini')
        chunk=step*256;boundary=3*chunk
        session={'model':weight,'configSha256':sha(ini),'modelSha256':sha(root/weight),'allFinite':True,'runMilliseconds':[],'runs':[]}
        report['sessions'].append(session)
        for name,values in [('official',pcm),('silence',np.zeros(32000,np.int16)),('below-chunk',pcm[:boundary-1]),('exact-chunk',pcm[:boundary]),('above-chunk',pcm[:boundary+1])]:
            label=model+'-'+name;inp=out/(label+'-input.wav')
            if name=='official':shutil.copy2(source,inp)
            else:writewav(inp,values)
            passes=[];arrays=[]
            for repeat in range(2):
                output=out/(label+('-repeat' if repeat else '-output')+'.wav');raw=out/(label+f'-pass{repeat}.f32')
                env=os.environ.copy();env['SE_RAW_OUTPUT']=str(raw)
                start=time.perf_counter();run=subprocess.run([str(binary),str(inp),str(output),str(ini),str(root/weight)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=90);wall=time.perf_counter()-start
                log=out/(label+f'-pass{repeat}.log');log.write_text(run.stdout)
                assert run.returncode==0, f'{label} failed; inspect {log}'
                stats=json.loads(re.search(r'^SE_STATS (.+)$',run.stdout,re.M)[1]);trace=re.search(r'^CL_TRACE (\d+) ([a-f0-9]{64})$',run.stdout,re.M)
                milliseconds=[float(x) for x in re.findall(r'^CL_RUN \d+ ([\d.]+)$',run.stdout,re.M)]
                expected_calls=len(values)//chunk;expected_samples=expected_calls*chunk-256
                assert stats['samplesIn']==len(values) and stats['samplesOut']==expected_samples
                assert int(trace[1])==stats['calls']==len(milliseconds)==expected_calls and stats['step']==step
                floating=np.fromfile(raw,dtype='<f4');wav=readwav(output)
                assert len(floating)==len(wav)==expected_samples and np.isfinite(floating).all()
                arrays.append(floating);passes.append(dict(stats,traceSha256=trace[2],rawSha256=sha(raw),wavSha256=sha(output),processWallSeconds=wall))
                session['runMilliseconds'].extend(milliseconds);session['runs'].append({'sample':name,'pass':repeat,**passes[-1]})
                # Fixed names and byte counts, captured before executing any frames.
                meta={side:[{'name':n,'bytes':int(b)} for n,b in re.findall(r'\b'+side+r'\[\d+\]:\s+(\S+)\s+size=(\d+) bytes',run.stdout)] for side in ['Input','Output']}
                assert meta['Input'] and meta['Output']
                if 'metadata' in session:assert session['metadata']==meta
                else:session['metadata']=meta
            assert np.array_equal(*arrays) and passes[0]['traceSha256']==passes[1]['traceSha256'] and passes[0]['wavSha256']==passes[1]['wavSha256']
            floating=arrays[0]
            np.savez_compressed(out/(label+'-raw.npz'),input=values.astype(np.float32)/32768,output=floating)
            row={'name':label,'model':model,'sample':name,'samplesIn':len(values),'samplesOut':len(floating),'sampleRate':16000,'hop':256,'step':step,'callsPerPass':expected_calls,
                'leadingSamplesDiscarded':256,'trailingSamplesNotProcessed':len(values)-expected_calls*chunk,'pipelineSeconds':passes[0]['pipelineMilliseconds']/1000,'repeatPipelineSeconds':passes[1]['pipelineMilliseconds']/1000,
                'realTimeFactor':passes[0]['pipelineMilliseconds']/1000/(len(values)/16000),'repeatExact':True,'allFinite':True,'outputRms':float(np.sqrt(np.mean(floating.astype(np.float64)**2))),
                'outputPeak':float(np.max(np.abs(floating))),'outputClippedFraction':float(np.mean(np.abs(floating)>=1)),
                'inputSha256':sha(inp),'outputSha256':sha(out/(label+'-output.wav')),'passes':passes}
            report['results'].append(row);save();print(json.dumps(row,ensure_ascii=False),flush=True)
    report['completed']=True;save()
    print('COMPLETED all three AX650 weights on native AXCL',flush=True)

if __name__=='__main__':main()
