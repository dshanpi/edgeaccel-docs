"""Run the pinned official LCM pipeline on an AXCL card and retain real outputs."""
import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

REVISION = '4ba40db7f8fddbf3e4f86edacf7fb255bb45d339'
PROVIDER = 'AXCLRTExecutionProvider'

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model-dir', type=Path, required=True, help='Root of the pinned official repository')
    p.add_argument('--variant', choices=['512', '1024'], default='512')
    p.add_argument('--prompt', required=True)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--init-image', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert 0 <= a.seed < 2**32
    assert not (a.variant == '1024' and a.init_image), 'The large variant has no VAE encoder'
    root = a.model_dir.resolve()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    folder = root / ('models' if a.variant == '512' else 'models_1024x768')
    height, width = (512, 512) if a.variant == '512' else (768, 1024)
    manifest = json.loads((root/'download-manifest.json').read_text())
    assert manifest['complete'] and manifest['revision'] == REVISION
    files = {f['path']: f for f in manifest['files']}
    launcher = root/'launcher.py'
    assert sha(launcher) == files['launcher.py']['verifiedHashes']['sha256']
    import axengine
    import numpy as np
    import torch
    from PIL import Image
    from transformers import CLIPTokenizer
    import importlib.metadata as md
    torch.set_num_threads(2)
    assert PROVIDER in axengine.get_available_providers()
    tokenizer = CLIPTokenizer.from_pretrained(folder/'tokenizer', local_files_only=True)
    token_ids = tokenizer(a.prompt, truncation=False)['input_ids']
    assert len(token_ids) <= 77, 'Prompt exceeds the compiled 77-token limit'
    rec = {'modelId': 'lcm-lora-sdv1-5', 'revision': REVISION, 'provider': PROVIDER,
           'completed': False, 'mode': 'img2img' if a.init_image else 'txt2img',
           'prompt': a.prompt, 'seed': a.seed, 'width': width, 'height': height,
           'timesteps': [499,259] if a.init_image else [999,759,499,259],
           'tokenIdsUnpadded': token_ids, 'sessions': [], 'calls': [],
           'launcherSha256': sha(launcher), 'runnerSha256': sha(__file__),
           'versions': {n:md.version(n) for n in ['torch','transformers','diffusers','numpy','Pillow']}}
    def save():
        (out/'deployment-result.json').write_text(json.dumps(rec, indent=2)+'\n')
    if a.init_image:
        a.init_image = a.init_image.resolve()
        rec['inputImageSha256'] = sha(a.init_image)
        Image.open(a.init_image).convert('RGB').resize((width,height)).save(out/'input.png')
    save()
    spec = importlib.util.spec_from_file_location('lcm_official_launcher', launcher)
    official = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(official)
    class Session:
        def __init__(self, path, backend):
            assert backend == 'axe'
            path = Path(path).resolve()
            name = path.relative_to(root).as_posix()
            assert sha(path) == files[name]['verifiedHashes']['sha256']
            self.record = {'model':name, 'sha256':sha(path), 'runMilliseconds':[], 'allFinite':True}
            rec['sessions'].append(self.record)
            save()
            started = time.perf_counter()
            self.s = axengine.InferenceSession(str(path), providers=[PROVIDER])
            actual = self.s.get_providers()
            assert actual == PROVIDER or actual == [PROVIDER], actual
            self.record.update(providerActual=actual, loadMilliseconds=1000*(time.perf_counter()-started))
            for kind in ['inputs','outputs']:
                self.record[kind] = [{'name':n.name,'shape':list(n.shape),'dtype':str(n.dtype)} for n in getattr(self.s,'get_'+kind)()]
            save()
        def get_inputs(self): return self.s.get_inputs()
        def run(self, names, feeds):
            nodes = self.s.get_inputs()
            assert set(feeds) == {n.name for n in nodes}
            def entry(name,v):
                return {'name':name,'shape':list(v.shape),'dtype':str(v.dtype),'sha256':hashlib.sha256(v.tobytes()).hexdigest()}
            for n in nodes:
                assert list(feeds[n.name].shape) == list(n.shape) and feeds[n.name].dtype == np.dtype(n.dtype), (n,feeds[n.name].shape)
            call = {'model':self.record['model'], 'inputs':[entry(n.name,feeds[n.name]) for n in nodes], 'completed':False}
            rec['calls'].append(call)
            save()
            start = time.perf_counter()
            values = self.s.run(names, feeds)
            ms = 1000*(time.perf_counter()-start)
            self.record['runMilliseconds'].append(ms)
            finite = all(np.isfinite(v).all() for v in values)
            self.record['allFinite'] &= bool(finite)
            call.update(runMilliseconds=ms, outputs=[entry(n.name,v) for n,v in zip(self.s.get_outputs(),values)], allFinite=bool(finite),completed=True)
            save()
            assert finite, 'Non-finite model output'
            return values
    official.create_session = Session
    sys.argv = ['launcher.py','--backend','axe','--model_dir',str(folder),'--isize',f'{height}x{width}',
                '--prompt',a.prompt,'--seed',str(a.seed),'--save_dir',str(out/'output.png')]
    if a.init_image: sys.argv += ['--init_image',str(a.init_image)]
    started = time.perf_counter()
    official.main()
    rec['pipelineSecondsIncludingLoadAndHash'] = time.perf_counter()-started
    pixels = np.asarray(Image.open(out/'output.png'))
    assert pixels.shape == (height,width,3) and pixels.std() > 1
    assert len(rec['calls']) == (5 if a.init_image else 6)
    rec.update(completed=True, imageSha256=sha(out/'output.png'), pixelSha256=hashlib.sha256(pixels.tobytes()).hexdigest(),
               imageStandardDeviation=float(pixels.std()), npuCallTotalMilliseconds=sum(c['runMilliseconds'] for c in rec['calls']))
    save()
    print(json.dumps(rec, indent=2), flush=True)

if __name__ == '__main__': main()
