"""Execute the pinned official offline meeting + Qwen3 summary with AXCL tracing."""
import argparse,hashlib,importlib.metadata,json,os,sys,time,traceback,urllib.request
from collections import OrderedDict
from pathlib import Path
MID='3D-Speaker-Meeting-Summary';REV='b55d044e8eb419c779dc15c4b3e486dfe531f67e';PROVIDER='AXCLRTExecutionProvider'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        offset=0
        while data:=f.read(8*1024*1024):
            h.update(data)
            os.posix_fadvise(f.fileno(),offset,len(data),os.POSIX_FADV_DONTNEED)
            offset+=len(data)
    return h.hexdigest()
def available():
    return int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--audio',default='wav/vad_example.wav');p.add_argument('--output',type=Path,required=True);p.add_argument('--max-new-tokens',type=int,default=512);p.add_argument('--embedding-oracle',type=Path,required=True);p.add_argument('--embedding-oracle-sha256',required=True);p.add_argument('--embedding-url',default='http://127.0.0.1:18869/3D-Speaker-Meeting-Summary/ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/model.embed_tokens.weight.npy');a=p.parse_args()
    root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);audio=(root/a.audio).resolve();assert audio.is_relative_to(root) and audio.is_file()
    m=json.loads((root/'.validation-download.json').read_text());assert m['complete'] and m['revision']==REV
    rec=dict(modelId=MID,revision=REV,provider=PROVIDER,completed=False,scope='official offline audio transcription and local Qwen3 summary',runnerSha256=sha(__file__),inputPath=a.audio,inputSha256=sha(audio),filesBefore=[],filesAfter=[],sessions=[],totalCalls=0,generatedTokens=[],endedWithEos=False,maxNewTokens=a.max_new_tokens)
    def save():(out/'deployment-result.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    rec['stage']='checking-input-files';save();start=time.perf_counter()
    try:
        for f in m['files']:
            file=(root/f['path']).resolve();assert file.is_relative_to(root)
            digest=sha(file);assert digest==f['verifiedHashes']['sha256'],f['path'];rec['filesBefore'].append(dict(path=f['path'],sha256=digest))
            if len(rec['filesBefore'])%8==0:save()
        import numpy as np,axengine,torch,soundfile as sf
        torch.set_num_threads(2);np.random.seed(42);torch.manual_seed(42)
        rec['versions']={n:importlib.metadata.version(n) for n in ['numpy','torch','torchaudio','funasr','librosa','transformers','fastcluster','sentencepiece','scikit-learn','hdbscan','umap-learn']}
        info=sf.info(audio);rec['audio']=dict(durationSeconds=info.duration,sampleRate=info.samplerate,channels=info.channels,frames=info.frames)
        original=axengine.InferenceSession;verified_before={f['path']:f['sha256'] for f in rec['filesBefore']}
        class Session:
            def __init__(self,path,*args,**kw):
                assert available()>512*1024**2,'Host MemAvailable below 512 MiB before loading next model'
                self.name=Path(path).resolve().relative_to(root).as_posix();kw['providers']=[PROVIDER];t=time.perf_counter();self.s=original(path,*args,**kw);assert self.s.get_providers() in (PROVIDER,[PROVIDER])
                self.row=dict(model=self.name,provider=PROVIDER,sha256=verified_before[self.name],loadSeconds=time.perf_counter()-t,calls=0,runMilliseconds=[],allFinite=True,groups={});rec['sessions'].append(self.row);self.schemas={};save()
            def __getattr__(self,n):return getattr(self.s,n)
            def run(self,names,feed,**kw):
                if rec['totalCalls']%100==0:assert available()>300*1024**2,'Host MemAvailable below 300 MiB before inference'
                g=kw.get('shape_group',0)
                if g not in self.schemas:
                    self.schemas[g]=(self.s.get_inputs(shape_group=g),self.s.get_outputs(shape_group=g))
                    self.row['groups'][str(g)]={k:[dict(name=x.name,shape=list(x.shape),dtype=str(x.dtype)) for x in v] for k,v in zip(['inputs','outputs'],self.schemas[g])}
                ins,outs=self.schemas[g];chosen=[next(x for x in outs if x.name==n) for n in names] if names else outs
                assert set(feed)=={x.name for x in ins}
                for x in ins:
                    v=feed[x.name];assert list(v.shape)==list(x.shape) and v.dtype==np.dtype(x.dtype),(self.name,g,x.name,v.shape,x.shape)
                    # Avoid allocating full FP32 copies of 8191-token KV caches.
                    if v.size<=1024*1024:assert np.isfinite(v.astype(np.float32)).all()
                t=time.perf_counter();values=self.s.run(names,feed,**kw);ms=(time.perf_counter()-t)*1000;assert len(values)==len(chosen);checks=[]
                for x,v in zip(chosen,values):
                    assert list(v.shape)==list(x.shape) and v.dtype==np.dtype(x.dtype)
                    finite=bool(np.isfinite(v.astype(np.float32)).all());self.row['allFinite'] &=finite;assert finite
                    checks.append(dict(name=x.name,shape=list(v.shape),dtype=str(v.dtype),sha256=hashlib.sha256(v.tobytes()).hexdigest()))
                with (out/'calls.jsonl').open('a') as log:log.write(json.dumps(dict(index=rec['totalCalls'],model=self.name,shapeGroup=g,milliseconds=ms,outputs=checks,allFinite=True))+'\n')
                self.row['calls']+=1;self.row['runMilliseconds'].append(ms);rec['totalCalls']+=1
                if rec['totalCalls']%100==0:save()
                return values
        axengine.InferenceSession=Session;sys.path.insert(0,str(root));os.chdir(out);rec["workingDirectory"]=str(out)
        os.environ.update(HF_HUB_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
        from transformers import AutoConfig,AutoTokenizer
        cfg=AutoConfig.from_pretrained(root/'tokenizer_qwen3_int4',local_files_only=True)
        tok=AutoTokenizer.from_pretrained(root/'tokenizer_qwen3_int4',local_files_only=True)
        eos=cfg.eos_token_id if isinstance(cfg.eos_token_id,list) else [cfg.eos_token_id];eos=list(set(eos+[tok.eos_token_id]));rec['eosTokenIds']=eos
        head_dim=getattr(cfg,'head_dim',None) or cfg.hidden_size//cfg.num_attention_heads
        rec['estimatedHostKvBytes']=2*cfg.num_hidden_layers*8191*head_dim*cfg.num_key_value_heads*2
        from utils.infer_func import InferManager
        original_post=InferManager.post_process
        def traced_post(self,*args,**kw):
            value=original_post(self,*args,**kw);token=int(value[0]);rec['generatedTokens'].append(token);rec['endedWithEos']=token in eos
            rec['summaryPartial']=tok.decode(rec['generatedTokens'],skip_special_tokens=True)
            if len(rec['generatedTokens'])%16==0 or rec['endedWithEos']:save()
            if len(rec['generatedTokens'])>=a.max_new_tokens and not rec['endedWithEos']:raise RuntimeError('Summary reached token limit without EOS')
            return value
        InferManager.post_process=traced_post
        oracle=a.embedding_oracle.read_bytes();assert hashlib.sha256(oracle).hexdigest()==a.embedding_oracle_sha256 and len(oracle)==151936*32
        rec['embeddingRowAudit']={'oracleSha256':a.embedding_oracle_sha256,'sourceSha256':verified_before['ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel/model.embed_tokens.weight.npy'],'checkedRows':0,'mismatches':0,'copyBeforeCheck':True}
        def verified_embedding(path):
            with open(path,'rb') as f:
                version=np.lib.format.read_magic(f);assert version==(1,0)
                shape,fortran,dtype=np.lib.format.read_array_header_1_0(f);offset=f.tell()
            assert shape==(151936,2560) and dtype==np.float32 and not fortran and offset==128
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));cache=OrderedDict()
            rec['embeddingRowAudit'].update(readMethod='HTTP byte range with bounded retry, copied and SHA256-checked',httpRequests=0,retries=0,cacheHits=0)
            def fetch(index):
                if index in cache:
                    rec['embeddingRowAudit']['cacheHits']+=1;cache.move_to_end(index);return cache[index]
                begin=offset+index*10240;end=begin+10239
                for attempt in range(6):
                    try:
                        request=urllib.request.Request(a.embedding_url,headers={'Range':f'bytes={begin}-{end}','Connection':'close'})
                        with opener.open(request,timeout=12) as response:
                            assert response.status==206 and response.headers['Content-Range']==f'bytes {begin}-{end}/1555824768'
                            assert response.headers['ETag'].strip('"')==rec['embeddingRowAudit']['sourceSha256']
                            data=response.read();assert len(data)==10240
                        rec['embeddingRowAudit']['httpRequests']+=1;cache[index]=data
                        if len(cache)>256:cache.popitem(last=False)
                        return data
                    except (OSError,TimeoutError) as exc:
                        rec['embeddingRowAudit']['retries']+=1;rec['embeddingRowAudit']['lastReadError']=repr(exc);save()
                        if attempt==5:raise
                        time.sleep(2)
            class GuardedEmbedding:
                def __getitem__(self,key):
                    index=key[0] if isinstance(key,tuple) else key
                    if isinstance(key,tuple):assert len(key)==2 and key[1]==slice(None)
                    indexes=np.asarray(index,dtype=np.int64);indices=indexes.reshape(-1)
                    data=np.empty(indexes.shape+(2560,),dtype=np.float32);rows=data.reshape(-1,2560)
                    for i,row in zip(indices,rows):
                        i=int(i);assert 0<=i<151936
                        row[:]=np.frombuffer(fetch(i),dtype=np.float32)
                        actual=hashlib.sha256(row.tobytes()).digest();expected=oracle[i*32:(i+1)*32]
                        if actual!=expected:
                            rec['embeddingRowAudit']['mismatches']+=1;rec['embeddingRowAudit']['badTokenId']=i;save()
                            raise RuntimeError('Embedding row differs from verified PC source before inference: '+str(i))
                        rec['embeddingRowAudit']['checkedRows']+=1
                    return data
            return GuardedEmbedding()
        source=(root/'demo.py').read_text(encoding='utf-8')
        changes=[('embeds = np.load(os.path.join(llm_axmodel_path, "model.embed_tokens.weight.npy"))','embeds = _verified_embedding(os.path.join(llm_axmodel_path, "model.embed_tokens.weight.npy"))'),('prefill_data = np.take(embeds, token_ids, axis=0)','prefill_data = embeds[np.asarray(token_ids, dtype=np.int64)]')]
        changes.append(('segment_filename = f"temp_segment_{i}.wav"','segment_filename = os.path.join(args.output_dir, f"temp_segment_{i}.wav")'))
        changes.extend([
            ('ax_model_dir = "ax_model"','ax_model_dir = '+repr(str(root/'ax_model'))),
            ('llm_axmodel_path = "./ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel"','llm_axmodel_path = '+repr(str(root/'ax_model/Qwen3-4B-Instruct-2507-GPTQ-Int4_8k_axmodel'))),
            ('llm_hf_tokenizer_path = "./tokenizer_qwen3_int4"','llm_hf_tokenizer_path = '+repr(str(root/'tokenizer_qwen3_int4')))])
        adapted=source
        for old,new in changes:assert adapted.count(old)==1;adapted=adapted.replace(old,new)
        rec['sourceAdaptation']=dict(sourceSha256=sha(root/'demo.py'),adaptedSha256=hashlib.sha256(adapted.encode()).hexdigest(),changes=[dict(before=x,after=y) for x,y in changes],reason='Read original FP32 embedding rows through HTTP byte ranges, copy and SHA256-verify every selected row before dtype conversion; request per-file checksum read-cache eviction; resolve model/tokenizer/audio by absolute paths and write intermediate files only in output directory; model values and inference math unchanged')
        (out/'demo-adapted.py').write_text(adapted,encoding='utf-8');save()
        sys.argv=[str(root/'demo.py'),'--output_dir',str(out),'--wav_file',str(audio)]
        rec['stage']='official-pipeline';rec['checksumReadCache']='POSIX_FADV_DONTNEED requested for each completed 8MiB checksum block';save()
        exec(compile(adapted,str(root/'demo.py'),'exec'),{'__name__':'__main__','__file__':str(root/'demo.py'),'_verified_embedding':verified_embedding})
        transcription=out/(audio.name+'.txt');summary=out/(audio.name+'_summary.md');assert transcription.is_file() and summary.is_file()
        rec['transcript']=transcription.read_text(encoding='utf-8');rec['summary']=summary.read_text(encoding='utf-8');assert rec['transcript'].strip() and rec['summary'].strip() and rec['endedWithEos']
        expected={f['path'] for f in m['files'] if f['path'].endswith('.axmodel')}
        assert {s['model'] for s in rec['sessions']}==expected and len(expected)==40 and all(s['calls']>0 for s in rec['sessions'])
        rec['stage']='checking-output-files';save()
        for f in m['files']:
            digest=sha(root/f['path']);assert digest==f['verifiedHashes']['sha256'],f['path'];rec['filesAfter'].append(dict(path=f['path'],sha256=digest))
        rec['completed']=True;rec['stage']='completed'
    except BaseException as exc:
        rec['failure']=repr(exc);rec['traceback']=traceback.format_exc();raise
    finally:rec['elapsedSeconds']=time.perf_counter()-start;rec['hostAvailableBytesAtExit']=available();save()
if __name__=='__main__':main()
