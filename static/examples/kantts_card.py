"""Run the fixed KAN-TTS five-network AXCL pipeline, saving actual audio and IO.

Requires NumPy, jieba and pypinyin. Chinese text frontend is an approximation
from the official calibration script, not the x86 ttsfrd production frontend.
"""
import argparse, ast, hashlib, importlib.metadata, json, os, re, subprocess, time
from pathlib import Path
import numpy as np

REVISION = '7e8b1618599e4528b465af9973ffbbce6cb6d274'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def frontend(root):
    import jieba
    from pypinyin import Style, lazy_pinyin
    tree = ast.parse((root/'sdk/tools/gen_calib.py').read_text(encoding='utf-8'))
    names = {'INITIALS', 'PUNCT', 'SYLL', 'WS', 'EMO', 'SPK'}
    functions = {'pinyin_syllable', 'word_symbols', 'text_to_symbols'}
    chosen = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in functions) or
              (isinstance(n, ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in names)]
    assert len(chosen)==len(names)+len(functions)
    scope = {'re': re, 'jieba': jieba, 'Style': Style, 'lazy_pinyin': lazy_pinyin}
    exec(compile(ast.Module(body=chosen,type_ignores=[]), 'official-calibration-frontend', 'exec'),scope)
    phones = re.findall(r'<name>([^<]+)</name>', (root/'model/resource/PinYin/PhoneSet.xml').read_text(encoding='utf-8')) + ['#'+str(i) for i in range(1,5)]
    tones = [('tone'+x.strip()) if x.strip() else 'tone_none' for x in (root/'model/resource/PinYin/tonelist.txt').read_text().splitlines()]
    vocab = [phones, tones, scope['SYLL'], scope['WS'], scope['EMO'], scope['SPK']]
    def validate(symbols):
        toks = symbols.split()
        if not toks: raise ValueError('Empty symbols')
        for tok in toks:
            if not tok.startswith('{') or not tok.endswith('}'): raise ValueError('Malformed symbol')
            fields = tok[1:-1].split('$')
            if len(fields)!=6 or any(x not in allowed for x,allowed in zip(fields,vocab)):
                raise ValueError('Unsupported symbol: '+tok)
        return toks
    def split(symbols):
        toks = validate(symbols); segments=[]
        while toks:
            if len(toks)<=22: end=len(toks)
            else:
                candidates=[]
                for i,tok in enumerate(toks[:22],1):
                    f=tok[1:-1].split('$')
                    if f[0] in ['#3','#4']: candidates.append((4,i))
                    elif f[0].startswith('#'): candidates.append((3,i))
                    elif f[3] in ['word_end','word_both']: candidates.append((2,i))
                    elif f[2] in ['s_end','s_both']: candidates.append((1,i))
                if not candidates: raise ValueError('Cannot split symbols at a syllable boundary')
                end=max(candidates)[1]
            segments.append(' '.join(toks[:end]));toks=toks[end:]
        return segments
    def convert(text):
        if not text.strip() or not any('\u4e00'<=c<='\u9fff' for c in text): raise ValueError('Chinese text required')
        if any(not ('\u4e00'<=c<='\u9fff' or c in scope['PUNCT'] or c.isspace()) for c in text):
            raise ValueError('Write numbers in Chinese; only Chinese text and Chinese punctuation are supported')
        if any(scope['pinyin_syllable'](c) is None for c in text if '\u4e00'<=c<='\u9fff'):
            raise ValueError('Unsupported Chinese character')
        return split(scope['text_to_symbols'](text))
    return convert,split

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--manifest', type=Path, help='File/hash manifest; defaults to bundled manifest or validation downloader record')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--text', help='Optional Chinese input, approximate frontend')
    p.add_argument('--duration-factor', type=float, default=1.4)
    a=p.parse_args();root=a.model_dir.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    if not .5<=a.duration_factor<=2: raise ValueError('Duration factor must be .5..2')
    manifest_path=a.manifest or (root/'.validation-download.json' if (root/'.validation-download.json').exists() else Path(__file__).with_name('kantts-download-manifest.json'))
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    assert manifest['revision']==REVISION
    for f in manifest['files']:
        assert (root/f['path']).stat().st_size==f['size']
        assert sha(root/f['path'])==f['verifiedHashes']['sha256'], f['path']
    convert,split=frontend(root)
    official=(root/'example/run_example.sh').read_text(encoding='utf-8').split("<<'SYM'\n",1)[1].split('\nSYM',1)[0].split('\t',1)[1]
    base=split(official);assert len(base)==1 and len(base[0].split())==22
    negative=[]
    for text in ['', '123 hello']:
        try: convert(text)
        except ValueError as e: negative.append({'text':text,'rejectedBeforeNpu':True,'reason':str(e)})
        else: raise AssertionError('Invalid text accepted')
    jobs=[('custom',a.text,convert(a.text),a.duration_factor,'approximate-calibration')] if a.text else [
        ('official-beijing','北京今天天气怎么样',base,1.4,'official-fixed-symbols'),
        ('official-original-duration','北京今天天气怎么样',base,1.0,'official-fixed-symbols'),
        ('approx-advantage','八十万对六十万，优势在我！',convert('八十万对六十万，优势在我！'),1.4,'approximate-calibration'),
        ('approx-long','今天天气很好，我们一起去公园散步吧。',convert('今天天气很好，我们一起去公园散步吧。'),1.4,'approximate-calibration'),
        ('official-beijing-repeat','北京今天天气怎么样',base,1.4,'official-fixed-symbols')]
    report={'modelId':'KAN-TTS','repo':'AXERA-TECH/KAN-TTS','revision':REVISION,'provider':'AXCL C API','deviceIndex':0,
            'completed':False,'qualityValidated':False,'samples':[], 'sessions':[], 'negativeFrontendChecks':negative,
            'versions':{n:importlib.metadata.version(n) for n in ['numpy','jieba','pypinyin']},
            'binarySha256':sha(a.binary),'frontendSourceSha256':sha(root/'sdk/tools/gen_calib.py'),
            'timingScope':'synthesis includes CPU PNCA and tensor saving; executeMilliseconds is only synchronous AXCL execution, excluding transfers',
            'cpuStages':['Chinese frontend','pitch/energy embeddings','length regulation','PNCA decoder','WAV assembly']}
    lines=[]
    for id,text,segments,factor,kind in jobs:
        symbolfile=out/(id+'-symbols.txt');symbolfile.write_text('\n'.join(segments)+'\n',encoding='utf-8')
        report['samples'].append({'id':id,'text':text,'symbols':segments,'frontend':kind,'durationFactor':factor})
        lines.append('\t'.join([id,str(symbolfile),str(factor)]))
    (out/'jobs.tsv').write_text('\n'.join(lines)+'\n',encoding='utf-8');dump(out/'deployment-result.json',report)
    env={k:v for k,v in os.environ.items() if not k.startswith('KANTTS_')}
    start=time.perf_counter()
    completed=subprocess.run([str(a.binary.resolve()),str(root),str(out/'jobs.tsv'),str(out)],env=env)
    report['nativeProcessSeconds']=time.perf_counter()-start;report['nativeExitCode']=completed.returncode
    dump(out/'deployment-result.json',report);completed.check_returncode()
    schemas={}
    for path in sorted((out/'schema').glob('*-schema.json')):
        s=json.loads(path.read_text());s['provider']='AXCL C API';s['providers']=['AXCL C API'];s['calls']=[]
        s['sha256']=sha(root/s['model']);schemas[Path(s['model']).stem]=s
    assert len(schemas)==5
    report['sessions']=list(schemas.values());report['device']=json.loads((out/'schema/device.json').read_text())
    for sample in report['samples']:
        folder=out/sample['id'];sample.update(json.loads((folder/'result.json').read_text()))
        for line in (folder/'calls.jsonl').read_text().splitlines():
            call=json.loads(line);s=schemas[call['model']];call['sample']=sample['id']
            for side in ['inputs','outputs']:
                call[side]={}
                for desc in s[side]:
                    path=folder/(call['prefix']+('-in-' if side=='inputs' else '-out-')+desc['name']+'.bin')
                    arr=np.fromfile(path,dtype=desc['dtype']).reshape(desc['shape']);assert np.isfinite(arr).all()
                    call[side][desc['name']]={**desc,'file':str(path.relative_to(out)),'sha256':sha(path),'finite':True}
            s['calls'].append(call)
        arr=np.fromfile(folder/'audio.f32',dtype='<f4');assert len(arr)==sample['samples'] and np.isfinite(arr).all()
        sample['audio']={'file':sample['id']+'/output.wav','sha256':sha(folder/'output.wav'),'seconds':len(arr)/16000,
                         'peak':float(np.max(np.abs(arr))),'rms':float(np.sqrt(np.mean(arr.astype(np.float64)**2))),
                         'clippedSamples':int((np.abs(arr)>1).sum()),'rawSha256':sha(folder/'audio.f32')}
    for s in report['sessions']:
        s['allFinite']=True;s['runMilliseconds']=[c['executeMilliseconds'] for c in s['calls']]
        assert s['calls']
    report['completed']=True;dump(out/'deployment-result.json',report);print(json.dumps({'completed':True,'samples':len(jobs)},ensure_ascii=False))

if __name__=='__main__': main()
