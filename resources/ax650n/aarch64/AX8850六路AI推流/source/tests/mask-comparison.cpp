#include <opencv2/opencv.hpp>
#include <chrono>
#include <iostream>
#include <vector>
cv::Mat calc(const cv::Mat& coeff,const cv::Mat& proto,cv::Rect roi,bool opt){
 cv::Mat cropped=cv::Mat::zeros(160,160,CV_32F),flat;
 if(opt){cv::Mat selected(32,roi.area(),CV_32F);for(int k=0;k<32;k++){cv::Mat plane(160,160,CV_32F,(void*)proto.ptr<float>(k));cv::Mat target=selected.row(k).reshape(1,roi.height);plane(roi).copyTo(target);}cv::gemm(coeff,selected,1,cv::noArray(),0,flat);flat.reshape(1,roi.height).copyTo(cropped(roi));}
 else{cv::gemm(coeff,proto,1,cv::noArray(),0,flat);cv::Mat mask=flat.reshape(1,160);mask(roi).copyTo(cropped(roi));}
 return cropped;
}
int main(){cv::setNumThreads(1);cv::RNG rng(12345);cv::Mat proto(32,25600,CV_32F),coeff(1,32,CV_32F);rng.fill(proto,cv::RNG::UNIFORM,-2,2);rng.fill(coeff,cv::RNG::UNIFORM,-2,2);
 std::vector<cv::Rect> rois={{0,0,160,160},{0,0,1,1},{159,159,1,1},{20,30,12,10},{40,40,20,14},{17,13,37,27},{0,40,160,30},{25,0,30,160},{70,70,50,60}};
 for(auto r:rois){auto a=calc(coeff,proto,r,false),b=calc(coeff,proto,r,true);double diff=cv::norm(a,b,cv::NORM_INF);cv::Mat aa,bb;cv::resize(a,aa,{640,640});cv::resize(b,bb,{640,640});int masks=cv::countNonZero((aa>.5)!=(bb>.5));std::cout<<"ROI "<<r<<" max_error="<<diff<<" differing_mask_pixels="<<masks<<std::endl;if(diff>1e-5||masks)return 1;}
 for(bool opt:{false,true}){auto t=std::chrono::steady_clock::now();for(int i=0;i<100;i++)for(auto r:std::vector<cv::Rect>{{20,30,12,10},{40,40,20,14},{17,13,37,27}})calc(coeff,proto,r,opt);std::cout<<"optimized="<<opt<<" ms_per_mask="<<std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count()/300<<std::endl;}
}
