// Six AXCL hardware decode/NPU/encode streams and a 3x2 overview.
// Seg/depth transforms follow AXERA-TECH/yolo26-seg and Yolo26-Depth references.
#include <opencv2/opencv.hpp>
#include "json.hpp"
#include <dlfcn.h>
#include <atomic>
#include <chrono>
#include <csignal>
#include <condition_variable>
#include <fstream>
#include <iostream>
#include <mutex>
#include <thread>
#include <unordered_map>
#include "common/ax_system.h"
#include "pipeline/ax_pipeline.h"
#include "pipeline/ax_muxer.h"
#include "ax_plugin/ax_plugin.h"
#include "tracking/ax_bytetrack.hpp"
#include "ax_model_runner_axcl.hpp"
#include "axcl_manager.h"
#include "ax_image_internal.h"
using json=nlohmann::json;
using namespace axvsdk;
using Clock=std::chrono::steady_clock;
using Image=common::AxImage;
using Det=axpipeline::ai::Detection;
std::atomic<bool> running{true};
std::atomic<int> errors{0};
std::mutex log_mutex;
double seconds(){return std::chrono::duration<double>(Clock::now().time_since_epoch()).count();}
void log(const json& j){std::lock_guard<std::mutex> l(log_mutex);std::cout<<j.dump()<<std::endl;}
void require(bool v,const std::string& s){if(!v)throw std::runtime_error(s);}
void signal_handler(int){running=false;}
cv::Scalar color(int64_t n){auto v=axpipeline::tracking::ByteTrack::ColorForTrackId(n+1);return {double(v&255),double((v>>8)&255),double((v>>16)&255)};}
void text(cv::Mat& m,const std::string& s,int x,int y,double scale=.75,cv::Scalar c={240,240,240}){
 cv::putText(m,s,{x,y},cv::FONT_HERSHEY_SIMPLEX,scale,{12,12,12},4,cv::LINE_AA);
 cv::putText(m,s,{x,y},cv::FONT_HERSHEY_SIMPLEX,scale,c,2,cv::LINE_AA);
}
std::string cname(int id,const std::string& kind){
 static const std::vector<std::string> coco={"person","bicycle","car","motorcycle","airplane","bus","train","truck","boat","traffic light","fire hydrant","stop sign","parking meter","bench","bird","cat","dog","horse","sheep","cow","elephant","bear","zebra","giraffe","backpack","umbrella","handbag","tie","suitcase","frisbee","skis","snowboard","sports ball","kite","baseball bat","baseball glove","skateboard","surfboard","tennis racket","bottle","wine glass","cup","fork","knife","spoon","bowl","banana","apple","sandwich","orange","broccoli","carrot","hot dog","pizza","donut","cake","chair","couch","potted plant","bed","dining table","toilet","tv","laptop","mouse","remote","keyboard","cell phone","microwave","oven","toaster","sink","refrigerator","book","clock","vase","scissors","teddy bear","hair drier","toothbrush"};
 static const std::vector<std::string> helmet={"helmet","head","e-bike","bike"};
 // PCD class order from AXERA-TECH/Person_car-axera model card.
 static const std::vector<std::string> pcd={"person","car","person_cycle"};
 const auto& names=kind=="helmet"?helmet:kind=="pcd"?pcd:coco;
 return id>=0&&id<int(names.size())?names[id]:"class"+std::to_string(id);
}
void box(cv::Mat& m,const Det& d,const std::string& kind){
 int x0=std::clamp(int(d.x0),0,m.cols-1),y0=std::clamp(int(d.y0),0,m.rows-1);
 int x1=std::clamp(int(d.x1),0,m.cols-1),y1=std::clamp(int(d.y1),0,m.rows-1);
 if(x1<=x0||y1<=y0)return;
 auto c=color(d.track_id>=0?d.track_id:d.class_id);
 cv::rectangle(m,{x0,y0},{x1,y1},c,3);
 std::string label=cname(d.class_id,kind)+cv::format(" %.2f",d.score);
 if(d.track_id>=0)label+=" #"+std::to_string(d.track_id);
 text(m,label,x0,std::max(28,y0-8),.7,c);
}
Image::Ptr wrap(const std::shared_ptr<cv::Mat>& m){
 common::ImageDescriptor d{};d.format=common::PixelFormat::kBgr24;d.width=m->cols;d.height=m->rows;d.strides[0]=m->step;
 std::array<common::ExternalImagePlane,3> p{};p[0].virtual_address=m->data;
 return Image::WrapExternal(d,p,m);
}
cv::Mat download(const Image& f){
 require(f.format()==common::PixelFormat::kNv12,"Expected NV12 decoder image");
 int h=f.height(),w=f.width();std::vector<uint8_t> y(f.plane_size(0)),uv(f.plane_size(1));
 require(axcl_Memcpy(y.data(),(const void*)f.physical_address(0),y.size(),AXCL_MEMCPY_DEVICE_TO_HOST,0)==0,"D2H Y failed");
 require(axcl_Memcpy(uv.data(),(const void*)f.physical_address(1),uv.size(),AXCL_MEMCPY_DEVICE_TO_HOST,0)==0,"D2H UV failed");
 cv::Mat Y(h,w,CV_8UC1,y.data(),f.stride(0)),UV(h/2,w/2,CV_8UC2,uv.data(),f.stride(1)),bgr;
 cv::cvtColorTwoPlane(Y,UV,bgr,cv::COLOR_YUV2BGR_NV12);return bgr;
}
struct Plugin{
 void* so=nullptr;ax_plugin_handle_t handle=nullptr;
 decltype(&ax_plugin_infer) infer=nullptr;decltype(&ax_plugin_release_result) release=nullptr;decltype(&ax_plugin_deinit) deinit=nullptr;
 void init(const std::string& path,const json& options){
  so=dlopen(path.c_str(),RTLD_NOW|RTLD_LOCAL);if(!so)throw std::runtime_error(dlerror());
  auto version=(decltype(&ax_plugin_get_api_version))dlsym(so,"ax_plugin_get_api_version");
  auto initfn=(decltype(&ax_plugin_init))dlsym(so,"ax_plugin_init");
  infer=(decltype(infer))dlsym(so,"ax_plugin_infer");release=(decltype(release))dlsym(so,"ax_plugin_release_result");deinit=(decltype(deinit))dlsym(so,"ax_plugin_deinit");
  require(version&&version()==2&&initfn&&infer&&release&&deinit,"Bad plugin ABI");require(initfn(options.dump().c_str(),0,&handle)==0,"Plugin init failed: "+path);
 }
 std::vector<Det> run(Image& f){
  ax_plugin_image_view_t v{};v.format=(ax_plugin_pixel_format_e)f.format();v.width=f.width();v.height=f.height();v.plane_count=f.plane_count();v.memory_type=AX_PLUGIN_MEMORY_TYPE_AXCL_DEVICE;
  for(size_t i=0;i<v.plane_count;i++){v.strides[i]=f.stride(i);v.physical_addrs[i]=f.physical_address(i);v.virtual_addrs[i]=f.virtual_address(i);v.block_ids[i]=f.block_id(i);}
  ax_plugin_det_result_t r{};int rc=infer(handle,&v,&r);if(rc){release(handle,&r);throw std::runtime_error("Plugin inference failed: "+std::to_string(rc));}
  std::vector<Det> out;for(size_t i=0;i<r.det_count;i++){auto d=r.dets[i];out.push_back({d.x0,d.y0,d.x1,d.y1,d.score,d.class_id,d.track_id});}release(handle,&r);return out;
 }
 ~Plugin(){if(handle)deinit(handle);/* Keep DSO loaded until TLS context destructors finish. */}
};
struct TensorModel{
 ax_runner_axcl runner;bool ready=false;std::vector<char> bytes;int h=0,w=0;std::string kind;float gain=1;int left=0,top=0,nw=0,nh=0;
 void init(const std::string& path,const std::string& k){
  kind=k;std::ifstream f(path,std::ios::binary);require(bool(f),"Missing model "+path);bytes.assign(std::istreambuf_iterator<char>(f),{});
  require(runner.init(bytes.data(),bytes.size(),0)==0,"NPU model init failed "+path);ready=true;
  require(runner.get_num_inputs()==1,"Model input count");auto t=runner.get_input(0);
  require(t.vShape.size()==4&&t.vShape[0]==1&&t.vShape[3]==3,"Model must be NHWC RGB uint8");h=t.vShape[1];w=t.vShape[2];require(t.nSize==h*w*3,"Unexpected input datatype");
  json shapes=json::array();for(int i=0;i<runner.get_num_outputs();i++){auto o=runner.get_output(i);shapes.push_back({{"name",o.sName},{"shape",o.vShape},{"bytes",o.nSize}});}
  log({{"event","model"},{"kind",kind},{"input",t.vShape},{"outputs",shapes}});
  runner.set_auto_sync_before_inference(false);runner.set_auto_sync_after_inference(false);
 }
 void run(const cv::Mat& bgr){
  gain=std::min(float(w)/bgr.cols,float(h)/bgr.rows);
  nw=kind=="depth"?int(std::round(bgr.cols*gain)):int(bgr.cols*gain);nh=kind=="depth"?int(std::round(bgr.rows*gain)):int(bgr.rows*gain);
  left=kind=="depth"?(w-nw)/2:0;top=kind=="depth"?(h-nh)/2:0;
  cv::Mat rgb(h,w,CV_8UC3,cv::Scalar::all(kind=="depth"?114:127)),small;cv::resize(bgr,small,{nw,nh});cv::cvtColor(small,small,cv::COLOR_BGR2RGB);small.copyTo(rgb(cv::Rect(left,top,nw,nh)));
  auto t=runner.get_input(0);require(axcl_Memcpy((void*)t.phyAddr,rgb.data,t.nSize,AXCL_MEMCPY_HOST_TO_DEVICE,0)==0,"NPU H2D failed");
  require(runner.inference()==0,"NPU inference failed");
  for(int i=0;i<runner.get_num_outputs();i++){auto o=runner.get_output(i);require(axcl_Memcpy(o.pVirAddr,(void*)o.phyAddr,o.nSize,AXCL_MEMCPY_DEVICE_TO_HOST,0)==0,"NPU D2H failed");}
 }
 cv::Mat depth(const cv::Mat& src){
  require(runner.get_num_outputs()==1,"Depth outputs");auto o=runner.get_output(0);auto s=o.vShape;
  require(s.size()==4&&s[0]==1&&s[1]==1&&o.nSize==int(s[2]*s[3]*4),"Depth layout");
  cv::Mat raw(s[2],s[3],CV_32F,o.pVirAddr);int x=std::round(float(left)*raw.cols/w),y=std::round(float(top)*raw.rows/h);
  int rw=std::round(float(nw)*raw.cols/w),rh=std::round(float(nh)*raw.rows/h);
  cv::Mat d=raw(cv::Rect(x,y,std::min(rw,raw.cols-x),std::min(rh,raw.rows-y))).clone();
  std::vector<float> pool;pool.reserve(d.total());
  for(auto it=d.begin<float>();it!=d.end<float>();++it){*it=std::isfinite(*it)&&*it>0?1.f/(*it):0.f;if(*it>0)pool.push_back(*it);}
  require(!pool.empty(),"Depth has no finite positive values");
  std::nth_element(pool.begin(),pool.begin()+pool.size()*2/100,pool.end());float lo=pool[pool.size()*2/100];
  std::nth_element(pool.begin(),pool.begin()+pool.size()*98/100,pool.end());float hi=std::max(lo+1e-6f,pool[pool.size()*98/100]);
  cv::Mat gray,heat;d.convertTo(gray,CV_8U,255/(hi-lo),-lo*255/(hi-lo));cv::applyColorMap(gray,heat,cv::COLORMAP_INFERNO);heat.setTo(cv::Scalar::all(0),d<=0);cv::resize(heat,heat,src.size());
  cv::Mat view;cv::addWeighted(src,.35,heat,.65,0,view);text(view,"Relative depth | bright=near | not calibrated metres",30,1030,.85);return view;
 }
 struct Candidate{Det d;std::vector<float> coeff;};
 std::vector<Det> segmentation(cv::Mat& src){
  require(runner.get_num_outputs()==10,"YOLO26 seg requires 10 output tensors");std::vector<Candidate> cand;
  const float threshold=.3f,rawth=std::log(threshold/(1-threshold));
  for(int k=0;k<3;k++){
   auto b=runner.get_output(3*k),c=runner.get_output(3*k+1),m=runner.get_output(3*k+2);
   require(b.vShape.size()==4&&b.vShape[3]==4&&c.vShape.size()==4&&c.vShape[3]==80&&m.vShape.size()==4&&m.vShape[3]==32,"Unexpected seg head layout");
   int gh=b.vShape[1],gw=b.vShape[2],stride=8<<k;require(gh*stride==h&&gw*stride==w,"Seg head grid");
   require(b.nSize==gh*gw*4*4&&c.nSize==gh*gw*80*4&&m.nSize==gh*gw*32*4,"Seg tensor byte size");
   auto bp=(float*)b.pVirAddr,cp=(float*)c.pVirAddr,mp=(float*)m.pVirAddr;
   for(int i=0;i<gh*gw;i++){auto cl=cp+i*80;int id=std::max_element(cl,cl+80)-cl;if(cl[id]<rawth)continue;
    float ax=i%gw+.5f,ay=i/gw+.5f;auto v=bp+i*4;Candidate a;a.d={(ax-v[0])*stride,(ay-v[1])*stride,(ax+v[2])*stride,(ay+v[3])*stride,1.f/(1+std::exp(-cl[id])),id,-1};a.coeff.assign(mp+i*32,mp+(i+1)*32);cand.push_back(std::move(a));}
  }
  std::sort(cand.begin(),cand.end(),[](const auto&a,const auto&b){return a.d.score>b.d.score;});if(cand.size()>300)cand.resize(300);
  std::vector<Candidate> keep;
  for(auto& a:cand){bool suppress=false;for(auto& b:keep){if(a.d.class_id!=b.d.class_id)continue;auto A=a.d,B=b.d;float inter=std::max(0.f,std::min(A.x1,B.x1)-std::max(A.x0,B.x0))*std::max(0.f,std::min(A.y1,B.y1)-std::max(A.y0,B.y0));float den=(A.x1-A.x0)*(A.y1-A.y0)+(B.x1-B.x0)*(B.y1-B.y0)-inter;if(den>0&&inter/den>.7f){suppress=true;break;}}if(!suppress)keep.push_back(a);if(keep.size()>=30)break;}
  auto p=runner.get_output(9);require(p.vShape.size()==4&&p.vShape[1]==32,"Seg proto must be NCHW");int ph=p.vShape[2],pw=p.vShape[3];require(p.nSize==32*ph*pw*4,"Proto bytes");cv::Mat proto(32,ph*pw,CV_32F,p.pVirAddr);
  std::vector<Det> out;cv::Mat colors(nh,nw,CV_8UC3,cv::Scalar::all(0)),union_mask=cv::Mat::zeros(nh,nw,CV_8U);
  for(auto& a:keep){cv::Mat coeff(1,32,CV_32F,a.coeff.data()),flat;cv::gemm(coeff,proto,1,cv::noArray(),0,flat);cv::Mat mask=flat.reshape(1,ph);
   int x0=std::clamp(int(a.d.x0*pw/w),0,pw),y0=std::clamp(int(a.d.y0*ph/h),0,ph),x1=std::clamp(int(a.d.x1*pw/w),0,pw),y1=std::clamp(int(a.d.y1*ph/h),0,ph);
   if(x1<=x0||y1<=y0)continue;
   cv::Mat cropped=cv::Mat::zeros(ph,pw,CV_32F);mask(cv::Rect(x0,y0,x1-x0,y1-y0)).copyTo(cropped(cv::Rect(x0,y0,x1-x0,y1-y0)));
   cv::Mat full,binary;cv::resize(cropped,full,{w,h});cv::compare(full(cv::Rect(0,0,nw,nh)),.5,binary,cv::CMP_GT);
   colors.setTo(color(a.d.class_id),binary);cv::bitwise_or(union_mask,binary,union_mask);
   auto d=a.d;d.x0/=gain;d.y0/=gain;d.x1/=gain;d.y1/=gain;out.push_back(d);
  }
  cv::Mat bigcolors,bigmask,blended;cv::resize(colors,bigcolors,src.size(),0,0,cv::INTER_NEAREST);cv::resize(union_mask,bigmask,src.size(),0,0,cv::INTER_NEAREST);
  cv::addWeighted(src,.55,bigcolors,.45,0,blended);blended.copyTo(src,bigmask);return out;
 }
 ~TensorModel(){if(ready)runner.deinit();}
};
struct Output{
 std::unique_ptr<codec::VideoEncoder> encoder;std::unique_ptr<pipeline::Muxer> mux;
 std::vector<Image::Ptr> staging;double fps=10;uint64_t pending_sequence=0,next_sequence=0;
 std::shared_ptr<cv::Mat> cached_host;Image::Ptr cached_device;
 std::mutex upload_mutex;std::condition_variable upload_cv;std::shared_ptr<cv::Mat> pending_upload;
 std::thread uploader;bool upload_stop=false;std::atomic<uint64_t> replaced{0};double started=0;
 std::atomic<uint64_t> mux_fail{0},submit_fail{0};
 void init(const std::string& uri,double fps,int bitrate){
  this->fps=fps;
  mux=pipeline::CreateMuxer();pipeline::MuxerConfig mc;mc.stream={codec::VideoCodecType::kH264,1920,1080,fps};mc.uris={uri};require(mux->Open(mc),"Muxer open failed "+uri);
  encoder=codec::CreateVideoEncoder();codec::VideoEncoderConfig ec;ec.codec=codec::VideoCodecType::kH264;ec.width=1920;ec.height=1080;ec.device_id=0;ec.frame_rate=fps;ec.bitrate_kbps=bitrate;ec.gop=int(fps*2);ec.input_queue_depth=2;ec.overflow_policy=codec::QueueOverflowPolicy::kDropOldest;
  require(encoder->Open(ec),"VENC open failed");encoder->SetPacketCallback([this](codec::EncodedPacket p){if(!mux->SubmitPacket(std::move(p)))++mux_fail;});require(encoder->Start(),"VENC start failed");
  started=seconds();uploader=std::thread([this]{try{while(true){std::shared_ptr<cv::Mat> frame;uint64_t seq;{std::unique_lock<std::mutex> l(upload_mutex);upload_cv.wait(l,[this]{return upload_stop||pending_upload;});if(upload_stop)break;frame=std::move(pending_upload);seq=pending_sequence;}upload(frame,seq);}}catch(const std::exception& e){log({{"event","upload_error"},{"error",e.what()}});++errors;running=false;}});
 }
 void submit(const std::shared_ptr<cv::Mat>& m){
  std::lock_guard<std::mutex> l(upload_mutex);if(pending_upload)++replaced;pending_upload=m;pending_sequence=next_sequence++;upload_cv.notify_one();
 }
 void upload(const std::shared_ptr<cv::Mat>& m,uint64_t sequence){
  if(cached_host!=m){
  // Host rendering -> packed NV12 -> bulk PCIe upload -> AXCL hardware VENC.
  cv::Mat yuv;cv::cvtColor(*m,yuv,cv::COLOR_BGR2YUV_I420);
  int pixels=m->cols*m->rows;cv::Mat uv(m->rows/2,m->cols/2,CV_8UC2);
  std::vector<cv::Mat> planes={cv::Mat(m->rows/2,m->cols/2,CV_8UC1,yuv.data+pixels),cv::Mat(m->rows/2,m->cols/2,CV_8UC1,yuv.data+pixels+pixels/4)};cv::merge(planes,uv);
  Image::Ptr target;for(auto& p:staging)if(p.use_count()==1){target=p;break;}
  if(!target&&staging.size()<16){common::ImageDescriptor d;d.format=common::PixelFormat::kNv12;d.width=m->cols;d.height=m->rows;d.strides[0]=m->cols;d.strides[1]=m->cols;target=Image::Create(d);require(bool(target),"VENC upload allocation");staging.push_back(target);}
  if(!target){++submit_fail;return;}
  require(target->stride(0)==unsigned(m->cols),"Upload geometry");
  require(axcl_Memcpy((void*)target->physical_address(0),yuv.data,pixels,AXCL_MEMCPY_HOST_TO_DEVICE,0)==0,"VENC Y upload failed");
  require(axcl_Memcpy((void*)target->physical_address(1),uv.data,pixels/2,AXCL_MEMCPY_HOST_TO_DEVICE,0)==0,"VENC UV upload failed");
  cached_host=m;cached_device=target;
  }
  // Repeat unchanged display frames without re-uploading pixels. Each submission
  // has independent timing metadata and retains the immutable device buffer.
  std::array<common::ExternalImagePlane,3> planes{};
  for(size_t i=0;i<cached_device->plane_count();i++){planes[i].physical_address=cached_device->physical_address(i);planes[i].virtual_address=cached_device->virtual_address(i);}
  auto send=Image::WrapExternal(cached_device->descriptor(),planes,cached_device);
  // Grid-aligned PTS prevents the SDK muxer's minimum-step unwrapping from
  // accumulating scheduling jitter into steadily increasing player latency.
  auto info=common::internal::AxImageAccess::MutableAxFrame(send.get());info->u64PTS=uint64_t(std::llround(sequence*1000000/fps));info->u32TimeRef=sequence;info->u64SeqNum=sequence;
  if(!encoder->SubmitFrame(std::move(send)))++submit_fail;
 }
 void close(){if(uploader.joinable()){{std::lock_guard<std::mutex> l(upload_mutex);upload_stop=true;pending_upload.reset();}upload_cv.notify_all();uploader.join();}if(encoder){encoder->Stop();encoder->Close();encoder.reset();}cached_device.reset();cached_host.reset();staging.clear();if(mux){mux->Close();mux.reset();}}
 ~Output(){close();}
};
struct Channel{
 json cfg;int index;double fps;std::unique_ptr<pipeline::Pipeline> input;Output output;Plugin plugin;TensorModel model;
 std::unique_ptr<axpipeline::tracking::ByteTrack> tracker;std::mutex m;std::condition_variable cv;Image::Ptr pending;std::shared_ptr<cv::Mat> latest;
 std::thread worker;std::atomic<uint64_t> frames{0},replaced{0};std::atomic<double> updated{0},infer_ms{0};std::atomic<int> objects{0};
 std::atomic<int> lr{0},rl{0};struct Cross{int side=0;bool counted=false;double seen=0;};std::unordered_map<int64_t,Cross> crosses;
 uint64_t loop_index=0;
 Channel(json j,int i,double f):cfg(j),index(i),fps(f){}
 void init(){
  std::string kind=cfg["kind"];
  if(kind=="depth"||kind=="seg")model.init(cfg["model"],kind);else plugin.init(cfg["plugin"],cfg["plugin_options"]);
  if(kind=="pcd"||kind=="count"){axpipeline::tracking::ByteTrackOptions o;o.frame_rate=int(fps);o.track_buffer=int(fps*3);o.smooth=true;tracker=std::make_unique<axpipeline::tracking::ByteTrack>(o);}
  output.init(cfg["output"],fps,3500);input=pipeline::CreatePipeline();pipeline::PipelineConfig pc;pc.device_id=0;pc.input.uri=cfg["input"];pc.input.realtime_playback=true;pc.input.loop_playback=true;
  pc.frame_output.output_image.format=common::PixelFormat::kNv12;pc.frame_output.output_image.width=1920;pc.frame_output.output_image.height=1080;
  require(input->Open(pc),"Decoder open failed");input->SetFrameCallback([this](Image::Ptr f){std::lock_guard<std::mutex> l(m);if(pending)++replaced;pending=std::move(f);cv.notify_one();});
 }
 void start(){worker=std::thread([this]{run();});require(input->Start(),"Input start failed");}
 void count(std::vector<Det>& ds,cv::Mat& image){
  ds.erase(std::remove_if(ds.begin(),ds.end(),[](auto&d){return d.class_id!=1&&d.class_id!=2&&d.class_id!=3&&d.class_id!=5&&d.class_id!=7;}),ds.end());
  auto tracks=tracker->Update(ds);ds.clear();double now=seconds();float line=cfg.value("line_x",.55)*image.cols;float dead=cfg.value("line_deadband",.015)*image.cols;
  for(auto&t:tracks){ds.push_back({t.x0,t.y0,t.x1,t.y1,t.score,t.class_id,t.track_id});auto& a=crosses[t.track_id];a.seen=now;float x=(t.x0+t.x1)*.5f;int side=x<line-dead?-1:x>line+dead?1:0;
   if(side&&a.side&&side!=a.side&&!a.counted){if(side>0)++lr;else ++rl;a.counted=true;log({{"event","crossing"},{"id",t.track_id},{"direction",side>0?"left_to_right":"right_to_left"},{"lr",lr.load()},{"rl",rl.load()}});}if(side)a.side=side;
  }
  for(auto it=crosses.begin();it!=crosses.end();)if(now-it->second.seen>10)it=crosses.erase(it);else++it;
  cv::line(image,{int(line),90},{int(line),1080},{0,240,255},3);text(image,"L->R "+std::to_string(lr)+"    R->L "+std::to_string(rl),30,145,1.0);
  text(image,"Moving camera: image-line crossings | loops accumulate",30,1040,.8);
 }
 void run(){
  try{std::string kind=cfg["kind"];auto next=Clock::now();
   while(running){std::this_thread::sleep_until(next);Image::Ptr frame;
    {std::unique_lock<std::mutex> l(m);cv.wait_for(l,std::chrono::milliseconds(200),[this]{return pending||!running;});if(!running)break;if(!pending)continue;frame=std::move(pending);}
    double begin=seconds();cv::Mat bgr=download(*frame);std::vector<Det> ds;
    if(kind=="depth"||kind=="seg"){model.run(bgr);if(kind=="depth")bgr=model.depth(bgr);else ds=model.segmentation(bgr);}
    else ds=plugin.run(*frame);
    if(kind=="vehicle")ds.erase(std::remove_if(ds.begin(),ds.end(),[](auto&d){return d.class_id!=0&&d.class_id!=1&&d.class_id!=2&&d.class_id!=3&&d.class_id!=5&&d.class_id!=7&&d.class_id!=9&&d.class_id!=11;}),ds.end());
    if(kind=="count"){
     auto span=cfg.value("source_loop_us",uint64_t(0));auto pts=common::internal::AxImageAccess::GetAxFrame(*frame).u64PTS;
     if(span&&pts/span>loop_index){loop_index=pts/span;axpipeline::tracking::ByteTrackOptions o;o.frame_rate=int(fps);o.track_buffer=int(fps*3);o.smooth=true;tracker=std::make_unique<axpipeline::tracking::ByteTrack>(o);crosses.clear();log({{"event","count_loop_reset"},{"loop",loop_index}});}
     count(ds,bgr);
    }else if(tracker){auto tracks=tracker->Update(ds);ds.clear();for(auto&t:tracks)ds.push_back({t.x0,t.y0,t.x1,t.y1,t.score,t.class_id,t.track_id});}
    for(auto& d:ds)box(bgr,d,kind);
    objects=ds.size();infer_ms=(seconds()-begin)*1000;++frames;
    cv::rectangle(bgr,{0,0},{1920,78},{18,24,34},-1);text(bgr,std::to_string(index+1)+"  "+cfg["title"].get<std::string>(),25,34,.9);
    text(bgr,cv::format("NPU results %llu | objects %d | process %.1f ms",(unsigned long long)frames.load(),objects.load(),infer_ms.load()),25,66,.62);
    {std::lock_guard<std::mutex> l(m);latest=std::make_shared<cv::Mat>(std::move(bgr));updated=seconds();}
    next=Clock::now()+std::chrono::milliseconds(std::max(0,int(1000/fps-infer_ms.load())));
   }
  }catch(const std::exception& e){log({{"event","channel_error"},{"channel",cfg["name"]},{"error",e.what()}});++errors;running=false;}
 }
 void stop(){if(input)input->Stop();cv.notify_all();if(worker.joinable())worker.join();{std::lock_guard<std::mutex> l(m);pending.reset();latest.reset();}if(input){input->Close();input.reset();}output.close();}
 ~Channel(){stop();}
};
int run_application(int argc,char**argv){
 std::vector<std::unique_ptr<Channel>> channels;Output overview;double duration=argc>2?std::stod(argv[2]):0;
 try{
  require(argc>=2,"Usage: six_app config.json [duration_seconds]");std::ifstream f(argv[1]);json config=json::parse(f);double fps=config.value("output_fps",10.);
  common::SystemOptions sys;sys.backend=common::BackendType::kAxcl;sys.device_id=0;require(common::InitializeSystem(sys),"SDK init failed");require(axcl_Dev_Init(0)==0,"AXCL NPU init failed");
  for(auto& c:config["channels"]){auto p=std::make_unique<Channel>(c,channels.size(),fps);p->init();channels.push_back(std::move(p));}
  overview.init(config["overview"],fps,6000);for(auto& c:channels)c->start();double started=seconds(),lastlog=started;auto tick=Clock::now();
  std::vector<uint64_t> before(channels.size(),0),previous(channels.size(),0);uint64_t overview_frames=0;
  while(running&&(!duration||seconds()-started<duration)){
   auto canvas=std::make_shared<cv::Mat>(1080,1920,CV_8UC3,cv::Scalar(15,21,29));bool all=true;double now=seconds();
   for(size_t i=0;i<channels.size();i++){auto& c=*channels[i];std::shared_ptr<cv::Mat> view;{std::lock_guard<std::mutex> l(c.m);view=c.latest;}
    int x=(i%3)*640,y=(i/3)*540;auto cell=(*canvas)(cv::Rect(x,y,640,540));
    text(cell,std::to_string(i+1)+"  "+c.cfg["title"].get<std::string>(),16,37,.65);text(cell,c.cfg["source_name"],16,67,.48,{151,164,181});
    if(view){c.output.submit(view);cv::resize(*view,(*canvas)(cv::Rect(x,y+100,640,360)),{640,360});text(cell,cv::format("NPU #%llu  objects %d  result age %.2fs",(unsigned long long)c.frames.load(),c.objects.load(),std::max(0.,seconds()-c.updated.load())),16,493,.49,{112,222,180});if(now-c.updated>5)throw std::runtime_error("Stale result "+c.cfg["name"].get<std::string>());}
    else{all=false;text(cell,"Starting decoder / NPU...",18,270,.7);if(now-started>30)throw std::runtime_error("No frames from "+c.cfg["name"].get<std::string>());}
    text(cell,"AX8850 | H.264 / RTSP",16,520,.46,{151,164,181});
   }
   if(all){overview.submit(canvas);++overview_frames;}
   if(now-lastlog>=10){json list=json::array();for(size_t i=0;i<channels.size();i++){auto& c=*channels[i];auto e=c.output.encoder->GetStats();list.push_back({{"name",c.cfg["name"]},{"decoded",c.input->GetStats().decoded_frames},{"inferred",c.frames.load()},{"infer_fps",(c.frames-before[i])/(now-lastlog)},{"process_ms",c.infer_ms.load()},{"objects",c.objects.load()},{"result_age",std::max(0.,seconds()-c.updated.load())},{"encoded",e.encoded_packets},{"dropped",e.dropped_frames},{"upload_replaced",c.output.replaced.load()},{"mux_errors",c.output.mux_fail.load()},{"submit_errors",c.output.submit_fail.load()},{"lr",c.lr.load()},{"rl",c.rl.load()}});before[i]=c.frames;}
    auto es=overview.encoder->GetStats();log({{"event","stats"},{"elapsed",now-started},{"channels",list},{"overview_encoded",es.encoded_packets},{"overview_dropped",es.dropped_frames},{"overview_mux_errors",overview.mux_fail.load()}});lastlog=now;
   }
   tick+=std::chrono::microseconds(int(1000000/fps));if(tick<Clock::now()-std::chrono::milliseconds(200))tick=Clock::now();std::this_thread::sleep_until(tick);
  }
 }catch(const std::exception& e){log({{"event","fatal"},{"error",e.what()}});++errors;}
 running=false;for(auto& c:channels)c->stop();overview.close();channels.clear();axcl_Dev_Exit(0);log({{"event","exit"},{"errors",errors.load()}});return errors?1:0;
}
int main(int argc,char**argv){
 std::signal(SIGINT,signal_handler);std::signal(SIGTERM,signal_handler);cv::setNumThreads(1);
 // Join all application/plugin TLS contexts before the SDK finalizes AXCL.
 int rc=1;std::thread app([&]{rc=run_application(argc,argv);});app.join();common::ShutdownSystem();return rc;
}
