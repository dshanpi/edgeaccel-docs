#!/usr/bin/env python3
"""Port fixed AXERA Lightweight-Speech-Denoising C runtime to host AXCL.

Apply to official Git commit ede9b239cf6b347dbc26a3ce70b574937f4c5771.
Original DSP, tensor packing, recurrent cache updates and audio alignment stay
unchanged. The explicit host backend checks FP32 buffers and hashes all I/O.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

COMMIT = 'ede9b239cf6b347dbc26a3ce70b574937f4c5771'
TYPES = r'''
#include <axcl.h>
#include <stdint.h>
#include <time.h>
#include <openssl/evp.h>
typedef struct { AX_U32 nSize; const char *pName; void *pVirAddr, *device; } ClBuffer;
typedef struct { AX_U32 nInputSize, nOutputSize; ClBuffer *pInputs, *pOutputs; } ClHostIO;
'''
FIELDS = r'''
    uint64_t model_id, context_id;
    axclrtEngineIOInfo cl_info;
    axclrtEngineIO cl_io;
    ClHostIO io;
    ClHostIO *io_info;
    int initialized, engine_initialized, loaded;
    EVP_MD_CTX *digest;
    unsigned calls;
    struct timespec run_start;
'''
BACKEND = r'''
static AX_VOID ax_engine_free(AxEngine *eng);
static AX_VOID ax_engine_release_buffers(AxEngine *eng) {
    for (int side = 0; side < 2; ++side) {
        unsigned count = side ? eng->io.nOutputSize : eng->io.nInputSize;
        ClBuffer *bufs = side ? eng->io.pOutputs : eng->io.pInputs;
        if (bufs) for (unsigned i = 0; i < count; ++i) {
            free(bufs[i].pVirAddr);
            if (bufs[i].device) axclrtFree(bufs[i].device);
        }
        free(bufs);
    }
    eng->io.pInputs = eng->io.pOutputs = NULL;
    if (eng->digest) {
        unsigned char out[EVP_MAX_MD_SIZE]; unsigned n = 0;
        if (!EVP_DigestFinal_ex(eng->digest, out, &n) || n != 32) abort();
        printf("CL_TRACE %u ", eng->calls);
        for (unsigned i = 0; i < n; ++i) printf("%02x", out[i]);
        printf("\n");
        EVP_MD_CTX_free(eng->digest); eng->digest = NULL;
    }
    if (eng->cl_io) axclrtEngineDestroyIO(eng->cl_io);
    if (eng->cl_info) axclrtEngineDestroyIOInfo(eng->cl_info);
    if (eng->loaded) axclrtEngineUnload(eng->model_id);
    if (eng->engine_initialized) axclrtEngineFinalize();
    if (eng->initialized) axclFinalize();
    eng->cl_io = NULL; eng->cl_info = NULL;
    eng->loaded = eng->engine_initialized = eng->initialized = 0;
}
static int cl_check_hash(AxEngine *eng, ClBuffer *buf) {
    const float *p = (const float*)buf->pVirAddr;
    for (unsigned i = 0; i < buf->nSize / sizeof(float); ++i)
        if (!isfinite(p[i])) { fprintf(stderr, "Nonfinite tensor %s\n", buf->pName); return -1; }
    return EVP_DigestUpdate(eng->digest, p, buf->nSize) ? 0 : -1;
}
static AX_S32 ax_engine_flush_inputs(AxEngine *eng) {
    clock_gettime(CLOCK_MONOTONIC, &eng->run_start);
    for (unsigned i = 0; i < eng->io.nInputSize; ++i) {
        ClBuffer *b = &eng->io.pInputs[i];
        if (cl_check_hash(eng, b) || axclrtMemcpy(b->device, b->pVirAddr, b->nSize, AXCL_MEMCPY_HOST_TO_DEVICE)) return -1;
    }
    return 0;
}
static AX_S32 ax_engine_execute(AxEngine *eng) {
    return axclrtEngineExecute(eng->model_id, eng->context_id, 0, eng->cl_io);
}
static AX_S32 ax_engine_invalidate_outputs(AxEngine *eng) {
    for (unsigned i = 0; i < eng->io.nOutputSize; ++i) {
        ClBuffer *b = &eng->io.pOutputs[i];
        if (axclrtMemcpy(b->pVirAddr, b->device, b->nSize, AXCL_MEMCPY_DEVICE_TO_HOST) || cl_check_hash(eng, b)) return -1;
    }
    struct timespec end; clock_gettime(CLOCK_MONOTONIC, &end);
    double ms = (end.tv_sec - eng->run_start.tv_sec) * 1000.0 + (end.tv_nsec - eng->run_start.tv_nsec) / 1e6;
    printf("CL_RUN %u %.9f\n", ++eng->calls, ms);
    return 0;
}
#define CL_TRY(expr) do { int rc = (expr); if (rc) { fprintf(stderr, "%s failed %d\n", #expr, rc); goto err; } } while (0)
static AX_S32 ax_engine_init(AxEngine *eng, const AX_CHAR *model_path,
                             AX_S32 t_model, AX_S32 f_freqs, AX_S32 step, AX_S32 model_type) {
    AX_U32 i;
    memset(eng, 0, sizeof(*eng));
    CL_TRY(axclInit(NULL)); eng->initialized = 1;
    axclrtDeviceList devices = {0}; CL_TRY(axclrtGetDeviceList(&devices));
    if (!devices.num) goto err;
    CL_TRY(axclrtSetDevice(devices.devices[0]));
    CL_TRY(axclrtEngineInit(AXCL_VNPU_DISABLE)); eng->engine_initialized = 1;
    CL_TRY(axclrtEngineLoadFromFile(model_path, &eng->model_id)); eng->loaded = 1;
    CL_TRY(axclrtEngineCreateContext(eng->model_id, &eng->context_id));
    CL_TRY(axclrtEngineGetIOInfo(eng->model_id, &eng->cl_info));
    CL_TRY(axclrtEngineCreateIO(eng->cl_info, &eng->cl_io));
    eng->io.nInputSize = axclrtEngineGetNumInputs(eng->cl_info);
    eng->io.nOutputSize = axclrtEngineGetNumOutputs(eng->cl_info);
    if (!eng->io.nInputSize || eng->io.nInputSize > 16 || !eng->io.nOutputSize || eng->io.nOutputSize > 16) goto err;
    eng->io_info = &eng->io;
    eng->input_count = eng->io.nInputSize; eng->output_count = eng->io.nOutputSize;
    eng->model_type = model_type;
    eng->digest = EVP_MD_CTX_new();
    if (!eng->digest || !EVP_DigestInit_ex(eng->digest, EVP_sha256(), NULL)) goto err;
    for (int side = 0; side < 2; ++side) {
        unsigned count = side ? eng->io.nOutputSize : eng->io.nInputSize;
        ClBuffer *bufs = calloc(count, sizeof(ClBuffer));
        if (!bufs) goto err;
        if (side) eng->io.pOutputs = bufs; else eng->io.pInputs = bufs;
        for (unsigned j = 0; j < count; ++j) {
            ClBuffer *b = &bufs[j]; axclrtEngineDataType dtype;
            uint64_t bytes = side ? axclrtEngineGetOutputSizeByIndex(eng->cl_info, 0, j) : axclrtEngineGetInputSizeByIndex(eng->cl_info, 0, j);
            CL_TRY(side ? axclrtEngineGetOutputDataType(eng->cl_info, j, &dtype) : axclrtEngineGetInputDataType(eng->cl_info, j, &dtype));
            if (!bytes || bytes > 32*1024*1024 || bytes % sizeof(float) || dtype != AXCL_DATA_TYPE_FP32) goto err;
            b->nSize = (AX_U32)bytes;
            b->pName = side ? axclrtEngineGetOutputNameByIndex(eng->cl_info, j) : axclrtEngineGetInputNameByIndex(eng->cl_info, j);
            if (!b->pName) goto err;
            b->pVirAddr = calloc(1, b->nSize); if (!b->pVirAddr) goto err;
            CL_TRY(axclrtMalloc(&b->device, bytes, AXCL_MEM_MALLOC_NORMAL_ONLY));
            CL_TRY(side ? axclrtEngineSetOutputBufferByIndex(eng->cl_io, j, b->device, bytes) : axclrtEngineSetInputBufferByIndex(eng->cl_io, j, b->device, bytes));
        }
    }
    /* HF package uses context/mask models; upstream also implements self-cache. */
    if (model_type != SE_MODEL_TYPE_MASK_BATCH && model_type != SE_MODEL_TYPE_SELF_CACHE && model_type != SE_MODEL_TYPE_GTCRN_STREAM) goto err;
    if (model_type == SE_MODEL_TYPE_MASK_BATCH) {
        unsigned compressed = t_model == 34 ? 17 : t_model == 64 ? 129 : 0;
        if (!compressed || eng->input_count != 1 || eng->output_count != 1 ||
            eng->io.pInputs[0].nSize != (size_t)t_model*f_freqs*sizeof(float) ||
            eng->io.pOutputs[0].nSize != (size_t)t_model*compressed*sizeof(float)) goto err;
    }
    if (model_type == SE_MODEL_TYPE_GTCRN_STREAM) {
        const size_t sizes[] = { (size_t)step*f_freqs*2, GTCRN_EN_CONV_CACHE_ELEMS, GTCRN_DE_CONV_CACHE_ELEMS,
            GTCRN_EN_TRA_CACHE_ELEMS, GTCRN_DE_TRA_CACHE_ELEMS, GTCRN_INTER_CACHE_0_ELEMS, GTCRN_INTER_CACHE_1_ELEMS };
        if (eng->input_count != 7 || eng->output_count != 7) goto err;
        for (i = 0; i < 7; ++i) if (eng->io.pInputs[i].nSize != sizes[i]*sizeof(float) || eng->io.pOutputs[i].nSize != sizes[i]*sizeof(float)) goto err;
    }
'''

CMAKE = '''cmake_minimum_required(VERSION 3.16)
project(lightweight_axcl C)
set(CMAKE_C_STANDARD 99)
find_path(AXCL_INCLUDE axcl.h PATHS /usr/include/axcl REQUIRED)
find_library(AXCL_RT axcl_rt PATHS /usr/lib/axcl REQUIRED)
find_package(OpenSSL REQUIRED)
add_library(se_unified STATIC lib/rnnoise_src/kiss_fft.c lib/rnnoise_src/rnnoise_tables.c
 lib/rnnoise_src/celt_lpc.c lib/rnnoise_src/pitch.c lib/tiny_se_v5_dsp.c src/ax_ai_se_denoise_ax.c)
target_include_directories(se_unified PUBLIC inc lib lib/rnnoise_src ${AXCL_INCLUDE})
target_compile_options(se_unified PRIVATE -O3 -Wall -Wextra)
target_link_libraries(se_unified PUBLIC ${AXCL_RT} OpenSSL::Crypto m)
add_executable(test_se_denoise_axcl src/test_se_denoise_ax.c)
target_link_libraries(test_se_denoise_axcl PRIVATE se_unified)
'''

def main():
    p = argparse.ArgumentParser(); p.add_argument('source', type=Path); a = p.parse_args()
    rev = subprocess.check_output(['git','-C',str(a.source),'rev-parse','HEAD'],text=True).strip()
    assert rev == COMMIT, 'Use the documented fixed source commit'
    root = a.source/'c_infer'; c = root/'src/ax_ai_se_denoise_ax.c'; test = root/'src/test_se_denoise_ax.c'
    paths = [c, test, root/'CMakeLists.txt'] + list((root/'lib').rglob('*.[ch]')) + list((root/'inc').glob('*.h'))
    original = {f.relative_to(a.source).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in paths}
    assert not subprocess.check_output(['git','-C',str(a.source),'diff','--name-only'],text=True).strip(), 'Use a clean checkout'
    s = c.read_text('utf-8')
    s = s.replace('#include "ax_sys_api.h"\n#include "ax_engine_api.h"\n#include "ax_engine_type.h"', TYPES)
    start=s.index('    AX_ENGINE_HANDLE     handle;');end=s.index('    AX_S32 model_type;',start)
    s=s[:start]+FIELDS+'\n'+s[end:]
    start=s.index('static AX_VOID ax_engine_release_buffers(')
    end=s.index('    if (model_type == SE_MODEL_TYPE_GTCRN_SPLIT)',start)
    s=s[:start]+BACKEND+'\n'+s[end:]
    old='''    ax_engine_release_buffers(eng);
    if (eng->handle) AX_ENGINE_DestroyHandle(eng->handle);
    AX_ENGINE_Deinit();
    AX_SYS_Deinit();'''
    assert old in s;s=s.replace(old,'    ax_engine_free(eng);',1)
    old='''    ax_engine_release_buffers(eng);
    if (eng->handle) {
        AX_ENGINE_DestroyHandle(eng->handle);
        eng->handle = AX_NULL;
    }
    AX_ENGINE_Deinit();
    AX_SYS_Deinit();'''
    assert old in s;s=s.replace(old,'    ax_engine_release_buffers(eng);')
    assert s.count('AX_ENGINE_RunSync(eng->handle, &eng->io)')==4
    s=s.replace('AX_ENGINE_RunSync(eng->handle, &eng->io)','ax_engine_execute(eng)')
    assert 'AX_SYS_' not in s and 'AX_ENGINE_' not in s
    c.write_text(s,encoding='utf-8')
    s=test.read_text('utf-8').replace('#include <time.h>','#include <time.h>\n#include <math.h>')
    marker='    AX_VOID *handle = AX_NULL;'
    assert marker in s
    s=s.replace(marker,'''    if (cfg.hop_len != 256 || cfg.f_freqs != 257 ||
        !((cfg.model_type == 0 && cfg.step == 6 && ((cfg.t_model == 34 && cfg.f_int == 17) || (cfg.t_model == 64 && cfg.f_int == 129))) ||
          (cfg.model_type == 1 && cfg.step == 1 && cfg.t_model == 1 && cfg.f_int == 257))) {
        fprintf(stderr, "Unsupported configuration for this integration\\n"); return -1;
    }
'''+marker)
    marker='    const AX_S32 hop_len = cfg.hop_len;'
    assert marker in s;s=s.replace(marker,'    if (sample_rate != 16000 || cfg.step <= 0 || cfg.hop_len != 256 || num_samples < 2*cfg.step*cfg.hop_len) { free(input_signal); AX_AI_SE_Free(handle); return -1; }\n'+marker)
    marker='    if (write_wav_file(output_wav, output_signal + out_offset, out_samples, sample_rate) != 0) {'
    assert marker in s
    s=s.replace(marker, r'''    for (int i = 0; i < n_frames_aligned * hop_len; ++i) if (!isfinite(output_signal[i])) {
        fprintf(stderr, "Nonfinite PCM\n"); free(output_signal); free(input_signal); AX_AI_SE_Free(handle); return -1;
    }
    const char *raw_path = getenv("SE_RAW_OUTPUT");
    if (raw_path && *raw_path) {
        FILE *raw = fopen(raw_path, "wb");
        if (!raw || fwrite(output_signal + out_offset, sizeof(float), out_samples, raw) != (size_t)out_samples) abort();
        if (fclose(raw)) abort();
    }
    printf("SE_STATS {\"samplesIn\":%d,\"samplesOut\":%d,\"hop\":%d,\"step\":%d,\"calls\":%d,\"pipelineMilliseconds\":%.9f,\"inferMilliseconds\":%.9f}\n",
        num_samples, out_samples, hop_len, step, infer_count, total_ms, total_infer_ms);
'''+marker)
    test.write_text(s,encoding='utf-8');(root/'CMakeLists.txt').write_text(CMAKE,encoding='utf-8')
    after={f.relative_to(a.source).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in paths}
    unchanged=[k for k in original if k not in ['c_infer/src/ax_ai_se_denoise_ax.c','c_infer/src/test_se_denoise_ax.c','c_infer/CMakeLists.txt']]
    assert all(original[k]==after[k] for k in unchanged)
    (a.source/'axcl-port-manifest.json').write_text(json.dumps({'commit':rev,'before':original,'after':after,'unchangedDspAndHeaders':unchanged},indent=2)+'\n')
    print('AXCL host backend applied; C DSP and cache packing preserved.')

if __name__ == '__main__': main()
