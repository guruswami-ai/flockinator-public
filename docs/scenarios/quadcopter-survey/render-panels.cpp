// Documentation-only fixtures. Uses the panel renderer; never connects to hardware.
#include "recon_render.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
using namespace recon;
void write(const std::filesystem::path& dir,const std::string& id,Scene s,int index=0){
 node::Frame frame,scratch;
 render(frame,scratch,s,index);
 std::ofstream out(dir/(id+".ppm"),std::ios::binary);
 out<<"P6\n64 64\n255\n";
 for(auto c:frame.pixels){char rgb[]={char(((c>>11)&31)*255/31),char(((c>>5)&63)*255/63),char((c&31)*255/31)};out.write(rgb,3);}
 if(!out.good())throw std::runtime_error("Cannot write image");
}
int main(int argc,char** argv){
 if(argc!=2)return 2;std::filesystem::path dir=argv[1];std::filesystem::create_directories(dir);
 // 25 of the firmware enum's 30 states: ENGAGE/KILL are outside this
 // non-weaponised survey scenario; FRIEND/TARGET/BLANK are not shown.
 const State states[]={READY,APPROVED,ORDERS,TAKEOFF,DEPLOY,SCAN,LOITER,SEEN,SHARE,CHECK,DOUBT,LOST,HOLD,ALERT,PRIORITY,CLAIM,ASSIGN,YIELD,R2B,LAND,CHARGE,STANDBY,NOLINK,EMPTY,CRASH};
 Scene s;s.phase=2.1f;s.motion=34;s.launch=1;s.observations=true;s.owner=2;s.source=0;s.peer=1;s.cycle=1;
 for(auto state:states){s.state=state;s.direction=0;s.commAge=99;s.phase=state==APPROVED?.1f:state==CRASH?1.2f:2.1f;write(dir,name(state),s);}
 const float ages[]={.125f,.3125f,.5f,.75f};
 for(int i=0;i<4;i++){
  s.state=SHARE;s.phase=2.1f;s.direction=1;s.peer=1;s.commAge=ages[i];write(dir,"TX-"+std::to_string(i),s);
  s.state=CHECK;s.direction=2;s.peer=0;write(dir,"RX-"+std::to_string(i),s,1);
 }
 s.state=ALERT;s.direction=1;s.peer=255;s.commAge=.125f;write(dir,"BROADCAST-TX",s);
 s.direction=2;s.peer=0;write(dir,"BROADCAST-RX",s,1);
 std::cout<<"Rendered 35 panel fixtures at 64 x 64 pixels.\n";
}
