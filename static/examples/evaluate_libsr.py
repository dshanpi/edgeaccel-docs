#!/usr/bin/env python3
"""Evaluate only the controlled downsample/restore example saved by libsr_card.py."""
import argparse,hashlib,json,math
from pathlib import Path
import cv2
import numpy as np

def score(a,b):
    a=a.astype(np.float64);b=b.astype(np.float64)
    mse=float(np.mean((a-b)**2))
    kernel=cv2.getGaussianKernel(11,1.5);window=kernel@kernel.T
    blur=lambda x:cv2.filter2D(x,-1,window)[5:-5,5:-5]
    ma,mb=blur(a),blur(b);va=blur(a*a)-ma*ma;vb=blur(b*b)-mb*mb;cab=blur(a*b)-ma*mb
    ssim=((2*ma*mb+6.5025)*(2*cab+58.5225))/((ma*ma+mb*mb+6.5025)*(va+vb+58.5225))
    return {'mse':mse,'psnrDb':10*math.log10(255**2/mse) if mse else None,'ssim':float(ssim.mean())}

def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);a=p.parse_args()
    r=json.loads((a.results/'deployment-result.json').read_text(encoding='utf-8'))
    assert r['modelId']=='libsr.axera' and r['completed']
    samples={s['name']:s for s in r['samples']};assert 'cat-downsample' in samples,'Run the default examples first'
    def image(item):
        path=a.results/item['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'];return cv2.imread(str(path))
    original=image(samples['cat']['input']);s=samples['cat-downsample'];small=image(s['input'])
    assert np.array_equal(cv2.resize(original,(240,180),interpolation=cv2.INTER_AREA),small)
    sr=image(s['output']);bc=image(s['bicubic']);assert sr.shape==bc.shape==original.shape
    result={'scope':'One JPEG / INTER_AREA x0.5 / x2 restoration; BGR channels, no color conversion; PSNR all pixels; SSIM 11x11 Gaussian sigma1.5, valid window centers, three-channel mean. No full benchmark.',
        'libsr':score(sr,original),'bicubic':score(bc,original)}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
