import socket,subprocess,json,time,re
from pathlib import Path
ev=Path('/home/baiwen/ax-pipeline/six/evidence/vlc-disconnect-20260918')
rows=[]
for i in range(3):
 s=socket.socket(socket.AF_UNIX);s.settimeout(1);s.connect('/run/user/1001/ax-six-vlc-live.sock');s.sendall(b'stats\nstatus\n');raw=b''
 try:
  while b'status: returned' not in raw:
   b=s.recv(65536)
   if not b:break
   raw+=b
 except socket.timeout:pass
 s.close();txt=raw.decode(errors='replace');(ev/('restored-stats-%d.log'%i)).write_text(txt)
 row={'time':time.time(),'playing':'play state: 3' in txt}
 for key,pat in [('decoded',r'video decoded\s*:\s*(\d+)'),('displayed',r'frames displayed\s*:\s*(\d+)'),('lost',r'frames lost\s*:\s*(\d+)'),('corrupted',r'demux corrupted\s*:\s*(\d+)')]:
  m=re.search(pat,txt);row[key]=int(m[1]) if m else None
 assert row['playing'] and row['displayed'],row
 if rows:row['display_fps']=(row['displayed']-rows[-1]['displayed'])/(row['time']-rows[-1]['time'])
 print(json.dumps(row),flush=True);rows.append(row)
 if i<2:time.sleep(30)
(ev/'restored-check.json').write_text(json.dumps(rows,indent=2))
assert all(r['corrupted']==0 for r in rows)
assert rows[-1]['lost']==rows[0]['lost']
