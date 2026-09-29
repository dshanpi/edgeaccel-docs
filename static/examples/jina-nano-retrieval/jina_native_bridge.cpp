// Minimal serial AXCL Native API bridge. Each call owns and releases one model.
// No driver/runtime changes; built against the installed AXCL headers and libraries.
#include <axcl.h>
#include <axcl_native.h>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
static bool initialized=false;
static std::string error_message;
static void check(int rc,const char* where){if(rc)throw std::runtime_error(std::string(where)+" returned "+std::to_string(rc));}
using Clock=std::chrono::steady_clock;
static double ms(Clock::time_point t){return std::chrono::duration<double,std::milli>(Clock::now()-t).count();}
struct Memory {void* p=nullptr;explicit Memory(uint64_t bytes){check(axclrtMalloc(&p,bytes,axclrtMemMallocPolicy{}),"axclrtMalloc");}~Memory(){if(p)axclrtFree(p);}Memory(const Memory&)=delete;};
struct Model {AX_ENGINE_HANDLE handle{};~Model(){if(handle)AXCL_ENGINE_DestroyHandle(handle);}Model()=default;Model(const Model&)=delete;};
extern "C" const char* jina_native_error(){return error_message.c_str();}
extern "C" int jina_native_init(){
 try {
  if(initialized)return 0;
  check(axclInit(nullptr),"axclInit");
  try {axclrtDeviceList devices{};check(axclrtGetDeviceList(&devices),"axclrtGetDeviceList");if(!devices.num)throw std::runtime_error("No AXCL device");check(axclrtSetDevice(devices.devices[0]),"axclrtSetDevice");AX_ENGINE_NPU_ATTR_T attr{};attr.eHardMode=static_cast<AX_ENGINE_NPU_MODE_T>(0);check(AXCL_ENGINE_Init(&attr),"AXCL_ENGINE_Init");initialized=true;return 0;}
  catch(...){axclFinalize();throw;}
 }catch(const std::exception& e){error_message=e.what();return -1;}
}
extern "C" void jina_native_final(){if(initialized){AXCL_ENGINE_Deinit();axclFinalize();initialized=false;}}
extern "C" int jina_native_run(const char* path,uint32_t group,uint32_t ni,const char** in_names,const void** in_data,const uint64_t* in_sizes,uint32_t no,const char** out_names,void** out_data,const uint64_t* out_sizes,double* kernel_ms,double* load_ms){
 try {
  if(!initialized)throw std::runtime_error("Native engine not initialized");
  auto start=Clock::now();
  std::ifstream file(path,std::ios::binary|std::ios::ate);if(!file)throw std::runtime_error("Cannot open model");auto end=file.tellg();if(end<=0||uint64_t(end)>std::numeric_limits<uint32_t>::max())throw std::runtime_error("Invalid model size");
  std::vector<char> bytes(static_cast<size_t>(end));file.seekg(0);if(!file.read(bytes.data(),bytes.size()))throw std::runtime_error("Incomplete model read");
  Memory model_data(bytes.size());check(axclrtMemcpy(model_data.p,bytes.data(),bytes.size(),AXCL_MEMCPY_HOST_TO_DEVICE),"model H2D");
  Model model;AX_ENGINE_HANDLE_EXTRA_T extra{};check(AXCL_ENGINE_CreateHandleV2(&model.handle,model_data.p,static_cast<AX_U32>(bytes.size()),&extra),"CreateHandleV2");
  AX_ENGINE_CONTEXT_T context{};check(AXCL_ENGINE_CreateContextV2(model.handle,&context),"CreateContextV2");
  AX_U32 groups=0;check(AXCL_ENGINE_GetGroupIOInfoCount(model.handle,&groups),"GetGroupIOInfoCount");if(group>=groups)throw std::runtime_error("Invalid shape group");
  AX_ENGINE_IO_INFO_T* info=nullptr;check(groups==1?AXCL_ENGINE_GetIOInfo(model.handle,&info):AXCL_ENGINE_GetGroupIOInfo(model.handle,group,&info),"GetIOInfo");
  if(info->nInputSize!=ni||info->nOutputSize!=no)throw std::runtime_error("IO count differs from metadata");
  *load_ms=ms(start);
  AX_ENGINE_IO_T io{};std::vector<AX_ENGINE_IO_BUFFER_T> inputs(ni),outputs(no);std::vector<std::unique_ptr<Memory>> memory;std::vector<size_t> output_map;
  io.nInputSize=ni;io.pInputs=inputs.data();io.nOutputSize=no;io.pOutputs=outputs.data();io.nBatchSize=1;io.nParallelRun=0;
  auto locate=[](const char* name,uint32_t n,const char** names){for(uint32_t i=0;i<n;++i)if(std::string(name)==names[i])return i;throw std::runtime_error(std::string("Missing tensor ")+name);};
  for(uint32_t i=0;i<ni;++i){auto& meta=info->pInputs[i];auto j=locate(reinterpret_cast<const char*>(meta.pName),ni,in_names);if(meta.nSize!=in_sizes[j])throw std::runtime_error("Input byte size mismatch");auto mem=std::make_unique<Memory>(meta.nSize);inputs[i].phyAddr=reinterpret_cast<uint64_t>(mem->p);inputs[i].nSize=meta.nSize;check(axclrtMemcpy(mem->p,in_data[j],meta.nSize,AXCL_MEMCPY_HOST_TO_DEVICE),"input H2D");memory.push_back(std::move(mem));}
  for(uint32_t i=0;i<no;++i){auto& meta=info->pOutputs[i];auto j=locate(reinterpret_cast<const char*>(meta.pName),no,out_names);if(meta.nSize!=out_sizes[j])throw std::runtime_error("Output byte size mismatch");auto mem=std::make_unique<Memory>(meta.nSize);outputs[i].phyAddr=reinterpret_cast<uint64_t>(mem->p);outputs[i].nSize=meta.nSize;check(axclrtMemset(mem->p,0,meta.nSize),"output memset");memory.push_back(std::move(mem));output_map.push_back(j);}
  start=Clock::now();check(groups==1?AXCL_ENGINE_RunSyncV2(model.handle,context,&io):AXCL_ENGINE_RunGroupIOSync(model.handle,context,group,&io),"native model run");*kernel_ms=ms(start);
  for(uint32_t i=0;i<no;++i)check(axclrtMemcpy(out_data[output_map[i]],reinterpret_cast<void*>(outputs[i].phyAddr),outputs[i].nSize,AXCL_MEMCPY_DEVICE_TO_HOST),"output D2H");
  return 0;
 }catch(const std::exception& e){error_message=e.what();return -1;}
}
