#!/usr/bin/env python3
"""Ask a local AXLLM SmolVLM2 server about one image or a frames directory."""
import argparse,base64,json,urllib.request
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
media=parser.add_mutually_exclusive_group(required=True)
media.add_argument('--image',type=Path)
media.add_argument('--frames',type=Path)
parser.add_argument('--question',required=True)
parser.add_argument('--url',default='http://127.0.0.1:8514')
args=parser.parse_args()
path=(args.image or args.frames).resolve()
if args.image:
    if not path.is_file():raise FileNotFoundError(path)
    mime='image/png' if path.suffix.lower()=='.png' else 'image/jpeg'
    uri='data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
    part={'type':'image_url','image_url':{'url':uri}}
else:
    if not path.is_dir():raise NotADirectoryError(path)
    # AXLLM resolves this path on the server: run the client on the same host.
    part={'type':'video_url','video_url':{'url':str(path)}}
payload={'model':'AXERA-TECH/SmolVLM2-256M-Video-Instruct_Ax650',
         'messages':[{'role':'user','content':[{'type':'text','text':args.question},part]}],
         'temperature':0,'max_tokens':96,'stream':True,'stream_options':{'include_usage':True}}
request=urllib.request.Request(args.url.rstrip('/')+'/v1/chat/completions',
                              data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
done=False
with opener.open(request,timeout=150) as response:
    for raw in response:
        line=raw.decode('utf-8').strip()
        if not line.startswith('data:'):continue
        chunk=line[5:].strip()
        if chunk=='[DONE]':done=True;break
        event=json.loads(chunk)
        if 'error' in event:raise RuntimeError(event['error'])
        for choice in event.get('choices',[]):
            print(choice.get('delta',{}).get('content') or '',end='',flush=True)
            if choice.get('finish_reason')=='length':print('\n[达到本次输出长度限制]',flush=True)
print()
if not done:raise RuntimeError('Incomplete response stream')
