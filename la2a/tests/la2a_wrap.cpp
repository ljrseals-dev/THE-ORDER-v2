#include "la2a_core.h"
#include <vector>
extern "C" void la2a_run(const float* inL,const float* inR,float* outL,float* outR,float* gr,int n,int nch,double fs,double gainDb,double pr,int compress,int link){
  la2a::Engine e; e.setParams(gainDb,pr,compress!=0,link!=0); e.prepare(fs);
  for(int i=0;i<n;++i){ const float* in[2]={inL+i,inR?inR+i:inL+i}; float* out[2]={outL+i,outR?outR+i:outL+i}; e.process(in,out,1,nch); gr[i]=(float)e.grDb(); } }
