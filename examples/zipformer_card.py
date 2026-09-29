"""Fixed official Zipformer encoder/cache/greedy decoder through AXCL."""
import argparse
import ast
import hashlib
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import axengine
import kaldi_native_fbank as knf
import numpy as np
import soundfile as sf
import torch
import torchaudio.compliance.kaldi as kaldi

p=argparse.ArgumentParser()
p.add_argument('--model-dir',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--audio',type=Path,action='append')
a=p.parse_args();root,out=a.model_dir.resolve(),a.output.resolve()
assert not out.exists(),'Choose a new output directory'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda v:hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()
source=root/'ax_pretrained_infer.py'
assert sha(source)=='883e9e71fff3224c08456e68d65f59c8d32fcf9ab0ae2794f855ff18e6711115'
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
torch.set_num_threads(2)
out.mkdir(parents=True)
report={'modelId':'Zipformer.axera','provider':'AXCLRTExecutionProvider','completed':False,
        'sourceSha256':sha(source),'tokensSha256':sha(root/'inputs/lang_char_bpe/tokens.txt'),
        'featureBackend':'kaldi-native-fbank 1.22.3, compared with torchaudio 2.5.1 Kaldi fbank',
        'sessions':[],'samples':[]}
current=0;raw_logits=[];encoder_features=[]


def save():
    (out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


class Measured:
    def __init__(self,path):
        t=time.perf_counter();self.engine=axengine.InferenceSession(path,providers=['AXCLRTExecutionProvider'])
        self.name=Path(path).name
        self.record={'model':str(Path(path).resolve().relative_to(root)),'weightSha256':sha(Path(path)),
                     'loadSeconds':time.perf_counter()-t,'allFinite':True,'runMilliseconds':[],'calls':[],
                     'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.engine.get_inputs()],
                     'outputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.engine.get_outputs()]}
        report['sessions'].append(self.record);save()
    def get_inputs(self):return self.engine.get_inputs()
    def get_outputs(self):return self.engine.get_outputs()
    def run(self,names,feeds):
        for m in self.engine.get_inputs():
            v=feeds[m.name]
            assert v.shape==tuple(m.shape) and v.dtype==np.dtype(m.dtype),(m.name,v.shape,v.dtype,m.shape,m.dtype)
            assert np.isfinite(v).all()
        t=time.perf_counter();values=self.engine.run(names,feeds);ms=(time.perf_counter()-t)*1000
        assert all(np.isfinite(v).all() for v in values)
        row={'sampleIndex':current,'inputs':{k:digest(v) for k,v in feeds.items()},
             'outputs':{k:digest(v) for k,v in zip(names,values)}}
        if self.name=='joiner.axmodel':
            raw_logits.append(values[0].copy());row['chosenToken']=int(np.argmax(values[0][0]))
        if self.name=='encoder.axmodel':encoder_features.append(feeds['x'].copy())
        self.record['runMilliseconds'].append(ms);self.record['calls'].append(row)
        return values


nodes=[n for n in ast.parse(source.read_text('utf-8')).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ['OnnxModel','greedy_search','read_sound_files']]
assert len(nodes)==3
selected=ast.Module(body=nodes,type_ignores=[])
used=out/'official-functions-used.py';used.write_text(ast.unparse(selected),encoding='utf-8')
report['usedFunctionsSha256']=sha(used)
namespace={'torch':torch,'np':np,'logging':logging,'Tuple':Tuple,'Dict':Dict,'List':List,'Optional':Optional,'InferenceSession':Measured}
exec(compile(selected,str(source),'exec'),namespace)
model=namespace['OnnxModel'](*[str(root/'inputs/axmodels_650N'/name) for name in ['encoder.axmodel','decoder.axmodel','joiner.axmodel']])
symbols={}
for line in (root/'inputs/lang_char_bpe/tokens.txt').read_text('utf-8').splitlines():
    if line.strip():
        token,index=line.rsplit(maxsplit=1);index=int(index);assert index not in symbols;symbols[index]=token
assert symbols[0]=='<blk>' and len(symbols)>=model.vocab_size
files=[p.resolve() for p in a.audio] if a.audio else sorted(p for p in (root/'inputs/test_wavs').iterdir() if p.suffix in ['.wav','.mp3'])
assert files
silence=out/'silence-3s.wav';sf.write(silence,np.zeros(48000,dtype=np.float32),16000,subtype='PCM_16')
for audio,kind in [(f,'official' if not a.audio else 'custom') for f in files]+[(files[0],'repeat'),(silence,'silence')]:
    current+=1;raw_logits=[];encoder_features=[]
    saved=out/f'input-{current}{audio.suffix}';shutil.copy2(audio,saved)
    model.init_encoder_states();starts=[len(s['calls']) for s in report['sessions']]
    t=time.perf_counter()
    wave=namespace['read_sound_files']([str(audio)],16000)[0]
    assert 0<len(wave)<=16000*60 and torch.isfinite(wave).all()
    padded=torch.cat([wave,torch.zeros(4800,dtype=torch.float32)])
    opts=knf.FbankOptions();opts.frame_opts.dither=0;opts.frame_opts.snip_edges=False;opts.frame_opts.samp_freq=16000
    opts.mel_opts.num_bins=80;opts.mel_opts.high_freq=-400
    fbank=knf.OnlineFbank(opts)
    processed=0;hyp=None;decoder_out=None
    for start in range(0,len(padded),16000):
        fbank.accept_waveform(16000,padded[start:start+16000].tolist())
        while fbank.num_frames_ready-processed>=model.segment:
            frames=np.stack([fbank.get_frame(processed+i) for i in range(model.segment)]).astype(np.float32)
            processed+=model.offset
            enc=model.run_encoder(torch.from_numpy(frames[None]))
            hyp,decoder_out=namespace['greedy_search'](model,enc,model.context_size,decoder_out,hyp)
    assert hyp is not None
    output=''.join(symbols[token] for token in hyp[model.context_size:]).replace('▁',' ').strip()
    elapsed=time.perf_counter()-t
    # Independent Kaldi front-end comparison; excluded from deployment timing.
    with torch.no_grad():
        reference=kaldi.fbank(padded[None],num_mel_bins=80,sample_frequency=16000,dither=0,snip_edges=False,high_freq=-400).numpy()
    available=np.stack([fbank.get_frame(i) for i in range(fbank.num_frames_ready)]).astype(np.float32)
    assert len(reference)>=len(available) and np.isfinite(reference).all() and np.isfinite(available).all()
    diff=available-reference[:len(available)]
    cosine=float(np.dot(available.ravel().astype(np.float64),reference[:len(available)].ravel().astype(np.float64))/(np.linalg.norm(available.astype(np.float64))*np.linalg.norm(reference[:len(available)].astype(np.float64))))
    raw=out/f'raw-{current}.npz'
    np.savez_compressed(raw,features=available,reference=reference,encoderInputs=np.concatenate(encoder_features),joinerLogits=np.concatenate(raw_logits))
    row={'kind':kind,'input':audio.name,'audioFile':saved.name,'audioSha256':sha(saved),'audioSeconds':len(wave)/16000,
         'output':output,'tokenIds':hyp,'processSeconds':elapsed,'rtf':elapsed/(len(wave)/16000),
         'processedFrames':processed,'readyFrames':fbank.num_frames_ready,'tailPaddingSeconds':.3,
         'featureComparison':{'maxAbsoluteError':float(np.max(np.abs(diff))),'meanAbsoluteError':float(np.mean(np.abs(diff))),'cosine':cosine},
         'sessionCalls':[len(s['calls'])-n for s,n in zip(report['sessions'],starts)],'rawFile':raw.name,'rawSha256':sha(raw)}
    report['samples'].append(row);save();print(json.dumps(row,ensure_ascii=False),flush=True)
report['completed']=True;save()
