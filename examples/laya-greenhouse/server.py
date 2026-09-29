"""Loopback-only desktop demonstration; one real inference job at a time."""
import argparse, json, math, queue, signal, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUESTIONS = {
    'action': {'type':'choice','instructions':'根据温室状态，选择当前最需要的操作。','criteria':['通风','补水','补光','保持']},
    'urgency': {'type':'score','instructions':'温室需要处理的紧急程度？','criteria':['无需处理','需要处理','立即处理']},
    'water': {'type':'noul','instructions':'植物缺水，需要浇水。'},
    'heat': {'type':'noul','instructions':'温室太热，需要通风降温。'},
}
def make_request(data):
    if not isinstance(data, dict): raise ValueError('输入必须是 JSON 对象')
    values = {}
    for key, low, high in [('temperature',0,50),('humidity',0,100),('soil',0,100),('light',0,100)]:
        value = data.get(key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('环境数值超出范围: '+key)
        values[key] = value
    note = data.get('note','')
    if not isinstance(note,str) or len(note)>80: raise ValueError('观察描述最多 80 个字符')
    state = f"温室温度{values['temperature']:g}℃，空气湿度{values['humidity']:g}%，土壤湿度{values['soil']:g}%，光照强度{values['light']:g}%。观察：{note}"
    return {'state':state,'questions':QUESTIONS}

class Engine:
    def __init__(self, model_dir):
        self.lock=threading.Lock();self.messages=queue.Queue();self.status='loading'
        self.proc=subprocess.Popen([sys.executable,'-u',str(ROOT/'worker.py'),model_dir],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
        threading.Thread(target=self.read,daemon=True).start()
        threading.Thread(target=self.ready,daemon=True).start()
    def read(self):
        for line in self.proc.stdout:
            try:
                item=json.loads(line)
                if isinstance(item,dict) and item.get('event') in ['ready','result','invalid','error']: self.messages.put(item)
            except json.JSONDecodeError: print(line.rstrip(),file=sys.stderr)
        self.messages.put({'event':'error','error':'模型进程已退出'})
    def ready(self):
        try:
            item=self.messages.get(timeout=90)
            self.status='ready' if item['event']=='ready' else 'unavailable'
        except queue.Empty:
            self.status='unavailable';self.stop()
    def stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try: self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired: self.proc.kill()
    def run(self,request):
        if self.status!='ready': return 503,{'error':'模型尚未就绪，请等待加载完成或检查服务日志。'}
        if not self.lock.acquire(blocking=False): return 409,{'error':'正在处理上一条请求，请稍后重试。'}
        try:
            self.proc.stdin.write(json.dumps(request,ensure_ascii=False)+'\n');self.proc.stdin.flush()
            message=self.messages.get(timeout=25)
            if message['event']=='invalid': return 422,{'error':message['error']}
            if message['event']!='result': raise RuntimeError(message.get('error'))
            return 200,message['result']
        except (queue.Empty,RuntimeError,OSError):
            self.status='unavailable';self.stop()
            return 503,{'error':'推理未完成，已停止本次服务的模型进程。检查设备后重新启动服务。'}
        finally: self.lock.release()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model-dir',required=True);parser.add_argument('--port',type=int,default=8855);args=parser.parse_args()
    engine=Engine(args.model_dir)
    class Handler(BaseHTTPRequestHandler):
        def reply(self,code,data,mime='application/json; charset=utf-8'):
            body=json.dumps(data,ensure_ascii=False,allow_nan=False).encode() if isinstance(data,dict) else data
            self.send_response(code);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        def local(self): return self.headers.get('Host') in [f'127.0.0.1:{args.port}',f'localhost:{args.port}']
        def do_GET(self):
            if not self.local(): return self.reply(403,{'error':'仅允许本机访问'})
            if self.path=='/api/status': return self.reply(200,{'status':engine.status,'model':'Laya multilingual','provider':'AXCLRTExecutionProvider'})
            paths={'/':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css'),'/app.js':('app.js','text/javascript; charset=utf-8')}
            if self.path not in paths: return self.reply(404,{'error':'页面不存在'})
            name,mime=paths[self.path];self.reply(200,(ROOT/name).read_bytes(),mime)
        def do_POST(self):
            if not self.local() or self.headers.get('Origin') not in [None,f'http://127.0.0.1:{args.port}',f'http://localhost:{args.port}']: return self.reply(403,{'error':'请求来源不允许'})
            if self.path!='/api/decision': return self.reply(404,{'error':'接口不存在'})
            try:
                if self.headers.get('Content-Type','').split(';')[0]!='application/json': raise ValueError('需要 JSON 请求')
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=4096: raise ValueError('请求大小无效')
                self.connection.settimeout(10)
                request=make_request(json.loads(self.rfile.read(size)))
            except (ValueError,UnicodeDecodeError,TimeoutError): return self.reply(400,{'error':'输入格式或范围无效；描述最多 80 个字符。'})
            code,result=engine.run(request);self.reply(code,result)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    print(f'http://127.0.0.1:{args.port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close();engine.stop()
if __name__=='__main__': main()
