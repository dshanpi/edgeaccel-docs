#!/usr/bin/env python3
"""Run fixed CosyVoice3 official ARM64 AXCL binaries with local tokenizer."""
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ['HF_HUB_OFFLINE']='1'
import argparse,ast,hashlib,json,re,subprocess,threading,time
from functools import lru_cache
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from transformers import AutoTokenizer

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tokenizer_class(root):
    # Extract the official CosyVoice3 tokenizer implementation unchanged; unused Whisper imports
    # otherwise pull in an unrelated speech-recognition package.
    path=root/'scripts/tokenizer/tokenizer.py';source=path.read_text('utf-8');tree=ast.parse(source)
    nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ['CosyVoice2Tokenizer','CosyVoice3Tokenizer','get_qwen_tokenizer']]
    assert [n.name for n in nodes]==['CosyVoice2Tokenizer','CosyVoice3Tokenizer','get_qwen_tokenizer']
    namespace={'torch':torch,'AutoTokenizer':AutoTokenizer,'lru_cache':lru_cache}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
    return namespace['get_qwen_tokenizer'](str(root/'scripts/CosyVoice-BlankEN'),True,'cosyvoice3')

def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--text',action='append');a=p.parse_args()
    root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    binary=root/'main_axcl_aarch64';binary.chmod(binary.stat().st_mode|0o100)
    env=os.environ.copy();env['LD_LIBRARY_PATH']='/usr/lib/axcl:'+env.get('LD_LIBRARY_PATH','')
    linked=subprocess.run(['ldd',str(binary)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True).stdout
    assert 'not found' not in linked and 'libaxcl_rt' in linked
    (out/'linked-libraries.txt').write_text(linked)
    folder='CosyVoice-BlankEN-Ax650-C64-P256-CTX512'
    llm=root/folder;prefill='64'
    texts=a.text or ['你好，欢迎使用算力卡语音合成。','今天的温度是二十六度，请打开窗户。','Hello, welcome to our voice demonstration.','高管也通过电话、短信、微信等方式对报道[j][ǐ]予好评。']
    tokenizer=tokenizer_class(root)
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def response(self,value):
            body=json.dumps(value,ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path=='/eos_id':self.response({'eos_id':1773})
            elif self.path=='/bos_id':self.response({'bos_id':0})
            else:self.send_error(404)
        def do_POST(self):
            try:
                req=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path=='/encode':value={'token_ids':tokenizer.encode(req['text'],allowed_special='all')}
                elif self.path=='/decode':value={'text':tokenizer.decode(req['token_ids'])}
                else:self.send_error(404);return
                requests.append({'endpoint':self.path,'request':req,'response':value});self.response(value)
            except Exception as ex:self.send_error(400,str(ex))
    server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    weights=[f.relative_to(root).as_posix() for base in [llm,root/'token2wav-axmodels'] for f in sorted(base.glob('*.axmodel'))]
    report={'modelId':'CosyVoice3','provider':'AXCL C++','variant':'w8a16-ten-step','completed':False,'binarySha256':sha(binary),'tokenizerSourceSha256':sha(root/'scripts/tokenizer/tokenizer.py'),
      'promptFilesSha256':{f.name:sha(f) for f in sorted((root/'prompt_files').glob('*.txt'))},'configuredWeightFiles':weights,'sessions':[],'samples':[],
      'timingScope':'Wall time around official executable, including load, text tokenization, AXCL and host processing, output files, cleanup. Not isolated NPU latency.'}
    def save():(out/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    save()
    try:
        for index,text in enumerate(texts):
            case=out/f'sample-{index+1}';case.mkdir();args=[str(binary),'--template_filename_axmodel',str(llm/f'qwen2_p{prefill}_l%d_together.axmodel'),
              '--token2wav_axmodel_dir',str(root/'token2wav-axmodels'),'--n_timesteps','10','--axmodel_num','24','--bos','0','--eos','0',
              '--filename_tokenizer_model',f'http://127.0.0.1:{server.server_port}',
              '--filename_post_axmodel',str(llm/'qwen2_post.axmodel'),'--filename_decoder_axmodel',str(llm/'llm_decoder.axmodel'),
              '--filename_tokens_embed',str(llm/'model.embed_tokens.weight.bfloat16.bin'),'--filename_llm_embed',str(llm/'llm.speech_embedding.float16.bin'),
              '--filename_speech_embed',str(llm/'llm.speech_embedding.float16.bin'),'--continue','0','--devices','0,','--prompt_files',str(root/'prompt_files'),'--text',text]
            start=time.perf_counter()
            with (case/'output.log').open('w') as log:
                result=subprocess.run(args,cwd=case,env=env,input='q\n',text=True,stdout=log,stderr=subprocess.STDOUT,timeout=240)
            elapsed=time.perf_counter()-start;log=(case/'output.log').read_text(errors='replace')
            assert result.returncode==0 and 'Voice generation pipeline completed.' in log,f'Inference failed: {case}'
            speech,sr=sf.read(case/'output.wav',dtype='float32');assert sr==24000 and speech.ndim==1 and len(speech)>0 and np.isfinite(speech).all()
            info=sf.info(case/'output.wav');assert info.subtype=='FLOAT'
            # Browser-safe PCM16 derivative. Raw float WAV is retained unmodified.
            sf.write(out/f'sample-{index+1}.wav',speech,sr,subtype='PCM_16')
            row={'name':f'sample-{index+1}','text':text,'exitCode':result.returncode,'processSeconds':elapsed,'sampleRate':sr,'samples':len(speech),'durationSeconds':len(speech)/sr,
              'allFinite':True,'rms':float(np.sqrt(np.mean(speech.astype(np.float64)**2))),'peak':float(np.max(np.abs(speech))),'clippedFraction':float(np.mean(np.abs(speech)>=1)),
              'rawSha256':sha(case/'output.wav'),'previewSha256':sha(out/f'sample-{index+1}.wav'),'generationReachedEos':bool(re.search(r'hit eos',log)),
              'decodeTokens':[int(n) for n in re.findall(r'total decode tokens:(\d+)',log)],'reportedTtftMs':[float(n) for n in re.findall(r'ttft:\s*([\d.]+) ms',log)],
              'chunks':len(list(case.glob('output_*.wav'))),'realTimeFactorIncludingLoad':elapsed/(len(speech)/sr)}
            assert row['rms']>1e-6 and row['generationReachedEos'];report['samples'].append(row);save();print(json.dumps(row,ensure_ascii=False),flush=True)
        # Native binary has no per-tensor recorder. Do not assert tensor-level finiteness.
        report['nativeOutputFinite']=True;report['completed']=True;save()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
        (out/'tokenizer-requests.json').write_text(json.dumps(requests,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
