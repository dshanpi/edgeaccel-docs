"""AXCL Native API bridge session, serial execution with a fresh model per run."""
import atexit,ctypes as C,hashlib,json,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import ml_dtypes
PROVIDER='AXCLNativeAPI'
MODELS={};JOURNAL=None;COUNTER=0;LIB=None
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def configure(metadata,journal):
 global MODELS,JOURNAL,COUNTER,LIB
 j=json.loads(Path(metadata).read_text());assert j['completed'] and j['revision']=='6181fa78a78812dde065f76ad0f73425aec43747' and len(j['models'])==19
 MODELS={x['model']:x for x in j['models']};JOURNAL=Path(journal);JOURNAL.mkdir(parents=True,exist_ok=False);COUNTER=0
 binary=Path(__file__).with_name('libjina_native_bridge.so');LIB=C.CDLL(str(binary))
 LIB.jina_native_error.argtypes=[];LIB.jina_native_error.restype=C.c_char_p
 LIB.jina_native_init.argtypes=[];LIB.jina_native_init.restype=C.c_int
 LIB.jina_native_final.argtypes=[];LIB.jina_native_final.restype=None
 LIB.jina_native_run.argtypes=[C.c_char_p,C.c_uint32,C.c_uint32,C.POINTER(C.c_char_p),C.POINTER(C.c_void_p),C.POINTER(C.c_uint64),C.c_uint32,C.POINTER(C.c_char_p),C.POINTER(C.c_void_p),C.POINTER(C.c_uint64),C.POINTER(C.c_double),C.POINTER(C.c_double)];LIB.jina_native_run.restype=C.c_int
 assert LIB.jina_native_init()==0,LIB.jina_native_error().decode();atexit.register(LIB.jina_native_final)
 (JOURNAL/'metadata.json').write_text(json.dumps({'provider':PROVIDER,'backend':'native-cpp-bridge','binary':str(binary),'binarySha256':sha(binary),'shapeMetadataSha256':sha(Path(metadata))},indent=2))
class InferenceSession:
 def __init__(self,path,providers):
  assert providers==[PROVIDER] and JOURNAL is not None
  self.path=Path(path);self.meta=MODELS[self.path.name];self._sess=self
 def _unload(self):pass
 def get_providers(self):return PROVIDER
 def nodes(self,kind,group):
  g=self.meta['groups'][group];assert g['index']==group
  return [SimpleNamespace(name=n['name'],shape=n['shape'],dtype=np.dtype(ml_dtypes.bfloat16 if n['dtype']=='bfloat16' else n['dtype'])) for n in g[kind]]
 def get_inputs(self,group=0):return self.nodes('inputs',group)
 def get_outputs(self,group=0):return self.nodes('outputs',group)
 def run(self,output_names,input_feed,run_options=None,shape_group=0):
  global COUNTER
  ins=self.get_inputs(shape_group);outs=self.get_outputs(shape_group);assert set(input_feed)=={n.name for n in ins}
  assert output_names is None or output_names==[n.name for n in outs]
  index=COUNTER;COUNTER+=1;record={'index':index,'model':self.path.name,'providerActual':PROVIDER,'backend':'native-cpp-bridge','shapeGroup':shape_group,'inputs':[],'outputs':[],'completed':False}
  iv=[];ov=[]
  for n in ins:
   v=np.ascontiguousarray(input_feed[n.name]);assert list(v.shape)==n.shape and v.dtype==n.dtype;iv.append(v)
   record['inputs'].append({'name':n.name,'shape':n.shape,'dtype':str(n.dtype),'bytes':v.nbytes,'sha256':hashlib.sha256(v.tobytes()).hexdigest()})
  for n in outs:ov.append(np.zeros(n.shape,dtype=n.dtype))
  names=lambda nodes:(C.c_char_p*len(nodes))(*[n.name.encode() for n in nodes])
  ptrs=lambda arrays:(C.c_void_p*len(arrays))(*[v.ctypes.data for v in arrays])
  sizes=lambda arrays:(C.c_uint64*len(arrays))(*[v.nbytes for v in arrays])
  kernel=C.c_double();load=C.c_double();started=time.monotonic()
  try:
   rc=LIB.jina_native_run(str(self.path).encode(),shape_group,len(ins),names(ins),ptrs(iv),sizes(iv),len(outs),names(outs),ptrs(ov),sizes(ov),C.byref(kernel),C.byref(load))
   record.update(exitCode=rc,elapsedSeconds=time.monotonic()-started,kernelMilliseconds=kernel.value,loadMilliseconds=load.value)
   assert rc==0,LIB.jina_native_error().decode()
   for n,v in zip(outs,ov):
    assert np.isfinite(v.astype(np.float32)).all(),n.name
    record['outputs'].append({'name':n.name,'shape':n.shape,'dtype':str(n.dtype),'bytes':v.nbytes,'sha256':hashlib.sha256(v.tobytes()).hexdigest(),'allFinite':True})
   record['completed']=True;return ov
  finally:(JOURNAL/f'{index:04d}.json').write_text(json.dumps(record,indent=2)+'\n')
