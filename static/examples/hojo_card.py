"""Hojo-TTS-Light on an AXCL M.2 card; bounded decode, traced TTS, CPU ISTFT."""
import argparse,hashlib,json,time,wave
from pathlib import Path
import numpy as np
import axengine
from ml_dtypes import bfloat16
from tokenizers import Tokenizer

MID='Hojo-TTS-Light'
REVISION='cee17e0534ba216649d82055a326b995b6cf35c4'
PROVIDER='AXCLRTExecutionProvider'

def sha(data):return hashlib.sha256(data).hexdigest()
def meta(value):return {'shape':list(value.shape),'dtype':str(value.dtype),'sha256':sha(value.tobytes())}

def synthesize_wave(mag,phase,frames):
    assert mag.shape==phase.shape==(961,2048) and 0<frames<=2048
    nfft,hop=1920,480
    window=(.5*(1-np.cos(2*np.pi*np.arange(nfft)/nfft))).astype(np.float32)
    length=(frames-1)*hop+nfft
    output=np.zeros(length,np.float32);squares=np.zeros(length,np.float32)
    for t in range(frames):
        amplitude=np.exp(np.minimum(mag[:,t],np.float32(np.log(100))))
        spectrum=amplitude*np.cos(phase[:,t])+1j*amplitude*np.sin(phase[:,t])
        spectrum[-1]=spectrum[-1].real
        signal=np.fft.irfft(spectrum,n=nfft).astype(np.float32)*window
        output[t*hop:t*hop+nfft]+=signal;squares[t*hop:t*hop+nfft]+=window*window
    output=np.divide(output,squares,out=np.zeros_like(output),where=squares>1e-6)[720:-720]
    assert len(output)==frames*hop and np.isfinite(output).all()
    return output

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--manifest',type=Path);p.add_argument('--text');p.add_argument('--voice',type=int,default=9)
    p.add_argument('--max-new-tokens',type=int,default=256);p.add_argument('--first-only',action='store_true')
    a=p.parse_args();assert 0<=a.voice<15 and 1<=a.max_new_tokens<=512
    root=a.model_dir.resolve();out=a.output.resolve();models=root/'models'
    manifest=a.manifest or (root/'.validation-download.json')
    if not manifest.exists():manifest=Path(__file__).with_name('download-manifest.json')
    download=json.loads(manifest.read_text());assert download['revision']==REVISION and download['complete']
    for f in download['files']:
        assert sha((root/f['path']).read_bytes())==f['verifiedHashes']['sha256'],f['path']
    out.mkdir(parents=True,exist_ok=False)
    tok=Tokenizer.from_file(str(models/'tokenizer.json'));assert tok.get_vocab_size()==17685
    voice=np.load(models/'Hojo-TTS-Light-40M-voice.npz',allow_pickle=False)
    embeddings=voice['token_embedding'].astype(bfloat16)
    assert embeddings.shape==(17685,512)
    assert np.array_equal(embeddings.view(np.uint16),np.fromfile(models/'lm_s8/embed_tokens.bin','<u2').reshape(17685,512))
    speakers=voice['speaker_embeds'];vectors=voice['speaker_vecs']
    assert speakers.shape==(15,16,512) and vectors.shape==(15,192)
    id2code=np.fromfile(models/'id2code.bin','<i8');assert id2code.shape==(17685,)
    for i,code in enumerate(id2code):
        if code>=0:assert tok.id_to_token(i)==f'[{code}]'
    end=tok.token_to_id('[target_speech_end]');assert end==17659
    record={'modelId':MID,'revision':REVISION,'provider':PROVIDER,'completed':False,'sessions':[],'samples':[],
            'maxNewTokens':a.max_new_tokens,'sampling':{'method':'greedy','repetitionPenalty':1.1,'penaltyWindow':20},
            'upstreamAlgorithm':'ml-inory/hojo-tts-light.axera@89bae65281eed45aa0e77ef641c06671b94a54ee',
            'tracePolicy':'LM caches reconstructed from zero initialization and saved per-step KV outputs; full cache hashes are recorded on every call.',
            'cpuStages':['tokenization','speaker prompt assembly','RMS normalization','bit threshold','ISTFT','PCM WAV']}
    def save():(out/'deployment-result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    class Session:
        def __init__(self,relative):
            t=time.perf_counter();self.session=axengine.InferenceSession(str(root/relative),providers=[PROVIDER])
            assert self.session.get_providers() in [PROVIDER,[PROVIDER]]
            self.inputs=self.session.get_inputs();self.outputs=self.session.get_outputs()
            self.row={'model':relative,'provider':PROVIDER,'weightSha256':sha((root/relative).read_bytes()),'loadSeconds':time.perf_counter()-t,
                      'inputs':[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in self.inputs],
                      'outputs':[{'name':x.name,'shape':list(x.shape),'dtype':str(x.dtype)} for x in self.outputs],
                      'allFinite':True,'runMilliseconds':[],'calls':[]}
            record['sessions'].append(self.row);save()
        def run(self,feed,trace,tracefile,tag):
            assert set(feed)=={x.name for x in self.inputs}
            io={};arrays={}
            for direction,items in [('inputs',[(x.name,feed[x.name],x) for x in self.inputs])]:
                for name,value,schema in items:
                    assert list(value.shape)==list(schema.shape) and value.dtype==schema.dtype,(name,value.shape,value.dtype,schema.shape,schema.dtype)
                    assert np.isfinite(value).all(),name
                    info=meta(value)
                    if name not in ['K_cache','V_cache']:
                        key=tag+'_in_'+name;trace[key]=value.view(np.uint16).copy() if value.dtype==np.dtype(bfloat16) else value.copy();info['key']=key
                    io[name]=info
            t=time.perf_counter();values=self.session.run(None,feed,shape_group=0);ms=(time.perf_counter()-t)*1000
            for schema,value in zip(self.outputs,values):
                value=value.copy();assert np.isfinite(value).all(),schema.name
                key=tag+'_out_'+schema.name;trace[key]=value.view(np.uint16).copy() if value.dtype==np.dtype(bfloat16) else value.copy()
                arrays[schema.name]=value
            call={'file':tracefile,'inputs':io,'outputs':{name:{**meta(value),'key':tag+'_out_'+name} for name,value in arrays.items()}}
            self.row['calls'].append(call);self.row['runMilliseconds'].append(ms)
            return arrays
    layers=[Session(f'models/lm_s8/qwen3_p8_l{i}_together.axmodel') for i in range(10)]
    post=Session('models/lm_s8/qwen3_post.axmodel');fine=Session('models/fine_local.axmodel');decoder=Session('models/decoder_sq.axmodel')
    history=layers[0].inputs[0].shape[1];assert history==2047
    assert all(next(x.shape for x in s.inputs if x.name=='K_cache')==[1,history,128] for s in layers)
    record['decodeHistoryRows']=history
    jobs=[('english-short','Hello, this is a demo.',9),('chinese-short','你好，欢迎使用算力卡。',0),('english-repeat','Hello, this is a demo.',9)]
    if a.text:
        assert a.text.strip() and len(a.text)<=500;jobs=[('custom',a.text,a.voice)]
    elif a.first_only:jobs=jobs[:1]
    for name,text,voice_id in jobs:
        folder=out/name;folder.mkdir();files=[]
        def pack(filename,arrays):
            path=folder/filename;np.savez_compressed(path,**arrays)
            files.append({'file':path.relative_to(out).as_posix(),'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size})
        prompt='[target_text_start]'+text+'[target_text_end][spk_start]'+''.join(f'[spk_emb_{i}]' for i in range(16))+'[spk_end][target_speech_start]'
        ids=tok.encode(prompt,add_special_tokens=True).ids
        assert 0<len(ids)<=512 and len(ids)+a.max_new_tokens<=history
        start=ids.index(tok.token_to_id('[spk_start]'))+1
        assert ids[start:start+16]==[tok.token_to_id(f'[spk_emb_{i}]') for i in range(16)]
        prompt_embeds=embeddings[ids].copy();prompt_embeds[start:start+16]=speakers[voice_id].astype(bfloat16)
        pack('prompt.npz',{'input_ids':np.array(ids,np.int64),'embeddings_bf16':prompt_embeds.view(np.uint16)})
        k=[np.zeros((1,history,128),bfloat16) for _ in layers];v=[x.copy() for x in k]
        generated=[];hidden=[];audio_ids=[];stop='token-limit'
        call_starts=[len(s['calls']) for s in record['sessions']];t0=time.perf_counter()
        for pos in range(len(ids)+a.max_new_tokens-1):
            trace={};filename=f'{name}/step-{pos:04d}.npz'
            data=(prompt_embeds[pos] if pos<len(ids) else embeddings[generated[-1]]).reshape(1,1,512)
            mask=np.full((1,1,history+1),-65536,dtype=bfloat16);mask[:,:,:pos]=0;mask[:,:,-1]=0
            indices=np.array([[pos]],dtype=np.uint32)
            for i,layer in enumerate(layers):
                values=layer.run({'input':data,'indices':indices,'mask':mask,'K_cache':k[i],'V_cache':v[i]},trace,filename,f'l{i}')
                k[i][:,pos:pos+1,:]=values['K_cache_out'];v[i][:,pos:pos+1,:]=values['V_cache_out'];data=values['output']
            if pos>=len(ids)-1:
                values=post.run({'input':data},trace,filename,'post');logits=values['output'].astype(np.float32).reshape(-1)
                penalized=logits.copy()
                for token in set(generated[-20:]):penalized[token]=penalized[token]/1.1 if penalized[token]>0 else penalized[token]*1.1
                token=int(np.argmax(penalized));generated.append(token)
                if token==end:stop='speech-end'
                elif id2code[token]>=0:hidden.append(data.reshape(512).copy());audio_ids.append(token)
            pack(Path(filename).name,trace)
            if stop=='speech-end':break
            if pos%50==0:print(name,'position',pos,'generated',len(generated),flush=True)
        lm_seconds=time.perf_counter()-t0;frames=len(audio_ids);assert 0<frames<=2048
        hidden_raw=np.array(hidden,dtype=bfloat16).astype(np.float32)
        norm=(1/np.sqrt(np.mean(hidden_raw.astype(np.float64)**2,axis=1).astype(np.float32)+np.float32(1e-6))).astype(np.float32)
        hs=np.zeros((1,2048,512),np.float32);hs[0,:frames]=hidden_raw*norm[:,None]
        coarse=np.zeros_like(hs);coarse[0,:frames]=embeddings[audio_ids].astype(np.float32)
        valid=np.zeros((1,2048),np.float32);valid[0,:frames]=1
        trace={};filename=f'{name}/synthesis.npz'
        fine_result=fine.run({'hidden_states':hs,'coarse_embeddings':coarse,'speaker_embedding':vectors[voice_id:voice_id+1].copy(),'valid_mask_fp32':valid},trace,filename,'fine')
        bits=np.zeros((2048,128),np.float32);bits[:frames]=np.where(fine_result['binary_logits'][0,:frames]>0,1.,-1.)
        dec_result=decoder.run({'bits':bits},trace,filename,'decoder')
        pcm_float=synthesize_wave(dec_result['mag'],dec_result['phase'],frames)
        pack('synthesis.npz',trace);np.save(folder/'waveform.npy',pcm_float)
        pcm=np.clip(pcm_float*np.float32(32767),-32768,32767).astype('<i2')
        with wave.open(str(folder/'output.wav'),'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000);wav.writeframes(pcm.tobytes())
        row={'name':name,'text':text,'voiceIndex':voice_id,'prompt':prompt,'promptTokenIds':ids,'generatedTokenIds':generated,'audioTokenIds':audio_ids,
             'stopReason':stop,'audioFrames':frames,'audioSeconds':len(pcm)/24000,'lmSecondsWithTrace':lm_seconds,'pipelineSecondsWithTrace':time.perf_counter()-t0,
             'calls':[len(s['calls'])-b for s,b in zip(record['sessions'],call_starts)],'files':files,
             'waveFile':f'{name}/output.wav','waveSha256':sha((folder/'output.wav').read_bytes()),'floatFile':f'{name}/waveform.npy',
             'floatSha256':sha((folder/'waveform.npy').read_bytes()),'floatPeak':float(np.max(np.abs(pcm_float))),'clippedSamples':int(np.count_nonzero((pcm_float*32767>32767)|(pcm_float*32767<-32768)))}
        record['samples'].append(row);save();print(json.dumps({k:v for k,v in row.items() if k in ['name','audioSeconds','stopReason','pipelineSecondsWithTrace']}),flush=True)
    record['completed']=True;save()

if __name__=='__main__':main()
