"""Run fixed Janus-Pro-1B official understanding or full image generation on an AXCL card."""
import argparse,datetime,gc,hashlib,json,os,shutil,sys,time
from pathlib import Path
import axengine
import numpy as np
import onnxruntime as ort
import torch

MID='Janus-Pro-1B';REVISION='6627e1e38ec2a3ef0d94e4249e8b5f619522ad70'
PROCESSOR_REVISION='1daa72fa409002d40931bd7b36a9280362469ead'
PROVIDER='AXCLRTExecutionProvider'
SOURCES={'understand':('infer_axmodel_und.py','0ac584f22ff0e2f276ac35bb0e5f4e0889aa229c87ff9a7599e9c084ca9e4532'),
         'generate':('infer_axmodel_gen.py','8deab778fae0a7c6bde9003f76697aa0463f3e7531a80109b00f972bdd83e32c')}
PROCESSOR_HASHES = {'LICENSE-CODE': '6e4c38e1172f42fdbff13edf9a7a017679fb82b0fde415a3e8b3c31c6ed4a4e4', 'janus/__init__.py': '3790984df4c51224d3ee6acdaeb1934b2bc339590654ede913f7d69bcba0700c', 'janus/janusflow/__init__.py': '3790984df4c51224d3ee6acdaeb1934b2bc339590654ede913f7d69bcba0700c', 'janus/janusflow/models/__init__.py': '81526804aa517e7cbac3f4294eb4e1fe20aa52d54964bb9cb737cf42af9d283c', 'janus/janusflow/models/clip_encoder.py': '1fdf2c5579a58b5cdaad9bfff96f45d936c18d7aa0ff4ee404f56bf06b2be0c3', 'janus/janusflow/models/image_processing_vlm.py': '364deb2b4782c25fa1a1878eaefd62886ed9bf72a5645176000cd55cddb0453d', 'janus/janusflow/models/modeling_vlm.py': '8a02ca537e7a1a10377a9331e947b9c54f8dfc5ce41d644319e3dd0e8428e067', 'janus/janusflow/models/processing_vlm.py': 'c33297c38f61f5a1dd47b046e85aef793c6a63699901b7ed29f5c6b846daf317', 'janus/janusflow/models/siglip_vit.py': '6966b2c72d1906429dc58fc2cf6548613904ec571e4a4a83f212a46b5fe9e932', 'janus/janusflow/models/uvit.py': '05dce4c0ba52aacf3d9facfe344cbf87cbc27208b22adddddd86f3ba7a1c8112', 'janus/models/__init__.py': '81526804aa517e7cbac3f4294eb4e1fe20aa52d54964bb9cb737cf42af9d283c', 'janus/models/clip_encoder.py': 'cb0c56afa47b3b810d9d5694e8240cb1e0ddb11b697c1740161a632ec5febee3', 'janus/models/image_processing_vlm.py': '364deb2b4782c25fa1a1878eaefd62886ed9bf72a5645176000cd55cddb0453d', 'janus/models/modeling_vlm.py': '3a676a7e373bb30f35f15f681ff1b03246f562fa33e31bd709340202bae4341f', 'janus/models/processing_vlm.py': 'e506b5bec2dd4f28d77f4430374cd307bf5e1892a464c291dcb3d62eda4de17e', 'janus/models/projector.py': '0573f1e238f88c80dd658649fe6a374a6ce06930150bb07140cb94d701337480', 'janus/models/siglip_vit.py': '4195dcbb4b57faaed56584aba8523e4d555b9d25d80856ebccfa023d4f39b2fe', 'janus/models/vq_model.py': 'a1328dfcad344170342528cfc3aeba7ade7f990ef4b7f0025d658b6e09f9f8ad', 'janus/utils/__init__.py': 'bbc0bef9e809313fc30e6d091b77eb5c649034dbfa71f200ba63e1821ce4c619', 'janus/utils/conversation.py': 'e1e201df4b480b34b4c6f442b91321dd27b6fcf22c5c91e44e5624283a9b539b', 'janus/utils/io.py': '28d583b56f3ac84d76a0ebbac02850eb3d58e6ff4c6a19e483891ea0c7c627c1', 'pyproject.toml': 'a235c3adbc8376b440968d7d95a0f5e45b072edaa9dc62944f70a104a9cebff2'}

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--janus-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=['understand','generate'],required=True)
    p.add_argument('--question');p.add_argument('--image',type=Path);p.add_argument('--description')
    p.add_argument('--max-new-tokens',type=int,default=128);p.add_argument('--seed',type=int,default=0)
    a=p.parse_args();assert 1<=a.max_new_tokens<=384
    root=a.model_dir.resolve();out=a.output.resolve();processor=a.janus_dir.resolve()
    assert len(PROCESSOR_HASHES)>0
    for rel,digest in PROCESSOR_HASHES.items():
        assert hashlib.sha256((processor/rel).read_text(encoding='utf-8').encode()).hexdigest()==digest,rel
    sys.path.insert(0,str(processor));os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    assert PROVIDER in axengine.get_available_providers()
    source_name,source_hash=SOURCES[a.mode];assert sha(root/source_name)==source_hash
    out.mkdir(parents=True,exist_ok=False);(out/'source').mkdir()
    r={'modelId':MID,'revision':REVISION,'provider':PROVIDER,'mode':a.mode,'completed':False,
       'sessions':[],'cpuSessions':[],'samples':[],'sourceFile':source_name,'sourceSha256':source_hash,
       'processorRevision':PROCESSOR_REVISION,'processorCanonicalHashes':PROCESSOR_HASHES,
       'sessionProviderOverride':PROVIDER,'cpuIntraOpThreads':2,'seed':a.seed,
       'maxNewTokens':a.max_new_tokens if a.mode=='understand' else None,
       'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'deployment-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    axfactory=axengine.InferenceSession;cpufactory=ort.InferenceSession;current_sample=0
    class Measured:
        def __init__(self,path,providers=None,**kwargs):
            path=Path(path).resolve();cpu=path.suffix=='.onnx';start=time.perf_counter()
            if cpu:
                opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1
                self.session=cpufactory(str(path),sess_options=opts,providers=['CPUExecutionProvider'])
                selected='CPUExecutionProvider';group='cpuSessions'
            else:
                self.session=axfactory(str(path),providers=[PROVIDER]);selected=PROVIDER;group='sessions'
            assert self.session.get_providers() in (selected,[selected])
            self.row={'model':path.relative_to(root).as_posix(),'provider':selected,'sampleIndex':current_sample,
                      'weightSha256':sha(path),'loadSeconds':time.perf_counter()-start,
                      'runMilliseconds':[],'allFinite':True,'shapeGroups':{}}
            r[group].append(self.row);save()
        def run(self,names,feed,shape_group=None):
            assert all(np.isfinite(v).all() for v in feed.values())
            start=time.perf_counter()
            values=self.session.run(names,feed) if shape_group is None else self.session.run(names,feed,shape_group=shape_group)
            self.row['runMilliseconds'].append((time.perf_counter()-start)*1000)
            finite=bool(all(np.isfinite(v).all() for v in values));self.row['allFinite'] &= finite;assert finite
            group=str(shape_group or 0)
            if group not in self.row['shapeGroups']:
                self.row['shapeGroups'][group]={'calls':0,'inputs':{k:{'shape':list(v.shape),'dtype':str(v.dtype)} for k,v in feed.items()},
                                               'outputs':[{'shape':list(v.shape),'dtype':str(v.dtype)} for v in values]}
            self.row['shapeGroups'][group]['calls']+=1
            return values
    oldcwd=Path.cwd();oldargv=sys.argv.copy();namespace=None
    try:
        axengine.InferenceSession=Measured;ort.InferenceSession=Measured;os.chdir(root)
        samples=[a.question] if a.question else ['Describe the image in one sentence.','How many astronauts?']
        if a.mode=='generate':samples=[a.description or 'A small red robot watering a green plant on a wooden desk, warm sunlight, clean illustration.']
        for index,text in enumerate(samples,1):
            current_sample=index;torch.manual_seed(a.seed);np.random.seed(a.seed)
            source=(root/source_name).read_text();changes=[]
            def replace(before,after,count=1):
                nonlocal source
                assert source.count(before)==count,(before,source.count(before))
                source=source.replace(before,after);changes.append({'before':before,'after':after,'count':count})
            sys.argv=[source_name,'--tokenizer_dir',str(root/'janus_pro_1b_tokenizer'),'--axmodel_path',str(root/'janus_pro_1b_axmodel')]
            if a.mode=='understand':
                picture=a.image.resolve() if a.image else root/'imgs/image.png'
                sys.argv+=['--vit_axmodel_path',str(root/'vit_axmodel/janus_warp_vit.axmodel'),'-i',str(picture)]
                replace('embeds = np.load(os.path.join(args.axmodel_path, "model.embed_tokens.weight.npy"))',
                        'embeds = np.load(os.path.join(args.axmodel_path, "model.embed_tokens.weight.npy"), mmap_mode="r")')
                replace('question = "Please describe the picture."','question = '+repr(text))
                replace('token_len = len(token_ids)','token_len = len(token_ids)\nassert 0 < token_len <= 640, "Shorten the question: compiled prefill is 640 tokens"')
                replace('for start_indice in tqdm(range(lastN + 1), desc="Decoder"): # lastN + 1',
                        f'for start_indice in tqdm(range(token_len, min(token_len + {a.max_new_tokens} - 1, lastN)) if token_ids[-1] != tokenizer.eos_token_id else [], desc="Decoder"):')
                replace('print("model load done!")','print("model load done!")\n_generation_start = _clock.perf_counter()')
            else:
                replace('embeds = np.load(f"{axmodel_path}/model.embed_tokens.weight.npy")',
                        'embeds = np.load(f"{axmodel_path}/model.embed_tokens.weight.npy", mmap_mode="r")')
                replace("codebook_entry_embedding = torch.load('./embeds/codebook_entry_embedding.pt', map_location=torch.device('cpu'))",
                        "codebook_entry_embedding = torch.load('./embeds/codebook_entry_embedding.pt', map_location=torch.device('cpu'), weights_only=True)")
                original='description = "A close-up high-contrast photo of Sydney Opera House sitting next to Eiffel tower, under a blue night sky of roiling energy, exploding yellow stars, and radiating swirls of blue."'
                replace(original,'description = '+repr(text))
                replace('batch, token_len, seq_dim = inputs_embeds.shape','batch, token_len, seq_dim = inputs_embeds.shape\n    assert 0 < token_len <= 448, "Shorten the description to leave context for 576 image tokens"')
                replace("'generated_samples'",repr(str(out/'generated_samples')),count=2)
                replace('        PIL.Image.fromarray(visual_img[i]).save(save_path)',
                        '        PIL.Image.fromarray(visual_img[i]).save(save_path)\n    return {"imageTokenIds": generated_tokens.tolist(), "imageShape": list(visual_img.shape), "imagePath": save_path, "prompt": prompt}')
                replace('logger.info("model load done!")','logger.info("model load done!")\n_generation_start = _clock.perf_counter()')
                replace('\ngenerate(\n','\n_generation_result = generate(\n')
            used=out/'source'/f'{a.mode}-{index}.py';used.write_text(source)
            namespace={'__name__':'__main__','__file__':str(used),'_clock':time}
            started=time.perf_counter();exec(compile(source,str(used),'exec'),namespace)
            duration=time.perf_counter()-started;generation=time.perf_counter()-namespace['_generation_start']
            row={'input':text,'sourceChanges':changes,'usedSourceSha256':sha(used),'processSeconds':duration,'generationSeconds':generation,'images':[]}
            if a.mode=='understand':
                ids=[int(i) for i in namespace['token_ids']];n=namespace['token_len'];generated=ids[n:];eos=int(namespace['tokenizer'].eos_token_id)
                target=out/f'input-{index}{picture.suffix}';shutil.copy2(picture,target)
                row['images']=[{'file':target.name,'source':str(picture.relative_to(root)) if picture.is_relative_to(root) else str(picture),
                                'sha256':sha(target),'pixelTensorSha256':hashlib.sha256(namespace['prepare_inputs']['pixel_values'].numpy().tobytes()).hexdigest()}]
                row.update(inputTokenIds=ids[:n],outputTokenIds=generated,inputTokens=n,generatedTokens=len(generated),
                           output=namespace['tokenizer'].decode(generated,skip_special_tokens=True),hitEos=generated[-1]==eos,
                           stopReason='eos' if generated[-1]==eos else 'length-or-context',eosTokenId=eos)
                assert row['output'].strip();r['samples'].append(row);save();assert row['hitEos'],'Response did not reach EOS'
            else:
                row.update(namespace['_generation_result']);row['imagePath']=str(Path(row['imagePath']).relative_to(out))
                row['imageSha256']=sha(out/row['imagePath']);row['seed']=a.seed;row['cfgWeight']=5;row['temperature']=1
                assert len(row['imageTokenIds'])==1 and len(row['imageTokenIds'][0])==576
                assert row['imageShape']==[1,384,384,3]
                r['samples'].append(row);save()
            print(json.dumps({k:v for k,v in row.items() if k not in ['sourceChanges','inputTokenIds','outputTokenIds','imageTokenIds','prompt']},ensure_ascii=False),flush=True)
            namespace=None;gc.collect()
        r['completed']=True
    except BaseException as e:r['error']=repr(e);raise
    finally:
        namespace=None;axengine.InferenceSession=axfactory;ort.InferenceSession=cpufactory;os.chdir(oldcwd);sys.argv=oldargv;gc.collect()
        r['finishedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()

if __name__=='__main__':main()
