"""Fixed Kokoro AXCL deployment with CPU harmonic model and saved real audio."""
import argparse,hashlib,importlib.metadata,json,os,sys,time,types
from pathlib import Path
import axengine,numpy as np,onnxruntime as ort,soundfile as sf

REVISION='db9625f0270396c108d0273b01477d86b4e5e7fe'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def desc(a):
    a=np.ascontiguousarray(a);return {'shape':list(a.shape),'dtype':str(a.dtype),'sha256':hashlib.sha256(a.tobytes()).hexdigest()}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--manifest',type=Path);p.add_argument('--text');p.add_argument('--lang',choices=['z','a','j'],default='z');a=p.parse_args()
    root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    mf=a.manifest or (root/'.validation-download.json' if (root/'.validation-download.json').exists() else Path(__file__).with_name('kokoro-download-manifest.json'))
    manifest=json.loads(mf.read_text(encoding='utf-8'));assert manifest['complete'] and manifest['revision']==REVISION
    for f in manifest['files']:assert (root/f['path']).stat().st_size==f['size'] and sha(root/f['path'])==f['verifiedHashes']['sha256'],f['path']
    assert sha(root/'demo_kokoro_ax.py')=='c82887f33e3652b9380a63fd57bf877ead38808fde4136fb22be0a89f073133a'
    assert sha(root/'inference_utils.py')=='addf0507ac8b8c5c1974b345322e3ba2b9870002b23e067c9c18ff3f2dc1dd2f'
    report={'modelId':'kokoro.axera','revision':REVISION,'provider':'AXCLRTExecutionProvider','completed':False,'qualityValidated':False,'sessions':[],'samples':[],
            'settings':{'cpuThreads':2,'ortSeedPerSample':42,'speed':1.0,'fadeOutSeconds':.3,'pauseSeconds':0,'maxMergedTokens':96},
            'versions':{n:importlib.metadata.version(n) for n in ['numpy','onnxruntime','soundfile','misaki','jieba','pypinyin','spacy','en-core-web-sm','fugashi','unidic-lite','pyopenjtalk','jaconv','mojimoji','cn2an','num2words','espeakng-loader','phonemizer-fork','typer','typer-slim','click']}}
    active={'sample':'setup','chunk':None};rawcount=0
    def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def raw(arrays):
        nonlocal rawcount
        rawcount+=1;path=out/f'raw-{rawcount:04d}.npz';np.savez_compressed(path,**arrays);return {'file':path.name,'sha256':sha(path),'arrays':{k:desc(v) for k,v in arrays.items()}}
    def init_record(engine,path,providers,start):
        schema=lambda xs:[{'name':x.name,'shape':list(x.shape),'dtype':str(getattr(x,'dtype',getattr(x,'type','unknown')))} for x in xs]
        rec={'model':str(Path(path).relative_to(root)),'weightSha256':sha(path),'provider':providers,'inputs':schema(engine.get_inputs()),'outputs':schema(engine.get_outputs()),'loadSeconds':time.perf_counter()-start,'allFinite':True,'runMilliseconds':[],'calls':[]};report['sessions'].append(rec);save();return rec
    def trace(rec,names,feed,values,ms):
        arrays={**{'input-'+k:np.asarray(v) for k,v in feed.items()},**{'output-'+k:np.asarray(v) for k,v in zip(names,values)}}
        assert all(np.isfinite(x).all() for x in arrays.values());rec['runMilliseconds'].append(ms);rec['calls'].append({'sample':active['sample'],'chunk':active['chunk'],'milliseconds':ms,'raw':raw(arrays)});save()
    class AxSession:
        def __init__(self,path):
            start=time.perf_counter();self.engine=axengine.InferenceSession(path,providers=['AXCLRTExecutionProvider']);assert 'AXCLRTExecutionProvider' in self.engine.get_providers();self.rec=init_record(self.engine,path,self.engine.get_providers(),start)
        def run(self,names,feed):
            for x in self.engine.get_inputs():assert feed[x.name].shape==tuple(x.shape) and np.isfinite(feed[x.name]).all(),x.name
            start=time.perf_counter();values=self.engine.run(names,feed);ms=(time.perf_counter()-start)*1000;trace(self.rec,names or [x.name for x in self.engine.get_outputs()],feed,values,ms);return values
    original_ort=ort.InferenceSession
    class CpuSession(original_ort):
        def __init__(self,path,*args,**kwargs):
            opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1;opts.enable_cpu_mem_arena=False;start=time.perf_counter();super().__init__(path,sess_options=opts,providers=['CPUExecutionProvider']);assert self.get_providers()==['CPUExecutionProvider'];self.rec=init_record(self,path,self.get_providers(),start)
        def run(self,names,feed,*args,**kwargs):
            start=time.perf_counter();values=super().run(names,feed,*args,**kwargs);ms=(time.perf_counter()-start)*1000;trace(self.rec,names or [x.name for x in self.get_outputs()],feed,values,ms);return values
    ort.InferenceSession=CpuSession
    text=(root/'inference_utils.py').read_text(encoding='utf-8')
    replacements=[('    except Exception:\n        return []','    except Exception:\n        raise'),
                  ('            logger.error(f"错误处理句子 \'{sentence}\': {e}")','            raise'),
                  ('            logger.error(f"推理错误: {e}")','            raise'),
                  ('def split_long_sentence(sentence, lang_code, g2p, g2p_type, vocab, max_merge_len=78, depth=0):','def split_long_sentence(sentence, lang_code, g2p, g2p_type, vocab, max_merge_len=78, depth=0):\n    if depth >= 16 or not sentence.strip(): raise ValueError("Cannot split this input safely")')]
    for old,new in replacements:assert text.count(old)==1; text=text.replace(old,new)
    utils=types.ModuleType('inference_utils');utils.__file__=str(root/'inference_utils.py');sys.modules['inference_utils']=utils;exec(compile(text,utils.__file__,'exec'),utils.__dict__)
    original_clean=utils.clean_text
    def clean(text):
        x=original_clean(text)
        if not x:raise ValueError('Empty text')
        return x
    utils.clean_text=clean
    def strict_ids(phonemes,vocab,debug=False):
        bad=[c for c in phonemes if c not in vocab]
        if bad:raise ValueError('Unsupported phonemes: '+repr(bad))
        if not phonemes.strip():raise ValueError('Empty phonemes')
        return np.array([vocab[c] for c in phonemes],dtype=np.int64)
    utils.phonemes_to_input_ids=strict_ids
    def load_voice(path,phoneme_len=None):
        assert phoneme_len is not None and 0<=phoneme_len<510
        file=Path(path).resolve();assert file.is_relative_to(root/'checkpoints/voices_npy');pack=np.load(file,allow_pickle=False);assert pack.shape==(510,1,256) and np.isfinite(pack).all();return pack[phoneme_len]
    utils.load_voice_embedding=load_voice
    sys.path.insert(0,str(root));import demo_kokoro_ax as official
    official.InferenceSession=AxSession
    class CheckedEngine(official.InferenceEngine):
        def _process_duration(self,duration,actual_len,speed):
            pred,total=super()._process_duration(duration,actual_len,speed)
            if total!=192:raise ValueError(f'Predicted alignment has {total} frames; model requires 192. Use shorter text segments.')
            return pred,total
        def inference(self,input_ids,ref_s,phonemes,vocab,speed=1.0,fade_out_duration=.3):
            assert input_ids.ndim==2 and input_ids.shape[0]==1 and 3<=input_ids.shape[1]<=96
            active['chunk']=len(active['record']['chunks']);chunk={'index':active['chunk'],'inputIds':input_ids.tolist(),'phonemes':phonemes,'voiceRow':input_ids.shape[1]-2,'voiceEmbedding':desc(ref_s),'fadeSeconds':fade_out_duration};active['record']['chunks'].append(chunk);save()
            audio=super().inference(input_ids,ref_s,phonemes,vocab,speed,fade_out_duration);assert audio.size and np.isfinite(audio).all();chunk['audio']=raw({'audio':audio});save();return audio
    vocab=utils.load_vocab_from_config(str(root/'checkpoints/config.json'));g2ps={}
    voice={'z':'zf_xiaoyi','a':'af_heart','j':'jm_kumo'}
    jobs=[('custom',a.lang,a.text)] if a.text is not None else [
        ('zh-short','z','你好，世界。'),('zh-official','z','致力于打造世界领先的人工智能感知与边缘计算芯片。'),
        ('en-official','a','The sky above the port was the color of television, tuned to a dead channel.'),
        ('ja-sentences','j','今日はいい天気です。一緒に公園へ行きましょう。'),
        ('zh-official-repeat','z','致力于打造世界领先的人工智能感知与边缘计算芯片。')]
    try:utils.clean_text('  ')
    except ValueError:report['blankRejectedBeforeNpu']=True
    else:raise AssertionError('Blank accepted')
    ort.set_seed(42);engine=CheckedEngine(str(root/'models'))
    for index,(id,lang,text) in enumerate(jobs):
        text=utils.clean_text(text)
        if lang not in g2ps:g2ps[lang]=utils.init_g2p(lang)
        ort.set_seed(42)
        if index:engine.session4=CpuSession(str(root/'models/model4_har_sim.onnx'))
        g2p,kind=g2ps[lang];sample={'id':id,'language':lang,'text':text,'voice':voice[lang],'voiceSha256':sha(root/'checkpoints/voices_npy'/(voice[lang]+'.npy')),'chunks':[]};report['samples'].append(sample);active.update(sample=id,record=sample,chunk=None)
        start=time.perf_counter();groups=utils.process_and_merge_sentences(text,lang,g2p,kind,vocab,max_merge_len=96)
        pieces=utils.run_batch_inference(engine,groups,str(root/'checkpoints/voices_npy'/(voice[lang]+'.npy')),vocab,speed=1.0,fade_out_duration=.3)
        audio=utils.audio_numpy_concat(pieces,sr=24000,speed=1.0,pause_duration=0);sample['pipelineSecondsWithTrace']=time.perf_counter()-start
        np.save(out/(id+'.npy'),audio,allow_pickle=False);sf.write(out/(id+'.wav'),audio,24000,subtype='PCM_16')
        sample['audio']={'file':id+'.wav','sha256':sha(out/(id+'.wav')),'floatFile':id+'.npy','floatSha256':sha(out/(id+'.npy')),'samples':len(audio),'sampleRate':24000,'seconds':len(audio)/24000,'peak':float(np.max(np.abs(audio))),'rms':float(np.sqrt(np.mean(audio.astype(float)**2))),'outsideUnitRange':int((np.abs(audio)>1).sum())};save();print(json.dumps({'sample':id,'seconds':sample['audio']['seconds'],'chunks':len(sample['chunks'])}),flush=True)
    assert all(s['runMilliseconds'] for s in report['sessions']);report['completed']=True;save()

if __name__=='__main__':main()
