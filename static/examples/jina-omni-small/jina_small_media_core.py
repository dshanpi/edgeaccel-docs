"""Experimental AXCL adapter: official Small weights and packed LoRA, short text only.

This is a validation candidate, not an accepted full multimodal deployment.
Mask construction and final-token pooling follow official ax-jina-v5-omnis.
"""
import argparse,hashlib,json,time,traceback
from pathlib import Path
import numpy as np
import ml_dtypes
from tokenizers import Tokenizer
import jina_small_native_session as axengine

BF=ml_dtypes.bfloat16
MID='jina-embeddings-v5-omni-small'
TASKS=['retrieval','clustering','classification','text-matching']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

class SmallText:
    def __init__(self,root):
        self.root=root;self.sessions=[];self.loaded=[];self.adapters={};self.calls=[]
        self.tokenizer=Tokenizer.from_file(str(root/'tokenizer.json'))
        self.tokenizer.no_truncation();self.tokenizer.no_padding()
        assert self.tokenizer.token_to_id('<|im_end|>')==151645
        self.embedding=np.memmap(root/'model.embed_tokens.weight.bfloat16.bin',dtype=BF,mode='r',shape=(151672,1024))
        for task in TASKS:
            directory=root/'lora'/task;m=json.loads((directory/'manifest.json').read_text())
            assert m['adapter_id']==task and m['num_layers']==28 and m['rank']==32
            assert m['packed_dtype']=='BF16' and m['scale_folded_into_b'] and len(m['tensor_order'])==14
            assert m['scale']==1.0
            self.adapters[task]=[]
            for i in range(28):
                name=f'layer_{i:02d}.bf16.bin';p=directory/name;spec=m['files'][name]
                assert p.stat().st_size==spec['size'] and sha(p)==spec['sha256']
                packed=np.fromfile(p,dtype=BF);offset=0;feed={}
                for tensor in m['tensor_order']:
                    module,side=tensor.rsplit('_',1);shape=m['ab_shapes'][module][0 if side=='A' else 1]
                    count=int(np.prod(shape));feed['lora_'+module+'_'+side.lower()]=packed[offset:offset+count].reshape(shape);offset+=count
                assert offset==packed.size and len(feed)==14
                self.adapters[task].append(feed)
        for i in range(28):
            name=f'jina_embeddings_v5_omni_p256_l{i}_together.axmodel';s=self.load(name)
            nodes={n.name:(list(n.shape),str(n.dtype)) for n in s.get_inputs(1)}
            assert nodes['input']==([1,256,1024],'bfloat16') and nodes['mask']==([1,256,256],'bfloat16')
            assert nodes['K_cache']==nodes['V_cache']==([1,1,1024],'bfloat16')
            assert nodes['indices']==([1,256],'uint32')
            assert set(nodes)=={'input','mask','indices','K_cache','V_cache'}|set(self.adapters['retrieval'][i])
            for task in TASKS:
                for key,value in self.adapters[task][i].items():assert nodes[key]==(list(value.shape),'bfloat16')
            self.sessions.append(s)
        self.post=self.load('jina_embeddings_v5_omni_post.axmodel')
        outputs={n.name:list(n.shape) for n in self.post.get_outputs()}
        assert outputs['output_norm']==[1,1,1024]

    def load(self,name):
        s=axengine.InferenceSession(str(self.root/name),providers=['AXCLNativeAPI'])
        assert s.get_providers()=='AXCLNativeAPI'
        self.loaded.append({'path':name,'providerActual':s.get_providers()});return s

    def encode(self,text,task,role,prepared_prompt=None,features=None,placeholder=151655):
        assert task in TASKS and role in ['query','document']
        started=time.monotonic()
        # Every native call owns a fresh model and buffers.
        for session in self.sessions+[self.post]:session._sess._unload()
        self.loaded=[]
        self.sessions=[self.load(f'jina_embeddings_v5_omni_p256_l{i}_together.axmodel') for i in range(28)]
        self.post=self.load('jina_embeddings_v5_omni_post.axmodel')
        prompt=prepared_prompt if prepared_prompt is not None else ('Query: ' if role=='query' else 'Document: ')+text
        ids=self.tokenizer.encode(prompt,add_special_tokens=True).ids
        # Official Small config: embedding_append_eos=false; ByteLevel adds no EOS.
        assert 0<len(ids)<=256 and all(0<=i<151672 for i in ids)
        hidden=np.zeros((1,256,1024),dtype=BF);hidden[0,:len(ids)]=self.embedding[ids]
        if features is not None:
            positions=[i for i,t in enumerate(ids) if t==placeholder]
            assert features.ndim==3 and features.shape[0]==1 and features.shape[2]==1024 and len(positions)==features.shape[1] and np.isfinite(features).all()
            hidden[0,positions]=features[0].astype(BF)
        mask=np.full((1,256,256),-65536,dtype=BF);mask[0,:len(ids),:len(ids)]=0
        layer_times=[]
        for i,s in enumerate(self.sessions):
            feed={'K_cache':np.zeros((1,1,1024),dtype=BF),'V_cache':np.zeros((1,1,1024),dtype=BF),
                  'indices':np.arange(256,dtype=np.uint32).reshape(1,256),'input':hidden,'mask':mask,**self.adapters[task][i]}
            start=time.monotonic();values=s.run(None,feed,shape_group=1)
            outputs=dict(zip([n.name for n in s.get_outputs(1)],values));hidden=np.ascontiguousarray(outputs['output'])
            assert list(hidden.shape)==[1,256,1024] and np.isfinite(hidden[0,:len(ids)].astype(np.float32)).all()
            layer_times.append(time.monotonic()-start)
        values=self.post.run(None,{'input':np.ascontiguousarray(hidden[:,len(ids)-1:len(ids),:])})
        outputs=dict(zip([n.name for n in self.post.get_outputs()],values))
        raw=outputs['output_norm'].reshape(1024).astype(np.float32)
        assert np.isfinite(raw).all();norm=float(np.linalg.norm(raw));assert norm>1e-8
        embedding=raw/norm
        result={'text':text,'task':task,'inputType':role,'prompt':prompt,'tokenIds':ids,'tokenCount':len(ids),
                'rawNorm':norm,'normalizedNorm':float(np.linalg.norm(embedding)),'embedding':embedding.tolist(),
                'embeddingSha256':hashlib.sha256(embedding.tobytes()).hexdigest(),'seconds':time.monotonic()-started,
                'loadedModels':list(self.loaded),'featureTokens':0 if features is None else features.shape[1],'freshModelsPerRequest':True,'layerSeconds':layer_times,'postOutput':'output_norm','shapeGroup':1}
        self.calls.append(result);return embedding
