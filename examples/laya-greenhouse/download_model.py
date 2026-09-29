"""Download the five locked official files, then verify SHA256."""
import argparse,hashlib,json,os,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);a=p.parse_args()
lock=json.loads(Path(__file__).with_name('model-lock.json').read_text())
for name,digest in lock['files'].items():
    dest=a.model_dir/name;dest.parent.mkdir(parents=True,exist_ok=True)
    def valid(path):
        if not path.is_file():return False
        with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()==digest
    if valid(dest):print('已校验',name,flush=True);continue
    if dest.exists():raise RuntimeError(f'{dest} 与固定版本不同；请改用空目录，保留原文件。')
    temp=dest.with_name(dest.name+'.part')
    url=f"https://huggingface.co/{lock['repo']}/resolve/{lock['revision']}/{name}"
    print('下载',name,flush=True)
    with urllib.request.urlopen(url,timeout=90) as source,temp.open('wb') as output:
        while chunk:=source.read(1024*1024):output.write(chunk)
    if not valid(temp):raise RuntimeError('SHA256 不一致: '+name)
    temp.replace(dest)
print('5 个文件已校验。可启动温室应用。',flush=True)
