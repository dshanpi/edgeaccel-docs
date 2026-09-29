"""Run official IGEV++ stereo pairs with AXCL and an explicit CPU reference."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import axengine
import numpy as np
import onnxruntime as ort
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument('--model-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root, out = a.model_dir.resolve(), a.output.resolve()
assert out != root and not out.exists(), 'Choose a new output directory'
source = root / 'infer.py'
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_sha == 'd1c63eae541d20e24cd6612edfc25e51b49ed555320d885ce3af8bd98db0599c'
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
namespace = {'__name__': 'igev_official_helpers'}
exec(compile(source.read_text('utf-8'), str(source), 'exec'), namespace)
out.mkdir(parents=True)
report = {'modelId': 'IGEV-plusplus', 'provider': 'AXCLRTExecutionProvider',
          'completed': False, 'upstreamScriptSha256': source_sha,
          'sessions': [], 'cpuSessions': [], 'samples': [],
          'visualization': {'quantity': 'horizontal disparity in 512x384 input pixels',
                            'colormap': 'jet', 'range': [0, 128],
                            'clippingAffectsVisualizationOnly': True}}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save():
    (out / 'deployment-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def session_record(session, weight, seconds, provider):
    return {'model': weight, 'weightSha256': digest(root / weight), 'provider': provider,
            'loadSeconds': seconds, 'allFinite': True, 'runMilliseconds': [],
            'inputs': [{'name': m.name, 'shape': list(m.shape), 'dtype': str(getattr(m, 'dtype', getattr(m, 'type', '')))} for m in session.get_inputs()],
            'outputs': [{'name': m.name, 'shape': list(m.shape)} for m in session.get_outputs()]}

weight = 'models/AX650_RTIGEV.axmodel'
t = time.perf_counter()
card = axengine.InferenceSession(str(root / weight), providers=['AXCLRTExecutionProvider'])
card_record = session_record(card, weight, time.perf_counter() - t, 'AXCLRTExecutionProvider')
report['sessions'].append(card_record)
options = ort.SessionOptions()
options.intra_op_num_threads = 2
options.inter_op_num_threads = 1
t = time.perf_counter()
cpu = ort.InferenceSession(str(root / 'models/AX650.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
cpu_record = session_record(cpu, 'models/AX650.onnx', time.perf_counter() - t, 'CPUExecutionProvider')
report['cpuSessions'].append(cpu_record)
save()
pairs = sorted((root / 'demo-imgs').glob('*/im0.png'))
assert len(pairs) == 7, 'Download all seven official stereo pairs'
for left in pairs:
    right = left.with_name('im1.png')
    assert right.is_file()
    pair = left.parent.name
    # Use the official PIL resize / RGB slice / float32 NCHW loader unchanged.
    l = namespace['load_image'](str(left)).cpu().numpy()
    r = namespace['load_image'](str(right)).cpu().numpy()
    inputs = {'left': l.transpose(0, 2, 3, 1).astype(np.uint8),
              'right': r.transpose(0, 2, 3, 1).astype(np.uint8)}
    for m in card.get_inputs():
        assert inputs[m.name].shape == tuple(m.shape) and inputs[m.name].dtype == np.dtype(m.dtype)
    card_outputs = []
    times = []
    for repeat in range(2):
        t = time.perf_counter()
        result = card.run(None, inputs)
        times.append((time.perf_counter() - t) * 1000)
        assert all(np.isfinite(v).all() for v in result)
        card_outputs.append(result)
    repeat_exact = all(np.array_equal(x, y) for x, y in zip(*card_outputs))
    t = time.perf_counter()
    reference = cpu.run(None, {'left': 2 * (l / 255.0) - 1.0, 'right': 2 * (r / 255.0) - 1.0})
    cpu_ms = (time.perf_counter() - t) * 1000
    assert all(np.isfinite(v).all() for v in reference)
    actual, expected = card_outputs[0][0].squeeze(), reference[0].squeeze()
    assert actual.shape == expected.shape == (384, 512)
    error = np.abs(actual.astype(np.float64) - expected.astype(np.float64))
    raw_name = pair + '-raw.npz'
    np.savez_compressed(out / raw_name, card=actual, repeat=card_outputs[1][0].squeeze(), cpu=expected,
                        left=inputs['left'], right=inputs['right'])
    for side, pixels in [('left', inputs['left']), ('right', inputs['right'])]:
        Image.fromarray(pixels[0]).save(out / (pair + '-' + side + '.png'))
    for label, value in [('card', actual), ('cpu', expected)]:
        plt.imsave(out / (pair + '-' + label + '.png'), value, cmap='jet', vmin=0, vmax=128)
    plt.imsave(out / (pair + '-error.png'), error, cmap='magma', vmin=0, vmax=16)
    item = {'pair': pair, 'inputSize': [512, 384], 'leftSource': str(left.relative_to(root)),
            'rightSource': str(right.relative_to(root)), 'leftSourceSha256': digest(left), 'rightSourceSha256': digest(right),
            'originalSize': list(Image.open(left).size), 'allFinite': True, 'repeatExact': repeat_exact,
            'runMilliseconds': times, 'cpuMilliseconds': cpu_ms, 'rawFile': raw_name, 'rawSha256': digest(out / raw_name),
            'maePixels': float(error.mean()), 'rmsePixels': float(np.sqrt(np.mean(error ** 2))),
            'p95AbsoluteErrorPixels': float(np.percentile(error, 95)),
            'fractionErrorOver1Pixel': float(np.mean(error > 1)),
            'cardPercentiles': {str(q): float(np.percentile(actual, q)) for q in [0, 25, 50, 75, 95, 100]},
            'visualizationClippedFraction': float(np.mean((actual < 0) | (actual > 128)))}
    report['samples'].append(item)
    card_record['runMilliseconds'].extend(times)
    cpu_record['runMilliseconds'].append(cpu_ms)
    save()
    print(pair, 'card ms', times, 'CPU ms', cpu_ms, 'MAE px', item['maePixels'], flush=True)
report['completed'] = True
save()
