"""Run the pinned official RIFE video pipeline with AXCL and bounded host queues."""
import argparse
import hashlib
import importlib.util
import inspect
import json
import sys
import time
import textwrap
from pathlib import Path

import axengine
import axengine._axclrt as axcl_backend
import cv2
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--model-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--resolution', choices=['720p','1080p','4k'], required=True)
a = p.parse_args()
root, out = a.model_dir.resolve(), a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
width, height = {'720p':(1280,720),'1080p':(1920,1080),'4k':(3840,2160)}[a.resolution]
source = root / 'video/demo.mp4'
cap = cv2.VideoCapture(str(source))
assert cap.isOpened()
fps = cap.get(cv2.CAP_PROP_FPS)
source_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
source_size = [int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))]
cap.release()
assert source_count > 1 and fps > 0
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
# PyAXEngine 0.1.3.rc3 inverts this mapping and cannot request a subset.
# Correct only this process; leave the installed package unchanged.
backend_source = textwrap.dedent(inspect.getsource(axcl_backend.AXCLRTSession.run))
old_mapping = 'outputs_ranks = [output_names.index(_on) for _on in origin_output_names]'
assert backend_source.count(old_mapping) == 1, 'This helper expects the pinned PyAXEngine 0.1.3.rc3 implementation'
patched_backend = backend_source.replace(old_mapping, 'outputs_ranks = [origin_output_names.index(_on) for _on in output_names]')
backend_namespace = {}
exec(compile(patched_backend,'<rife-selected-output>','exec'),vars(axcl_backend),backend_namespace)
axcl_backend.AXCLRTSession.run = backend_namespace['run']
record = {'modelId':'RIFE.axera','variant':a.resolution,'provider':'AXCLRTExecutionProvider',
          'completed':False,'sourceVideoSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'sourceFrames':source_count,'sourceFps':fps,'sourceSize':source_size,
          'processedSize':[width,height],'resizeInterpolation':'OpenCV INTER_LINEAR',
          'retrievalScope':'Final interpolated image only; the full model is executed',
          'backendRunSourceSha256':hashlib.sha256(backend_source.encode()).hexdigest(),
          'sessions':[],'results':[]}
def save():
    (out/'deployment-result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')

original_session = axengine.InferenceSession
class MeasuredSession:
    def __init__(self, path):
        started = time.perf_counter()
        self.session = original_session(path,providers=['AXCLRTExecutionProvider'])
        self.row = {'model':Path(path).relative_to(root).as_posix(),'loadSeconds':time.perf_counter()-started,
                    'inputs':[{'name':m.name,'shape':list(m.shape),'dtype':str(m.dtype)} for m in self.session.get_inputs()],
                    'outputs':[{'name':m.name,'shape':list(m.shape)} for m in self.session.get_outputs()],
                    'retrievedOutput':self.session.get_outputs()[-1].name,
                    'runMilliseconds':[],'allFinite':True}
        record['sessions'].append(self.row)
        save()
    def __getattr__(self, name):
        return getattr(self.session,name)
    def run(self, names, feeds):
        for m in self.session.get_inputs():
            assert list(feeds[m.name].shape)==list(m.shape) and feeds[m.name].dtype==np.dtype(m.dtype), (m.shape,feeds[m.name].shape)
        started = time.perf_counter()
        selected_names = [self.session.get_outputs()[-1].name]
        values = self.session.run(selected_names,feeds)
        elapsed = (time.perf_counter()-started)*1000
        self.row['runMilliseconds'].append(elapsed)
        self.row['allFinite'] &= all(np.isfinite(v).all() for v in values)
        save()
        assert self.row['allFinite'], 'Non-finite interpolation tensor'
        if len(self.row['runMilliseconds'])==1:
            repeated = self.session.run(selected_names,feeds)
            assert all(np.isfinite(v).all() for v in repeated)
            record['firstPairRepeatExact'] = all(np.array_equal(x,y) for x,y in zip(values,repeated))
            assert record['firstPairRepeatExact']
            record['extraRepeatCalls'] = 1
            del repeated
            tensor = next(iter(feeds.values()))
            for label, v in [('left',tensor[:,:3]),('right',tensor[:,3:]),('middle',values[-1])]:
                rgb = np.clip(v[0]*255,0,255).astype(np.uint8).transpose(1,2,0)[:height,:width]
                assert rgb.shape==(height,width,3)
                assert cv2.imwrite(str(out/f'{label}.png'),cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
            record['firstPairInputSha256'] = hashlib.sha256(tensor.tobytes()).hexdigest()
            record['firstPairOutputSha256'] = [hashlib.sha256(v.tobytes()).hexdigest() for v in values]
            save()
        return values

axengine.InferenceSession = MeasuredSession
sys.path.insert(0,str(root))
original = (root/'run_axmodel.py').read_text()
record['upstreamScriptSha256'] = hashlib.sha256(original.encode()).hexdigest()
# Keep the official frame decision logic and model preprocessing/postprocessing.
# Bound queues so full-resolution frames cannot accumulate across the whole video.
patched = original.replace('Queue(maxsize=500)','Queue(maxsize=2)')
old = '_thread.start_new_thread(clear_write_buffer, (args, write_buffer, vid_out))'
assert original.count(old)==1
patched = patched.replace(old,'writer = threading.Thread(target=clear_write_buffer, args=(args, write_buffer, vid_out), daemon=True)\n    writer.start()')
old = 'while(not write_buffer.empty()):\n        time.sleep(0.1)'
assert patched.count(old)==1
patched = patched.replace(old,'writer.join()')
patched = 'import threading\n'+patched
namespace = {'__name__':'pinned_rife_pipeline','__file__':str(root/'run_axmodel.py')}
exec(compile(patched,str(root/'run_axmodel.py'),'exec'),namespace)
original_reader = namespace['read_video']
def resized_reader(path):
    for frame in original_reader(path):
        yield cv2.resize(frame,(width,height),interpolation=cv2.INTER_LINEAR) if frame.shape[:2]!=(height,width) else frame
namespace['read_video'] = resized_reader
args = namespace['parser'].parse_args(['--video',str(source),'--model',str(root/f'model/rife_x2_{a.resolution}.axmodel'),
                                       '--output',str(out/'interpolated.mp4'),'--fps',str(round(fps*2))])
namespace['args'] = args
start = time.perf_counter()
namespace['run'](args)
record['pipelineSeconds'] = time.perf_counter()-start
check = cv2.VideoCapture(str(out/'interpolated.mp4'))
assert check.isOpened()
output_fps = check.get(cv2.CAP_PROP_FPS)
decoded = 0
while True:
    ok, frame = check.read()
    if not ok:break
    assert frame.shape==(height,width,3)
    decoded += 1
check.release()
assert output_fps==round(fps*2) and decoded==source_count*2-1, (output_fps,decoded,source_count)
record['results']=[{'outputVideo':'interpolated.mp4','decodedFrames':decoded,'fps':output_fps,'size':[width,height],
                    'fileSha256':hashlib.sha256((out/'interpolated.mp4').read_bytes()).hexdigest()}]
record['completed']=True
save()
print(json.dumps(record,ensure_ascii=False))
