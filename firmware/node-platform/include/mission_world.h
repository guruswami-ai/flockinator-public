#pragma once
#include "world_render.h"

// Shared presentation choreography. No navigation or target decision policy.
namespace mission_world {
inline world::Pose flight(int index,float elapsed){return world::authored(index,uint32_t(std::max(0.f,elapsed-12)*1000));}
inline world::Pose pose(int index,float elapsed,const recon::Scene& s){
 auto home=flight(index,12),p=flight(index,elapsed);
 if(elapsed<12){float u=recon::smooth((elapsed-6)/6);p.position.z=.25f+(home.position.z-.25f)*u;p.pitch=-60+(home.pitch+60)*u;p.roll=home.roll*u;}
 if(s.state==recon::R2B||s.state==recon::LAND){
  auto entry=flight(index,elapsed-s.phase-(s.state==recon::LAND?8:0));float u=s.state==recon::LAND?1:recon::smooth(s.phase/8);
  p.position=world::mix(entry.position,home.position,u);p.heading=entry.heading+(home.heading-entry.heading)*u;p.pitch=entry.pitch+(home.pitch-entry.pitch)*u;p.roll=entry.roll*(1-u);
  if(s.state==recon::LAND){float d=recon::smooth(s.phase/6);p.position.z=home.position.z+(.25f-home.position.z)*d;p.pitch=home.pitch+(-60-home.pitch)*d;}
 }
 if(s.state==recon::CRASH||s.state==recon::EMPTY||s.state==recon::NOLINK){
  p=flight(index,elapsed-s.phase);
  if(s.state==recon::CRASH){float u=recon::smooth(s.phase/2);p.position.z+=(.25f-p.position.z)*u;p.pitch+=(-90-p.pitch)*u;p.roll+=(index%2?-180:180)*u;}
 }
 if(s.state==recon::STANDBY||s.state==recon::CHARGE){p=home;p.position.z=.25;p.pitch=-60;p.roll=0;}
 return p;
}
inline bool airborne(const recon::Scene& s){
 switch(s.state){case recon::READY:case recon::APPROVED:case recon::ORDERS:case recon::STANDBY:case recon::CHARGE:case recon::BLANK:return false;default:break;}
 return !(s.state==recon::MARK&&s.phase>=10)&&!(s.state==recon::CRASH&&s.phase>=2)&&!(s.state==recon::EMPTY&&s.phase>=3);
}
inline world::Sensor sensor(uint8_t s){return s==recon::CAM?world::Cam:s==recon::WH?world::WhiteHot:s==recon::BH?world::BlackHot:s==recon::IR?world::IR:world::Night;}
inline world::Sample render(node::Frame& f,node::Frame& scratch,const recon::Runtime& runtime,uint32_t now,int index){
 auto s=runtime.frame(now,index);uint32_t elapsed=runtime.elapsed(now),duration=(32+runtime.config.seconds+26+5)*1000u;
 float t=(elapsed%duration)/1000.f;
 world::Sample sample{pose(index,t,s),uint32_t(t*1000),0,world::Air,world::Live};
 if(s.state==recon::CRASH){sample.age=s.phase*1000;sample.stage=s.phase>=2?world::Ground:world::Impact;}
 if(!airborne(s)&&s.state!=recon::CRASH){recon::render(f,scratch,s,index);return sample;}
 if(s.state==recon::MARK){recon::render(f,scratch,s,index);return sample;}
 world::Peer peers[16]{};int count=0;
 for(int id=0;id<16;id++)if(id!=index){auto peer=runtime.frame(now,id);if(airborne(peer))peers[count++]={id,pose(id,t,peer).position};}
 world::render(scratch,sample,index,sensor(s.sensor),peers,count);
 recon::render(f,scratch,s,index,&scratch,sample.pose.heading,sample.pose.pitch,sample.pose.roll,sample.pose.position.z);
 return sample;
}
} // namespace mission_world
