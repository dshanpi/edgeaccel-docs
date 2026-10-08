"""Text retrieval with full Qwen3-Embedding-0.6B Int8 on an AXCL M.2 card.

Profile: AX650, 28 decoder layers, prefill512, step128, BF16 state, ret_postnorm.
"""
from pathlib import Path
import argparse, gc, json, time
import axengine
import numpy as np
from ml_dtypes import bfloat16
from tokenizers import Tokenizer


class Qwen3Embedding:
    max_tokens = 512
    dimensions = 1024

    def __init__(self, model_dir):
        self.root = Path(model_dir)
        self.sessions = []
        self.post = None
        self.tokenizer = Tokenizer.from_file(str(self.root / 'tokenizer.json'))
        self.embedding = self.root / 'model.embed_tokens.weight.bfloat16.bin'
        if self.embedding.stat().st_size != 151669 * 1024 * 2:
            raise ValueError('The original BF16 embedding table must have shape [151669,1024].')
        begin = time.perf_counter()
        try:
            for layer in range(28):
                session = axengine.InferenceSession(str(self.root / f'qwen3_p128_l{layer}_together.axmodel'),
                                                   providers=['AXCLRTExecutionProvider'])
                self.sessions.append(session)
                if session.get_providers() != 'AXCLRTExecutionProvider':
                    raise RuntimeError('AXCLRTExecutionProvider is required.')
                if session._sess._shape_count != 5:
                    raise ValueError('Expected one decode group and four 128-token prefill groups.')
                for group in range(1, 5):
                    offset = (group - 1) * 128
                    shapes = {'input': [1,128,1024], 'indices': [1,128], 'mask': [1,128,offset+128],
                              'K_cache': [1,max(1,offset),1024], 'V_cache': [1,max(1,offset),1024]}
                    inputs = session.get_inputs(group)
                    if {n.name for n in inputs} != set(shapes):
                        raise ValueError(f'Unexpected input names in layer{layer}, group{group}.')
                    for node in inputs:
                        dtype = 'uint32' if node.name == 'indices' else 'bfloat16'
                        if list(node.shape) != shapes[node.name] or str(node.dtype) != dtype:
                            raise ValueError(f'Unexpected shape/dtype: layer{layer}, {node.name}.')
                    outputs = session.get_outputs(group)
                    if [n.name for n in outputs] != ['K_cache_out','V_cache_out','output']:
                        raise ValueError('Unexpected decoder output order.')
                    if any(list(n.shape) != [1,128,1024] or str(n.dtype) != 'bfloat16' for n in outputs):
                        raise ValueError('Unexpected decoder output shape/dtype.')
            self.post = axengine.InferenceSession(str(self.root / 'qwen3_post.axmodel'),
                                                 providers=['AXCLRTExecutionProvider'])
            if self.post.get_providers() != 'AXCLRTExecutionProvider':
                raise RuntimeError('AXCLRTExecutionProvider is required for post normalization.')
            inputs = self.post.get_inputs()
            if len(inputs) != 1 or inputs[0].name != 'input' or list(inputs[0].shape) != [1,1,1024] or str(inputs[0].dtype) != 'bfloat16':
                raise ValueError('Unexpected final RMSNorm input.')
            outputs = self.post.get_outputs()
            matches = [i for i,n in enumerate(outputs) if n.name == 'output_norm' and list(n.shape) == [1,1,1024]]
            if len(matches) != 1:
                raise ValueError('The post model must be built with --ret_postnorm and expose output_norm.')
            self.norm_output = matches[0]
            self.k = [np.zeros((1,512,1024),dtype=bfloat16) for _ in self.sessions]
            self.v = [np.zeros((1,512,1024),dtype=bfloat16) for _ in self.sessions]
            self.empty = np.zeros((1,1,1024),dtype=bfloat16)
            self.load_seconds = time.perf_counter() - begin
        except BaseException:
            self.close()
            raise

    def close(self):
        self.post = None
        self.sessions.clear()
        self.k = []
        self.v = []
        gc.collect()

    def encode(self, text):
        return self.encode_tokens(self.tokenizer.encode(text, add_special_tokens=True).ids)

    def encode_tokens(self, ids):
        if not 1 <= len(ids) <= self.max_tokens:
            raise ValueError(f'Text has {len(ids)} tokens; this profile accepts1..{self.max_tokens}. Split longer documents first.')
        if any(not isinstance(t,int) or not 0 <= t < 151669 for t in ids):
            raise ValueError('Token ID is outside the original vocabulary.')
        begin = time.perf_counter()
        for cache in self.k + self.v:
            cache.fill(0)
        embeddings = np.empty((len(ids),1024),dtype=bfloat16)
        with self.embedding.open('rb') as f:
            for i,token in enumerate(ids):
                f.seek(token * 2048)
                raw = f.read(2048)
                if len(raw) != 2048:
                    raise IOError('Incomplete BF16 embedding-table read.')
                embeddings[i] = np.frombuffer(raw,dtype=bfloat16)
        executions = 0
        for offset in range(0,len(ids),128):
            valid = min(128,len(ids)-offset)
            data = np.zeros((1,128,1024),dtype=bfloat16)
            data[0,:valid] = embeddings[offset:offset+valid]
            indices = np.arange(offset,offset+128,dtype=np.uint32).reshape(1,128)
            mask = np.full((1,128,offset+128),-65536,dtype=bfloat16)
            for row in range(valid):
                mask[0,row,:offset+row+1] = 0
            for layer,session in enumerate(self.sessions):
                feed = dict(input=data,indices=indices,mask=mask,
                            K_cache=np.ascontiguousarray(self.k[layer][:,:offset]) if offset else self.empty,
                            V_cache=np.ascontiguousarray(self.v[layer][:,:offset]) if offset else self.empty)
                # Request all outputs to support PyAXEngine0.1.3 output mapping.
                values = session.run(None,feed,shape_group=offset//128+1)
                if len(values) != 3 or not all(np.isfinite(v).all() for v in values):
                    raise RuntimeError(f'Invalid output in layer{layer}, block{offset//128}.')
                self.k[layer][:,offset:offset+valid] = values[0][:,:valid]
                self.v[layer][:,offset:offset+valid] = values[1][:,:valid]
                data = values[2]
                executions += 1
        last = np.ascontiguousarray(data[:,valid-1:valid])
        outputs = self.post.run(None,{'input':last})
        value = outputs[self.norm_output].astype(np.float32).reshape(1024).copy()
        norm = float(np.linalg.norm(value))
        if not np.isfinite(value).all() or not np.isfinite(norm) or norm <= 0:
            raise RuntimeError('Invalid normalized hidden state.')
        vector = value / norm
        return vector,dict(tokens=len(ids),seconds=time.perf_counter()-begin,chunks=(len(ids)+127)//128,
                           decoderExecutions=executions,postExecutions=1,preL2Norm=norm)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir',type=Path,required=True)
    parser.add_argument('--input-json',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args = parser.parse_args()
    payload = json.loads(args.input_json.read_text('utf-8'))
    if 'texts' in payload:
        if 'queries' in payload or 'documents' in payload:
            raise ValueError('Use texts or queries/documents, not both.')
        texts = payload['texts']
        query_count = 0
    else:
        queries,documents = payload['queries'],payload['documents']
        if not queries or not documents:
            raise ValueError('Provide at least one query and one document.')
        instruction = payload.get('instruction','Given a web search query, retrieve relevant passages that answer the query')
        texts = [f'Instruct: {instruction}\nQuery:{query}' for query in queries] + documents
        query_count = len(queries)
    if not isinstance(texts,list) or not texts or not all(isinstance(t,str) and t for t in texts):
        raise ValueError('Provide a nonempty list of nonempty strings.')
    args.output_dir.mkdir(parents=True,exist_ok=False)
    engine = Qwen3Embedding(args.model_dir)
    try:
        vectors,statistics = [],[]
        for text in texts:
            vector,stats = engine.encode(text)
            vectors.append(vector)
            statistics.append(stats)
        vectors = np.stack(vectors)
        result = dict(provider='AXCLRTExecutionProvider',dimensions=1024,batch=1,maxTokens=512,
                      loadSeconds=engine.load_seconds,texts=texts,samples=statistics,
                      embeddingsFile='embeddings.npy',normalized=True)
        if query_count:
            scores = vectors[:query_count] @ vectors[query_count:].T
            result.update(queries=queries,documents=documents,similarities=scores.tolist(),
                          matches=[dict(query=queries[i],document=documents[int(np.argmax(row))],
                                        documentIndex=int(np.argmax(row)),score=float(np.max(row)))
                                   for i,row in enumerate(scores)])
        np.save(args.output_dir/'embeddings.npy',vectors)
        (args.output_dir/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    finally:
        engine.close()


if __name__ == '__main__':
    main()
