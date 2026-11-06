#include "mission_world.h"
#include <unity.h>
void setUp(){} void tearDown(){}
void poses(){
 recon::Scene s;s.state=recon::SCAN;
 auto a=mission_world::pose(0,40,s);s.state=recon::SHARE;s.phase=0;
 auto b=mission_world::pose(0,40,s);TEST_ASSERT_FLOAT_WITHIN(.0001,a.position.y,b.position.y);
 auto c=mission_world::pose(0,40.125,s);TEST_ASSERT_TRUE(c.position.y>b.position.y);
 s.state=recon::TAKEOFF;s.phase=0;a=mission_world::pose(0,6,s);s.phase=6;b=mission_world::pose(0,12,s);
 TEST_ASSERT_FLOAT_WITHIN(.001,.25,a.position.z);TEST_ASSERT_TRUE(b.position.z>a.position.z);TEST_ASSERT_TRUE(b.pitch>a.pitch);
 s.state=recon::R2B;s.phase=8;a=mission_world::pose(0,108,s);s.state=recon::LAND;s.phase=0;b=mission_world::pose(0,108,s);
 TEST_ASSERT_FLOAT_WITHIN(.001,a.position.y,b.position.y);TEST_ASSERT_FLOAT_WITHIN(.001,a.position.z,b.position.z);
 s.phase=6;b=mission_world::pose(0,114,s);TEST_ASSERT_FLOAT_WITHIN(.001,.25,b.position.z);
 s.state=recon::CRASH;s.phase=2;b=mission_world::pose(0,102,s);TEST_ASSERT_FLOAT_WITHIN(.001,-90,b.pitch);TEST_ASSERT_FALSE(mission_world::airborne(s));
}
void render_cycle(){
 static node::Frame a,scratch,b,tmp;recon::Runtime r;recon::Config c;c.run=1;c.seed=271828;r.apply(c,true,0,0);
 for(unsigned t=0;t<127000;t+=500)for(int i=0;i<16;i++){
  mission_world::render(a,scratch,r,t,i);TEST_ASSERT_FALSE(a.clipped);
  auto scene=r.frame(t,i);
  if(scene.state==recon::BLANK||scene.state==recon::MARK||scene.state==recon::STANDBY||scene.state==recon::APPROVED){
   recon::render(b,tmp,scene,i);TEST_ASSERT_EQUAL_MEMORY(a.pixels,b.pixels,sizeof(a.pixels));
  }
 }
}
int main(){UNITY_BEGIN();RUN_TEST(poses);RUN_TEST(render_cycle);return UNITY_END();}
