#!/usr/bin/env python3
"""Adapt AXERA-TECH/ten-vad.axera 666ae7ce to the host AXCL runtime.

Run against a clean checkout. Original DSP and license files are preserved.
This file is a board integration example, not an upstream release.
"""
import argparse
from pathlib import Path

BACKEND = r'''
// AXCL host backend adaptation. Original DSP below is unchanged.
#include <cmath>

#define AXCL_TRY(call) do { auto rc = (call); if (rc != 0) { \
  fprintf(stderr, "%s failed: %d\n", #call, static_cast<int>(rc)); return; } } while (0)

AUP_MODULE_AIVAD::AUP_MODULE_AIVAD(const char* model_path) {
  AXCL_TRY(axclInit(nullptr));
  sys_inited = 1;
  axclrtDeviceList devices = {};
  AXCL_TRY(axclrtGetDeviceList(&devices));
  if (devices.num == 0) { fprintf(stderr, "No AXCL device\n"); return; }
  device_id = devices.devices[0];
  AXCL_TRY(axclrtSetDevice(device_id));
  AXCL_TRY(axclrtEngineInit(AXCL_VNPU_DISABLE));
  engine_inited = 1;
  AXCL_TRY(axclrtEngineLoadFromFile(model_path, &model_id));
  model_loaded = 1;
  AXCL_TRY(axclrtEngineCreateContext(model_id, &context_id));
  AXCL_TRY(axclrtEngineGetIOInfo(model_id, &io_info));
  if (axclrtEngineGetNumInputs(io_info) != 5 ||
      axclrtEngineGetNumOutputs(io_info) != 5) return;
  AXCL_TRY(axclrtEngineCreateIO(io_info, &io));
  const char* ins[] = {"input_1", "input_2", "input_3", "input_6", "input_7"};
  const char* outs[] = {"output_1", "output_2", "output_3", "output_6", "output_7"};
  for (int logical = 0; logical < 5; ++logical) {
    int in = axclrtEngineGetInputIndexByName(io_info, ins[logical]);
    int out = axclrtEngineGetOutputIndexByName(io_info, outs[logical]);
    if (in < 0 || out < 0) return;
    input_sizes[logical] = logical == 0 ? sizeof(input_data_buf_0) : sizeof(input_data_buf_1234[0]);
    output_sizes[logical] = logical == 0 ? sizeof(float) : sizeof(input_data_buf_1234[0]);
    if (axclrtEngineGetInputSizeByIndex(io_info, 0, in) != input_sizes[logical] ||
        axclrtEngineGetOutputSizeByIndex(io_info, 0, out) != output_sizes[logical]) return;
    axclrtEngineDataType it, ot;
    AXCL_TRY(axclrtEngineGetInputDataType(io_info, in, &it));
    AXCL_TRY(axclrtEngineGetOutputDataType(io_info, out, &ot));
    if (it != AXCL_DATA_TYPE_FP32 || ot != AXCL_DATA_TYPE_FP32) return;
    AXCL_TRY(axclrtMalloc(&inputs[logical], input_sizes[logical], AXCL_MEM_MALLOC_NORMAL_ONLY));
    AXCL_TRY(axclrtMalloc(&outputs[logical], output_sizes[logical], AXCL_MEM_MALLOC_NORMAL_ONLY));
    AXCL_TRY(axclrtEngineSetInputBufferByIndex(io, in, inputs[logical], input_sizes[logical]));
    AXCL_TRY(axclrtEngineSetOutputBufferByIndex(io, out, outputs[logical], output_sizes[logical]));
  }
  const char* trace_path = getenv("TEN_VAD_TRACE");
  if (trace_path && *trace_path) {
    trace = fopen(trace_path, "wb");
    if (!trace) return;
  }
  inited = 1;
}
#undef AXCL_TRY

AUP_MODULE_AIVAD::~AUP_MODULE_AIVAD() {
  if (trace) fclose(trace);
  if (io) axclrtEngineDestroyIO(io);
  for (int i = 0; i < 5; ++i) {
    if (inputs[i]) axclrtFree(inputs[i]);
    if (outputs[i]) axclrtFree(outputs[i]);
  }
  if (io_info) axclrtEngineDestroyIOInfo(io_info);
  if (model_loaded) axclrtEngineUnload(model_id);
  if (engine_inited) axclrtEngineFinalize();
  if (sys_inited) axclFinalize();
}

int AUP_MODULE_AIVAD::Process(float* input, float* output) {
  if (!inited) return -1;
  memcpy(input_data_buf_0, input, sizeof(input_data_buf_0));
  if (clear_hidden) {
    memset(input_data_buf_1234, 0, sizeof(input_data_buf_1234));
    clear_hidden = 0;
  }
  const void* data[] = {input_data_buf_0, input_data_buf_1234[0],
    input_data_buf_1234[1], input_data_buf_1234[2], input_data_buf_1234[3]};
  for (int i = 0; i < 5; ++i) {
    const float* values = static_cast<const float*>(data[i]);
    for (size_t j = 0; j < input_sizes[i] / sizeof(float); ++j)
      if (!std::isfinite(values[j])) return -1;
    if (trace && fwrite(data[i], 1, input_sizes[i], trace) != input_sizes[i]) return -1;
    if (axclrtMemcpy(inputs[i], data[i], input_sizes[i], AXCL_MEMCPY_HOST_TO_DEVICE)) return -1;
  }
  if (axclrtEngineExecute(model_id, context_id, 0, io)) return -1;
  void* result[] = {output, input_data_buf_1234[0], input_data_buf_1234[1],
    input_data_buf_1234[2], input_data_buf_1234[3]};
  for (int i = 0; i < 5; ++i) {
    if (axclrtMemcpy(result[i], outputs[i], output_sizes[i], AXCL_MEMCPY_DEVICE_TO_HOST)) return -1;
    const float* values = static_cast<const float*>(result[i]);
    for (size_t j = 0; j < output_sizes[i] / sizeof(float); ++j)
      if (!std::isfinite(values[j])) return -1;
    if (trace && fwrite(result[i], 1, output_sizes[i], trace) != output_sizes[i]) return -1;
  }
  return (*output >= 0.0f && *output <= 1.0f) ? 0 : -1;
}

int AUP_MODULE_AIVAD::Reset() {
  if (!inited) return -1;
  clear_hidden = 1;
  return 0;
}
'''

FIELDS = '''  uint64_t model_id = 0, context_id = 0;
  axclrtEngineIOInfo io_info = nullptr;
  axclrtEngineIO io = nullptr;
  void* inputs[5] = {};
  void* outputs[5] = {};
  size_t input_sizes[5] = {}, output_sizes[5] = {};
  int device_id = 0, model_loaded = 0;
  FILE* trace = nullptr;
'''

CMAKE = '''cmake_minimum_required(VERSION 3.16)
project(ten_vad_axcl LANGUAGES C CXX)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 14)
find_path(AXCL_INCLUDE_DIR axcl.h PATHS /usr/include/axcl REQUIRED)
find_library(AXCL_RT axcl_rt PATHS /usr/lib/axcl REQUIRED)
add_library(ten_vad SHARED src/aed.cc src/biquad.cc src/fftw.c src/fscvrt.cc
  src/pitch_est.cc src/stft.cc src/ten_vad.cc)
target_include_directories(ten_vad PUBLIC include PRIVATE src ${AXCL_INCLUDE_DIR})
target_compile_options(ten_vad PRIVATE -Wall -Wextra -Werror)
target_link_libraries(ten_vad PRIVATE ${AXCL_RT})
set_target_properties(ten_vad PROPERTIES C_VISIBILITY_PRESET hidden
  CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN YES)
add_executable(ten_vad_example examples/example.c)
target_compile_options(ten_vad_example PRIVATE -Wall -Wextra -Werror)
target_link_libraries(ten_vad_example PRIVATE ten_vad)
'''

def main():
    p = argparse.ArgumentParser(); p.add_argument('source', type=Path); a = p.parse_args()
    cc = a.source / 'src/aed.cc'; header = a.source / 'src/aed_st.h'
    text = cc.read_text(encoding='utf-8')
    start = text.index('static int find_tensor(')
    end = text.index('static int AUP_Aed_checkStatCfg(')
    text = text[:start] + BACKEND + '\n' + text[end:]
    # The original init ignores a failed backend initialization. Propagate it.
    marker = '  stHdl->aivadInf->Reset();'
    assert text.count(marker) == 2
    position = text.rfind(marker)
    text = text[:position] + '  if (stHdl->aivadInf->Reset() != 0) return -1;' + text[position+len(marker):]
    cc.write_text(text, encoding='utf-8')
    text = header.read_text(encoding='utf-8').replace('#include <ax_engine_api.h>\n#include <ax_sys_api.h>', '#include <axcl.h>')
    start = text.index('  AX_ENGINE_HANDLE engine_handle')
    end = text.index('  int sys_inited', start)
    header.write_text(text[:start] + FIELDS + text[end:], encoding='utf-8')
    (a.source / 'CMakeLists.txt').write_text(CMAKE, encoding='utf-8')
    # Make upstream demonstration fail fast rather than report success after inference errors.
    example = a.source / 'examples/example.c'
    text = example.read_text(encoding='utf-8')
    marker = '      printf("ten_vad_process failed res %d\\n", res);'
    assert marker in text
    text = text.replace(marker, marker + '\n      ten_vad_destroy(&ten_vad_handle);\n      return -1;')
    example.write_text(text, encoding='utf-8')
    print('Applied AXCL backend; original DSP preserved. Build with cmake -S . -B build-axcl.')

if __name__ == '__main__': main()
