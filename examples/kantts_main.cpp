#include "ax_engine.hpp"
#include "kantts.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
using namespace kantts;
static void wav(const std::string&p,const std::vector<float>&a){
 std::vector<int16_t> pcm(a.size());for(size_t i=0;i<a.size();++i){if(!std::isfinite(a[i]))throw std::runtime_error("Non-finite waveform");pcm[i]=int16_t(std::max(-1.f,std::min(1.f,a[i]))*32767.f);}
 std::ofstream f(p,std::ios::binary);auto wr=[&](const void*x,size_t n){f.write((const char*)x,n);};uint32_t data=pcm.size()*2,sz=36+data,hdr=16,rate=16000,bps=32000;uint16_t fmt=1,ch=1,bits=16,ba=2;
 wr("RIFF",4);wr(&sz,4);wr("WAVEfmt ",8);wr(&hdr,4);wr(&fmt,2);wr(&ch,2);wr(&rate,4);wr(&bps,4);wr(&ba,2);wr(&bits,2);wr("data",4);wr(&data,4);wr(pcm.data(),data);if(!f)throw std::runtime_error("WAV write failed");
}
int main(int argc,char**argv){
 if(argc!=4){std::cerr<<"usage: kantts_card MODEL_DIR JOBS.tsv OUTPUT_DIR\n";return 2;}int code=0;
 try{
  std::string model=argv[1],out=argv[3];setenv("KANTTS_TRACE_DIR",(out+"/schema").c_str(),1);AxRuntimeInit();
  {KanttsPipeline pipeline(model+"/model",model+"/model/resource",model+"/model/am_config.yaml");std::ifstream jobs(argv[2]);if(!jobs)throw std::runtime_error("Cannot read jobs");std::string line;
   while(std::getline(jobs,line)){std::stringstream ss(line);std::string id,file,speed;std::getline(ss,id,'\t');std::getline(ss,file,'\t');std::getline(ss,speed,'\t');if(id.empty()||id.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789-")!=std::string::npos)throw std::runtime_error("Invalid sample id");float factor=std::stof(speed);if(!std::isfinite(factor)||factor<.5||factor>2)throw std::runtime_error("Duration factor outside .5..2");
    std::ifstream input(file);if(!input)throw std::runtime_error("Cannot open symbols");std::vector<std::string> symbols;std::string sym;while(std::getline(input,sym))if(!sym.empty())symbols.push_back(sym);if(symbols.empty())throw std::runtime_error("Empty symbols");
    std::filesystem::create_directories(out+"/"+id);setenv("KANTTS_TRACE_DIR",(out+"/"+id).c_str(),1);setenv("KANTTS_SPEED",speed.c_str(),1);
    auto start=std::chrono::steady_clock::now();auto audio=pipeline.SynthesizeSymbols(symbols);double sec=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();wav(out+"/"+id+"/output.wav",audio);
    std::ofstream raw(out+"/"+id+"/audio.f32",std::ios::binary);raw.write((char*)audio.data(),audio.size()*4);if(!raw)throw std::runtime_error("Raw audio write failed");
    std::ofstream log(out+"/"+id+"/result.json");log<<std::setprecision(17)<<"{\"id\":\""<<id<<"\",\"segments\":"<<symbols.size()<<",\"durationFactor\":"<<factor<<",\"synthesisSecondsWithTrace\":"<<sec<<",\"sampleRate\":16000,\"samples\":"<<audio.size()<<"}";if(!log)throw std::runtime_error("Result write failed");std::cout<<id<<" samples="<<audio.size()<<" synthesis_seconds="<<sec<<std::endl;
   }
  }
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';code=1;}
 try{AxRuntimeDeinit();}catch(const std::exception&e){std::cerr<<e.what()<<'\n';code=1;}return code;
}
