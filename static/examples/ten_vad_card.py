#!/usr/bin/env python3
"""TEN-VAD AXCL card demonstration: PCM16 mono 16 kHz to probabilities and segments.

Uses the native library built from the fixed upstream source plus ten_vad_axcl_patch.py.
No synthetic inference or CPU fallback. ONNX is an optional, separately labeled reference.
"""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import time
import wave
import numpy as np

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_wav(path, data):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(np.asarray(data, dtype='<i2').tobytes())

def segments(flags, duration):
    result = []; start = None
    for i, value in enumerate(list(flags) + [0]):
        if value and start is None: start = i
        if not value and start is not None:
            result.append([round(start * .016, 6), round(min(i * .016, duration), 6)])
            start = None
    return result

def compare_labels(path, flags, duration):
    if not path.exists(): return None
    entries = path.read_text().strip().split(',')[1:]
    assert len(entries) % 3 == 0
    spans = [[float(entries[i]), float(entries[i+1]), int(entries[i+2])] for i in range(0,len(entries),3)]
    centers = (np.arange(len(flags)) + .5) * .016
    valid = centers < duration
    truth = np.full(len(flags), -1)
    for start, end, label in spans:
        assert label in [0,1] and end >= start
        mask = (centers >= start) & (centers < end)
        assert np.all(truth[mask] == -1)
        truth[mask] = label
    valid &= truth >= 0
    pred = np.asarray(flags)[valid]; truth = truth[valid]
    tp = int(np.sum((pred==1)&(truth==1))); fp = int(np.sum((pred==1)&(truth==0)))
    fn = int(np.sum((pred==0)&(truth==1))); tn = int(np.sum((pred==0)&(truth==0)))
    return {'method':'16ms frame-center labels; no delay compensation; ignore centers beyond audio or annotations',
            'scoredFrames':int(valid.sum()),'tp':tp,'fp':fp,'fn':fn,'tn':tn,
            'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None,
            'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,'annotationSha256':sha(path)}

def onnx_reference(model, trace):
    import onnxruntime as ort
    rows=np.fromfile(trace,dtype='<f4').reshape(-1,636)
    assert np.isfinite(rows).all()
    opts=ort.SessionOptions();opts.intra_op_num_threads=1;opts.inter_op_num_threads=1
    session=ort.InferenceSession(str(model),sess_options=opts,providers=['CPUExecutionProvider'])
    ins=['input_1','input_2','input_3','input_6','input_7']; outs=['output_1','output_2','output_3','output_6','output_7']
    shapes={}
    for x in session.get_inputs():
        # Official export uses a symbolic batch dimension; AX650 artifact is batch 1.
        assert all(isinstance(d,int) and d>0 for d in x.shape[1:])
        shapes[x.name]=[1]+x.shape[1:]
    sizes=[123,64,64,64,64]; errors=[]; mismatch=0; hidden_max=0.
    for row in rows:
        feed={};offset=0
        for name,size in zip(ins,sizes):
            feed[name]=row[offset:offset+size].reshape(shapes[name]);offset+=size
        result=session.run(outs,feed)
        result=np.concatenate([x.reshape(-1) for x in result]); target=row[379:]
        assert result.shape==target.shape and np.isfinite(result).all()
        errors.append(abs(float(result[0])-float(target[0])))
        mismatch+=int((result[0]>.5)!=(target[0]>.5))
        hidden_max=max(hidden_max,float(np.max(np.abs(result[1:]-target[1:]))))
    return {'provider':'CPUExecutionProvider','method':'one-step ONNX comparison using identical features and NPU recurrent input states',
            'calls':len(rows),'probabilityMaxAbsError':max(errors),'probabilityMeanAbsError':float(np.mean(errors)),
            'threshold05Disagreements':mismatch,'hiddenStateMaxAbsError':hidden_max,'onnxSha256':sha(model)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True)
    p.add_argument('--library',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--input',type=Path,action='append',help='PCM16 mono 16 kHz WAV; default official samples 01–03 and generated silence')
    p.add_argument('--repeat',type=int,default=2);p.add_argument('--onnx-reference',action='store_true')
    a=p.parse_args(); assert a.repeat>=1
    root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    library=a.library.resolve();lib=C.CDLL(str(library))
    lib.ten_vad_create.argtypes=[C.POINTER(C.c_void_p),C.c_size_t,C.c_float];lib.ten_vad_create.restype=C.c_int
    lib.ten_vad_process.argtypes=[C.c_void_p,C.POINTER(C.c_int16),C.c_size_t,C.POINTER(C.c_float),C.POINTER(C.c_int)]
    lib.ten_vad_process.restype=C.c_int
    lib.ten_vad_destroy.argtypes=[C.POINTER(C.c_void_p)];lib.ten_vad_destroy.restype=C.c_int
    inputs=[x.resolve() for x in a.input] if a.input else [root/f'testset/testset-audio-{i:02}.wav' for i in range(1,4)]
    if not a.input:
        silence=out/'silence.wav';write_wav(silence,np.zeros(32000,dtype=np.int16));inputs.append(silence)
    # Upstream opens axmodel/ten-vad-ax650.axmodel relative to the working directory.
    os.chdir(root/'models')
    report={'model':'AXERA-TECH/ten-vad','backend':'native AXCL on card 0','hopSamples':256,'sampleRate':16000,
            'threshold':.5,'librarySha256':sha(library),'modelSha256':sha(root/'models/axmodel/ten-vad-ax650.axmodel'),
            'finiteCheckScope':'all AXCL input, probability and four recurrent output tensors on every call','samples':[]}
    for path in inputs:
        with wave.open(str(path),'rb') as w:
            assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,16000)
            audio=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').copy()
        assert len(audio)>0
        name=path.stem;duration=len(audio)/16000;count=(len(audio)+255)//256
        padded=np.pad(audio,(0,count*256-len(audio))).reshape(count,256)
        write_wav(out/(name+'-input.wav'),audio)
        attempts=[]; previous=None
        for repeat in range(a.repeat):
            trace=out/f'{name}-repeat{repeat+1}-trace.f32';os.environ['TEN_VAD_TRACE']=str(trace)
            handle=C.c_void_p();started=time.perf_counter()
            try:
                rc=lib.ten_vad_create(C.byref(handle),256,.5)
                if rc: raise RuntimeError('ten_vad_create failed: '+str(rc))
                load_seconds=time.perf_counter()-started;probs=[];flags=[];frame_times=[]
                for frame in padded:
                    prob=C.c_float();flag=C.c_int();t=time.perf_counter()
                    rc=lib.ten_vad_process(handle,frame.ctypes.data_as(C.POINTER(C.c_int16)),256,C.byref(prob),C.byref(flag))
                    frame_times.append((time.perf_counter()-t)*1000)
                    if rc: raise RuntimeError(f'ten_vad_process failed at frame {len(probs)}: {rc}')
                    assert np.isfinite(prob.value) and 0<=prob.value<=1 and flag.value in [0,1]
                    probs.append(prob.value);flags.append(flag.value)
            finally:
                if handle.value:
                    rc=lib.ten_vad_destroy(C.byref(handle))
                    if rc: raise RuntimeError('ten_vad_destroy failed: '+str(rc))
            wall=time.perf_counter()-started
            rows=np.fromfile(trace,dtype='<f4').reshape(-1,636)
            assert len(rows)>0 and np.isfinite(rows).all()
            current=(probs,flags)
            if previous is not None: assert current==previous,'Repeated outputs differ'
            previous=current
            attempts.append({'loadSeconds':load_seconds,'wallSeconds':wall,'processSeconds':sum(frame_times)/1000,
                'meanFrameMs':float(np.mean(frame_times)),'p95FrameMs':float(np.percentile(frame_times,95)),
                'npuCalls':len(rows),'traceSha256':sha(trace)})
        result={'name':name,'inputSha256':sha(path),'durationSeconds':duration,'frames':count,
            'tailPaddingSamples':count*256-len(audio),'voiceFrames':sum(flags),'voiceSegments':segments(flags,duration),
            'probabilities':probs,'flags':flags,'attempts':attempts,'repeatExact':True,'labels':compare_labels(path.with_suffix('.scv'),flags,duration)}
        if a.onnx_reference:result['onnxReference']=onnx_reference(root/'models/original/ten-vad.onnx',trace)
        mask=np.repeat(flags,256)[:len(audio)]
        write_wav(out/(name+'-gated.wav'),audio*mask)
        report['samples'].append(result)
        (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k not in ['probabilities','flags']},ensure_ascii=False),flush=True)
    report['completed']=True
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
