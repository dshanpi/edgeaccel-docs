// AXCL implementation of the official KAN-TTS ModelSession interface.
#include "ax_engine.hpp"
#include <axcl.h>
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <stdexcept>
namespace kantts {
namespace {
void check(axclError e,const char* what){if(e)throw std::runtime_error(std::string(what)+": "+std::to_string(e));}
bool initialized=false;uint64_t sequence=0;
std::string trace_dir(){const char*p=std::getenv("KANTTS_TRACE_DIR");if(!p)throw std::runtime_error("KANTTS_TRACE_DIR missing");std::filesystem::create_directories(p);return p;}
void bytes(const std::string&p,const std::vector<char>&v){std::ofstream f(p,std::ios::binary);f.write(v.data(),v.size());if(!f)throw std::runtime_error("Cannot save tensor "+p);}
std::string dtype(axclrtEngineDataType t){if(t==AXCL_DATA_TYPE_FP32)return "float32";if(t==AXCL_DATA_TYPE_INT32)return "int32";throw std::runtime_error("Unsupported tensor dtype "+std::to_string(t));}
}
void AxRuntimeInit(){
 if(initialized)throw std::runtime_error("Runtime already initialized");check(axclInit(nullptr),"axclInit");
 try{axclrtDeviceList d{};check(axclrtGetDeviceList(&d),"device list");if(d.num!=1)throw std::runtime_error("This example requires exactly one card");check(axclrtSetDevice(d.devices[0]),"device 0");check(axclrtEngineInit(AXCL_VNPU_DISABLE),"engine init");initialized=true;
 std::ofstream f(trace_dir()+"/device.json");f<<"{\"provider\":\"AXCL C API\",\"deviceIndex\":0,\"runtimeDeviceId\":"<<d.devices[0]<<"}";
 }catch(...){axclFinalize();throw;}
}
void AxRuntimeDeinit(){if(initialized){check(axclrtEngineFinalize(),"engine finalize");check(axclFinalize(),"axclFinalize");initialized=false;}}
struct ModelSession::Impl{
 struct Buffer{void* device=nullptr;std::vector<char> host;std::vector<int64_t> dims;std::string name,type;bool set=false;};
 uint64_t model=0,context=0;bool loaded=false;axclrtEngineIOInfo info=nullptr;axclrtEngineIO io=nullptr;std::vector<Buffer> inputs,outputs;std::string name,path;
 void release() noexcept {if(io)axclrtEngineDestroyIO(io);for(auto&b:inputs)if(b.device)axclrtFree(b.device);for(auto&b:outputs)if(b.device)axclrtFree(b.device);if(info)axclrtEngineDestroyIOInfo(info);if(loaded)axclrtEngineUnload(model);}
 explicit Impl(const std::string&p):name(std::filesystem::path(p).stem().string()),path(p){
  if(!initialized)throw std::runtime_error("Runtime not initialized");
  try{check(axclrtEngineLoadFromFile(p.c_str(),&model),"load");loaded=true;check(axclrtEngineCreateContext(model,&context),"context");check(axclrtEngineGetIOInfo(model,&info),"io info");int32_t groups=0;check(axclrtEngineGetShapeGroupsCount(info,&groups),"groups");if(groups!=1)throw std::runtime_error("Expected one shape group");check(axclrtEngineCreateIO(info,&io),"create io");
   inputs.resize(axclrtEngineGetNumInputs(info));outputs.resize(axclrtEngineGetNumOutputs(info));
   for(int side=0;side<2;++side){auto&bs=side?outputs:inputs;for(uint32_t i=0;i<bs.size();++i){auto&b=bs[i];b.name=side?axclrtEngineGetOutputNameByIndex(info,i):axclrtEngineGetInputNameByIndex(info,i);if(b.name.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")!=std::string::npos)throw std::runtime_error("Unsafe tensor name");
    size_t size=side?axclrtEngineGetOutputSizeByIndex(info,0,i):axclrtEngineGetInputSizeByIndex(info,0,i);if(!size||size>256*1024*1024)throw std::runtime_error("Unexpected buffer size");b.host.assign(size,0);axclrtEngineIODims ds{};check(side?axclrtEngineGetOutputDims(info,0,i,&ds):axclrtEngineGetInputDims(info,0,i,&ds),"dims");b.dims.assign(ds.dims,ds.dims+ds.dimCount);axclrtEngineDataType t;check(side?axclrtEngineGetOutputDataType(info,i,&t):axclrtEngineGetInputDataType(info,i,&t),"dtype");b.type=dtype(t);
    size_t logical=4;for(auto dim:b.dims){if(dim<=0)throw std::runtime_error("Dynamic tensor unsupported");logical*=dim;}if(logical!=size)throw std::runtime_error("Unexpected padded tensor size");
    check(axclrtMalloc(&b.device,size,AXCL_MEM_MALLOC_NORMAL_ONLY),"allocate");check(side?axclrtEngineSetOutputBufferByIndex(io,i,b.device,size):axclrtEngineSetInputBufferByIndex(io,i,b.device,size),"set buffer");
   }}
   std::ofstream f(trace_dir()+"/"+name+"-schema.json");f<<"{\"model\":\"model/"<<name<<".axmodel\",\"compiler\":\""<<axclrtEngineGetModelCompilerVersion(model)<<"\"";
   for(int side=0;side<2;++side){f<<",\""<<(side?"outputs":"inputs")<<"\":[";auto&bs=side?outputs:inputs;for(size_t i=0;i<bs.size();++i){auto&b=bs[i];if(i)f<<',';f<<"{\"name\":\""<<b.name<<"\",\"dtype\":\""<<b.type<<"\",\"bytes\":"<<b.host.size()<<",\"shape\":[";for(size_t j=0;j<b.dims.size();++j){if(j)f<<',';f<<b.dims[j];}f<<"]}";}f<<']';}f<<'}';if(!f)throw std::runtime_error("Cannot save schema");
  }catch(...){release();throw;}
 }
 ~Impl(){release();}
};
ModelSession::ModelSession(const std::string&p):impl_(new Impl(p)){}
ModelSession::~ModelSession(){delete impl_;}
void ModelSession::SetInput(const std::string&name,const void*data,size_t n){for(auto&b:impl_->inputs)if(b.name==name){if(n!=b.host.size())throw std::runtime_error("Input size mismatch "+name);std::memcpy(b.host.data(),data,n);b.set=true;return;}throw std::runtime_error("Unknown input "+name);}
void ModelSession::Run(){
 for(auto&b:impl_->inputs){if(!b.set)throw std::runtime_error("Input missing "+b.name);check(axclrtMemcpy(b.device,b.host.data(),b.host.size(),AXCL_MEMCPY_HOST_TO_DEVICE),"H2D");}
 auto t=std::chrono::steady_clock::now();check(axclrtEngineExecute(impl_->model,impl_->context,0,impl_->io),"execute");double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count();
 for(auto&b:impl_->outputs)check(axclrtMemcpy(b.host.data(),b.device,b.host.size(),AXCL_MEMCPY_DEVICE_TO_HOST),"D2H");
 std::string dir=trace_dir(),prefix=std::to_string(++sequence)+"-"+impl_->name;for(int side=0;side<2;++side)for(auto&b:side?impl_->outputs:impl_->inputs)bytes(dir+"/"+prefix+(side?"-out-":"-in-")+b.name+".bin",b.host);
 std::ofstream log(dir+"/calls.jsonl",std::ios::app);log<<std::setprecision(17)<<"{\"model\":\""<<impl_->name<<"\",\"prefix\":\""<<prefix<<"\",\"executeMilliseconds\":"<<ms<<"}\n";if(!log)throw std::runtime_error("Cannot write trace");for(auto&b:impl_->inputs)b.set=false;
}
size_t ModelSession::OutputBytes(const std::string&name) const{for(auto&b:impl_->outputs)if(b.name==name)return b.host.size();throw std::runtime_error("Unknown output "+name);}
void ModelSession::GetOutput(const std::string&name,void*out,size_t n)const{for(auto&b:impl_->outputs)if(b.name==name){if(n>b.host.size())throw std::runtime_error("Output too large "+name);std::memcpy(out,b.host.data(),n);return;}throw std::runtime_error("Unknown output "+name);}
std::vector<int64_t> ModelSession::OutputShape(const std::string&name)const{for(auto&b:impl_->outputs)if(b.name==name)return b.dims;throw std::runtime_error("Unknown output "+name);}
}
