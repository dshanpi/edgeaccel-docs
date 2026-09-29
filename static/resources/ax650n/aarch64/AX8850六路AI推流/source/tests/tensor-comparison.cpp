#include "ax_model_runner_axcl.hpp"
#include "axcl_manager.h"
#include <axcl.h>
#include <fstream>
#include <iostream>
#include <vector>
#include <cstring>
#include <thread>
#include <stdexcept>
#include <cstdlib>

void check(int r){if(r)throw std::runtime_error("AXCL error "+std::to_string(r));}
uint64_t hash(const void* ptr,size_t n){uint64_t h=14695981039346656037ULL;auto p=(const unsigned char*)ptr;for(size_t i=0;i<n;i++){h^=p[i];h*=1099511628211ULL;}return h;}
void compare(const char* path){
 std::ifstream f(path,std::ios::binary);std::vector<char> data((std::istreambuf_iterator<char>(f)),{});
 if(data.empty())throw std::runtime_error("Empty model");
 ax_runner_axcl legacy,packed;
 setenv("AXP_AXCL_PACK_OUTPUTS","0",1);check(legacy.init(data.data(),data.size(),0));
 setenv("AXP_AXCL_PACK_OUTPUTS","1",1);check(packed.init(data.data(),data.size(),0));
 if(legacy.get_num_inputs()!=packed.get_num_inputs()||legacy.get_num_outputs()!=packed.get_num_outputs())throw std::runtime_error("IO count mismatch");
 for(unsigned seed:{0U,1U,42U}){
  for(int i=0;i<legacy.get_num_inputs();i++){
   auto a=legacy.get_input(i),b=packed.get_input(i);if(a.nSize!=b.nSize||a.vShape!=b.vShape)throw std::runtime_error("Input mismatch");
   unsigned state=seed+12345;for(size_t j=0;j<size_t(a.nSize);j++){state=1664525*state+1013904223;((unsigned char*)a.pVirAddr)[j]=seed?state>>24:114;}
   std::memcpy(b.pVirAddr,a.pVirAddr,a.nSize);
  }
  check(legacy.inference());check(packed.inference());size_t total=0;
  for(int i=0;i<legacy.get_num_outputs();i++){
   auto a=legacy.get_output(i),b=packed.get_output(i);
   if(a.nSize!=b.nSize||a.vShape!=b.vShape||a.sName!=b.sName)throw std::runtime_error("Output layout mismatch");
   if(std::memcmp(a.pVirAddr,b.pVirAddr,a.nSize))throw std::runtime_error("Output bytes differ for "+a.sName);
   if(a.vShape==std::vector<uint32_t>{1,1,768,768}){
    size_t offset=168ULL*768*4,bytes=432ULL*768*4;void* slice=nullptr;check(axcl_MallocHost(&slice,bytes,0));
    check(axcl_Memcpy(slice,(void*)(b.phyAddr+offset),bytes,AXCL_MEMCPY_DEVICE_TO_HOST,0));
    if(std::memcmp(slice,static_cast<char*>(a.pVirAddr)+offset,bytes))throw std::runtime_error("Depth crop bytes differ");
    check(axcl_FreeHost(slice,0));std::cout<<"DEPTH_CROP_MATCH bytes="<<bytes<<" full_bytes="<<a.nSize<<std::endl;
   }
   total+=a.nSize;
   std::cout<<"MATCH seed="<<seed<<" tensor="<<i<<" bytes="<<a.nSize<<" hash="<<std::hex<<hash(a.pVirAddr,a.nSize)<<std::dec<<std::endl;
  }
  std::cout<<"PASS model="<<path<<" seed="<<seed<<" outputs="<<legacy.get_num_outputs()<<" bytes="<<total<<std::endl;
 }
 packed.deinit();legacy.deinit();
}
int main(int argc,char**argv){check(axclInit(nullptr));int rc=0;std::thread t([&]{try{check(axcl_Dev_Init(0));for(int i=1;i<argc;i++)compare(argv[i]);}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<std::endl;rc=1;}});t.join();check(axclFinalize());return rc;}
