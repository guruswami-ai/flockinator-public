import {distanceLabel,returnLabel} from './readouts.mjs';
import {variants} from './variants.mjs';
import {reversibleStates,visualPhase} from './playback.mjs';
import {simulatedHeading,northArrow} from './compass.mjs';
export const states=['HOLD','SCAN','SEEN','SHARE','CHECK','DOUBT','ENGAGE','LOST','ZOOM','CRASH','EMPTY','NOLINK','ALERT','PRIORITY','CLAIM','ASSIGN','YIELD','LOITER','R2B','LAND','CHARGE','STANDBY','FRIEND','TARGET','DEPLOY'];
export const designationColors={friendly:'#4488ff',target:'#ff3030'};
export const sensorViews={cam:'TV · daylight',night:'NV · night vision',whitehot:'WH · white-hot',blackhot:'BH · black-hot',ir:'IR strobe'};
// Keep legacy timeline keys; display the shared firmware's current vocabulary.
export const stateLabel=state=>state==='ZOOM'?'MARK':state==='ENGAGE'?'EVENT':state;
export const descriptions={HOLD:'Hovering, waiting for the next simulated order.',SCAN:'A banking horizon and flowing ground texture suggest forward flight.',SEEN:'Single-pixel synthetic contacts have been observed. Corner brackets mark the group.',SHARE:'Paired message pulses: orange TX on the sender, green RX on the receiver. Each border flashes twice.',CHECK:'A second observation is requested before accepting a report.',DOUBT:'Two conflicting locations remain visible. Neither is silently treated as truth.'};
Object.assign(descriptions,{
 DEPLOY:'Twenty seconds of outbound flight to spread into the survey area. No sightings or identification reports appear during deployment.',
 FRIEND:'A scripted friendly group uses separate blue pixels inside a selection square and is broadcast to peers. The report source stays visible beside the warning.',
 TARGET:'A scripted classified group uses separate red pixels inside a selection square. Unidentified people remain black/white pixels across sensor modes.',
 LOITER:'Following a scripted orbit or grid-pattern survey. The path is an animated illustration, not navigation data.',
 R2B:'Returning to the illustrated home station; mission observation markers give way to a home cue.',
 LAND:'A forward-only six-second descent. Altitude reaches zero and the camera settles onto the ground.',
 CHARGE:'Landed at a simulated charging pad. Battery fills before the node becomes ready again; charging time is compressed for presentation.',
 STANDBY:'A reserve node stays on its pad, available for another mission. It has not taken off.',
 APPROVED:'Mission approved. A flashing title announces the next fictional mission.',
 ORDERS:'Survey the sector, share observations and keep clear. Scripted presentation instructions.',
 TAKEOFF:'The fleet lifts off together; altitude rises smoothly into the survey flight.',
 BLANK:'Node finished. Waiting for the next mission; the entire fleet has a five-second blank interval.',
 ALERT:'A scripted beacon alert is broadcast: orange TX at its source, green RX at receiving nodes.',
 PRIORITY:'Preset P1 and P2 beacon labels make the demonstration priority visible; P1 is highlighted.',
 CLAIM:'Two scripted nodes request ownership of the same fictional observation.',
 ASSIGN:'The storyboard names one observation owner. This is a preset result, not a live decision.',
 YIELD:'Peers release their duplicate claim and show the assigned owner.',
 ENGAGE:'Scripted inspection event: brackets close around the fictional beacon. This is a visual event, not an aircraft command.',
 LOST:'Target lost: the observation drifts out of view, leaving a search reticle and last-known marker.',
 ZOOM:'Closing on red contacts: ground and people enlarge, the horizon leaves the frame and the central contact fills the camera before black. Target fixation with a solid red border and countdown 00:10 to 00:01 during zoom, then 1.5 seconds of black screen and five seconds of SIGNAL LOST static.',
 CRASH:'The camera tumbles toward the ground, settles against dirt with no horizon, and holds still. At three seconds, SIGNAL LOST static begins for five seconds.',
 EMPTY:'Simulated battery drains to zero. The image dims and freezes; status remains readable.',
 NOLINK:'Contact lost: the last simulated camera image is held while its age increases. Battery remains separate.'});
export const fonts={
 ':':['000','010','000','010','000'],
 'A':['010','101','111','101','101'],'B':['110','101','110','101','110'],'C':['011','100','100','100','011'],'D':['110','101','101','101','110'],'E':['111','100','110','100','111'],'F':['111','100','110','100','100'],'G':['011','100','101','101','011'],'H':['101','101','111','101','101'],'I':['111','010','010','010','111'],'J':['001','001','001','101','010'],'K':['101','101','110','101','101'],'L':['100','100','100','100','111'],'M':['101','111','111','101','101'],'N':['101','111','111','111','101'],'O':['010','101','101','101','010'],'P':['110','101','110','100','100'],'Q':['010','101','101','111','011'],'R':['110','101','110','101','101'],'S':['011','100','010','001','110'],'T':['111','010','010','010','010'],'U':['101','101','101','101','111'],'V':['101','101','101','101','010'],'W':['101','101','111','111','101'],'X':['101','101','010','101','101'],'Y':['101','101','010','010','010'],'Z':['111','001','010','100','111'],
 '+':['000','010','111','010','000'],
 '0':['111','101','101','101','111'],'1':['010','110','010','010','111'],'2':['110','001','010','100','111'],'3':['110','001','010','001','110'],'4':['101','101','111','001','001'],'5':['111','100','110','001','110'],'6':['011','100','111','101','111'],'7':['111','001','010','010','010'],'8':['111','101','111','101','111'],'9':['111','101','111','001','110'],'?':['110','001','010','000','010'],'-':['000','000','111','000','000'],' ':['000','000','000','000','000']};
export const palettes={
 phosphor:{bg:'#06110d',ground:'#0a1b14',low:'#102b20',road:'#244134',building:'#1b392b',edge:'#3a5945',ink:'#c4f6a4',dim:'#759d70',accent:'#92f5ad',warn:'#ffd17b',conflict:'#ff9fc8'},
 ice:{bg:'#050e16',ground:'#0a1924',low:'#112a38',road:'#254352',building:'#1b3546',edge:'#3a596b',ink:'#d7efff',dim:'#7b9da8',accent:'#82e9f4',warn:'#ffd17b',conflict:'#ff9fc8'},
 amber:{bg:'#140e06',ground:'#201a0c',low:'#312611',road:'#4d3b1c',building:'#3d3019',edge:'#6b5130',ink:'#ffe1a0',dim:'#b69b69',accent:'#ffd07c',warn:'#fff0c0',conflict:'#ff9fc8'}};
export const peerLabel=peer=>peer==='ALL'?'ALL':labelFor(peer);
export function labelFor(index){return String.fromCharCode(65+index%4)+(1+Math.floor(index/4));}
export const stateDuration=state=>state==='ZOOM'?16.5:state==='LAND'?6:state==='DEPLOY'?20:8;
export const sequenceDuration=states.reduce((sum,state)=>sum+stateDuration(state),0);
export function sceneAt(t,index=0){
 const duration=sequenceDuration;
 let phase=((t+index*2.37)%duration+duration)%duration;
 for(const state of states){if(phase<stateDuration(state))return {state,phase};phase-=stateDuration(state);}
 return {state:states[0],phase:0};
}
export function stateAt(t,index){return sceneAt(t,index).state;}
export function eventVisual(state,phase,variant=0){
 const profile=variants[variant]||variants[0];
 const s=Math.max(0,phase),staticStart=state==='ZOOM'?11.5:state==='CRASH'?3:Infinity;
 return {zoom:state==='ZOOM'?1+(profile.zoomMax-1)*(Math.min(s,10)/10)**profile.zoomPower:1,
  approach:state==='ZOOM'&&s<10,blackout:state==='ZOOM'&&s>=10&&s<11.5,signalLost:s>=staticStart&&s<staticStart+5,
  grounded:state==='CRASH'&&s>=profile.rollTime,
  roll:state==='CRASH'?profile.roll*Math.PI*Math.min(s/profile.rollTime,1):0,
  cameraElapsed:state==='NOLINK'?0:state==='CRASH'?Math.min(s,profile.rollTime):state==='EMPTY'?Math.min(s,3):s,
  battery:state==='EMPTY'?Math.max(0,5-Math.floor(s*2)):state==='CHARGE'?Math.min(5,1+Math.floor(s/1.5)):state==='R2B'?3:state==='LAND'?1:5,
  dim:state==='EMPTY'?1-Math.min(s/3,1)*.8:1};
}
export const communicationColors={TX:'#ff8a24',RX:'#32ed70'};
export function communicationPulse(age){return age>=0&&(age<.25||(age>=.375&&age<.625));}
export function renderHUD({time=0,index=0,state=stateAt(time,index),palette='phosphor',sensor='night',phase=sceneAt(time,index).phase,communication=null,designation=null,variant=0,coordination=null,camera=null,mission=1,readouts=null,world=null}={}){
 const p=palettes[palette]||palettes.phosphor,rgba=new Uint8ClampedArray(64*64*4),cache={};
 const profile=variants[variant]||variants[0],event=eventVisual(state,phase,variant),motionPhase=visualPhase(state,phase);
 function pixel(x,y,color){x=Math.round(x);y=Math.round(y);if(x<0||x>63||y<0||y>63)return;const c=cache[color]??=(color.slice(1).match(/../g).map(v=>parseInt(v,16)));const i=(y*64+x)*4;rgba[i]=c[0];rgba[i+1]=c[1];rgba[i+2]=c[2];rgba[i+3]=255;}
 function rect(x,y,w,h,color){for(let yy=y;yy<y+h;yy++)for(let xx=x;xx<x+w;xx++)pixel(xx,yy,color);}
 function line(x0,y0,x1,y1,c){x0=Math.round(x0);y0=Math.round(y0);x1=Math.round(x1);y1=Math.round(y1);let dx=Math.abs(x1-x0),sx=x0<x1?1:-1,dy=-Math.abs(y1-y0),sy=y0<y1?1:-1,err=dx+dy;for(;;){pixel(x0,y0,c);if(x0===x1&&y0===y1)break;let e=2*err;if(e>=dy){err+=dy;x0+=sx;}if(e<=dx){err+=dx;y0+=sy;}}}
 function text(x,y,s,c){for(const ch of s){const glyph=fonts[ch]||fonts['?'];glyph.forEach((r,yy)=>[...r].forEach((v,xx)=>{if(v==='1')pixel(x+xx,y+yy,c);}));x+=4;}}
 function corners(x,y,r,c,dashed=false){if(dashed){for(let k=-r;k<=r;k+=3){pixel(x+k,y-r,c);pixel(x+k,y+r,c);pixel(x-r,y+k,c);pixel(x+r,y+k,c);}return;}for(const sx of [-1,1])for(const sy of [-1,1]){line(x+sx*r,y+sy*r,x+sx*(r-3),y+sy*r,c);line(x+sx*r,y+sy*r,x+sx*r,y+sy*(r-3),c);}}
 function square(x,y,r,c){line(x-r,y-r,x+r,y-r,c);line(x+r,y-r,x+r,y+r,c);line(x+r,y+r,x-r,y+r,c);line(x-r,y+r,x-r,y-r,c);}
 function border(){const color=event.approach?'#ff3030':communicationColors[communication?.direction];if(color&&(event.approach||communicationPulse(communication.age))){line(0,0,63,0,color);line(0,63,63,63,color);line(0,1,0,62,color);line(63,1,63,62,color);}}
 rect(0,0,64,64,p.bg);
 if(state==='BLANK'){rect(0,0,64,64,'#000000');return rgba;}
 if(state==='APPROVED'||state==='ORDERS'){
  rect(0,0,64,64,'#000000');
  if(state==='APPROVED'){
   if(Math.floor(phase*2)%2===0){text(18,24,'MISSION',p.accent);text(16,33,'APPROVED',p.accent);}
  }else{
   text(2,1,labelFor(index),p.ink);text(50,1,distanceLabel(readouts?.distanceKm),p.accent);
   text(20,13,'ORDERS',p.accent);text(18,25,'SURVEY',p.ink);text(12,34,'SHARE DATA',p.ink);text(12,43,'KEEP CLEAR',p.ink);
   text(12,58,'MISSION '+String(mission).padStart(2,'0'),p.dim);
  }
  return rgba;
 }

 if(event.blackout){rect(0,0,64,64,'#000000');border();return rgba;}
 if(event.signalLost){
  const frame=Math.floor(phase*8),shades=['#101315','#22272a','#343a3d','#4b5357','#697175'];
  for(let y=0;y<64;y++)for(let x=0;x<64;x++){
   let seed=((x+y*64+1)^Math.imul(frame+1,0x45d9f3b)^Math.imul(index+1,0x27d4eb2d)^Math.imul(variant+1,0x85ebca6b))>>>0;
   seed=Math.imul(seed^(seed>>>16),0x45d9f3b);seed=Math.imul(seed^(seed>>>16),0x45d9f3b);seed=(seed^(seed>>>16))>>>0;
   pixel(x,y,shades[seed%shades.length]);
  }
  rect(0,0,64,8,p.bg);text(2,1,labelFor(index),p.ink);text(50,1,distanceLabel(readouts?.distanceKm),p.accent);
  rect(8,25,48,11,'#000000');text(10,28,'SIGNAL LOST','#e1e8e9');
  rect(0,50,64,14,p.bg);text(2,52,stateLabel(state),p.warn);text(2,58,'FEED LOST',p.dim);
  border();return rgba;
 }
 if(state==='CHARGE'||state==='STANDBY'){
  text(2,1,labelFor(index),p.ink);text(50,1,distanceLabel(readouts?.distanceKm),p.accent);line(1,7,62,7,p.dim);
  // Ten pad layouts retain the per-node visual treatment while parked.
  const pad=18+variant%5,cy=27;
  corners(32,cy,pad,p.dim);line(24,cy-7,24,cy+7,p.accent);line(40,cy-7,40,cy+7,p.accent);line(24,cy,40,cy,p.accent);
  const blink=state==='CHARGE'&&Math.floor(phase*2)%2===0;
  rect(18,42,27,6,p.dim);rect(19,43,25,4,p.bg);rect(19,43,event.battery*5,4,blink?p.ink:p.accent);rect(45,44,2,2,p.dim);
  text(2,52,state,p.ink);text(2,58,designation?.kind==='friendly'?'FRIEND '+labelFor(designation.source):state==='STANDBY'?'RESERVE':event.battery===5?'READY':'BAT '+event.battery*20,designation?.kind==='friendly'?designationColors.friendly:p.dim);
  text(18,10,'PAD '+String(variant+1).padStart(2,'0'),p.dim);border();return rgba;
 }
 const motion=variants[camera?.variant]||profile,baseTime=camera?.motionTime??camera?.time??time;
 const visualTime=reversibleStates.has(state)?(camera?.motionTime??(baseTime-phase+motionPhase)):baseTime-phase+event.cameraElapsed;
 const t=visualTime+index*1.71+motion.offset,fly=(camera?1:state==='HOLD'?0.3:1)*motion.speed;
 const heading=Math.round(world?.pose.heading??simulatedHeading(t,index,camera?.variant??variant))%360;
 const landing=Math.max(0,Math.min(1,phase/6)),landEase=landing*landing*(3-2*landing);
 const launch=state==='LAND'?1-landEase:camera?.launch??1;
 // Forward-looking attitude scene. Texture is a motion cue, not terrain data.
 // Takeoff reveals the horizon once, from a ground-filled view. Aim at the
 // first airborne attitude rather than adding oscillation to the ascent.
 const attitudeTime=state==='TAKEOFF'?6+index*1.71+motion.offset:['ZOOM','LAND'].includes(state)?baseTime-phase+index*1.71+motion.offset:t;
 const airborneBank=motion.bank+Math.sin(attitudeTime*.32*motion.rate)*motion.sway;
 const airbornePitch=motion.pitch+Math.sin(attitudeTime*.43*motion.rate)*motion.heave;
 const crashProgress=state==='CRASH'?Math.min(1,Math.max(0,phase/profile.rollTime)):0;
 const crashEase=crashProgress*crashProgress*(3-2*crashProgress);
 const bank=world?world.pose.roll*Math.PI/180:airborneBank*launch,pitch=world?42*Math.tan(Math.max(-60,world.pose.pitch)*Math.PI/180):state==='CRASH'?airbornePitch+(-60-airbornePitch)*crashEase:['TAKEOFF','LAND'].includes(state)?-32+(airbornePitch+32)*launch:airbornePitch;
 const thermal=sensor==='whitehot'||sensor==='blackhot';
 const observationsEnabled=!['TAKEOFF','DEPLOY'].includes(state)&&(camera?.observationsEnabled??true);
 const heatColors={[p.bg]:28,[p.low]:64,[p.edge]:104,[p.accent]:155};
 const daylightColors={[p.bg]:'#607b8a',[p.low]:'#454e37',[p.edge]:'#827557',[p.accent]:'#afc9ce'};
 const cosBank=Math.cos(bank),sinBank=Math.sin(bank);
 // A shared 2D camera effect keeps terrain and contacts attached during the
 // authored close-up. It does not model a flight path or navigation command.
 const approach=state==='ZOOM',progress=Math.min(1,Math.max(0,phase/10));
 const magnification=approach?96**(progress**profile.zoomPower):1;
 const focusX=31.5-(6+pitch)*sinBank,focusY=28.5+(6+pitch)*cosBank;
 const centreEase=approach?progress*progress*(3-2*progress):0;
 const viewX=focusX+(31.5-focusX)*centreEase,viewY=focusY+(28.5-focusY)*centreEase;
 const terrainTime=approach?attitudeTime:t;
 if(world)rgba.set(world.frame.subarray(8*64*4,50*64*4),8*64*4);
 else for(let y=8;y<50;y++)for(let x=0;x<64;x++){
  const dx=(approach?focusX+(x-viewX)/magnification:x)-31.5,dy=(approach?focusY+(y-viewY)/magnification:y)-28.5;
  const u=dx*cosBank+dy*sinBank,v=-dx*sinBank+dy*cosBank-pitch;
  let c=p.bg;
  if(v>0){
   c=p.low;
   // Inverse perspective makes rectangular world patches appear trapezoidal.
   // A near-horizon exclusion avoids subpixel texture shimmer.
   if(v>5){
    const depth=110/v,wx=u*depth/3.5+index*9+(camera?.variant??variant)*13,wz=depth*10-terrainTime*fly*5;
    const gx=((wx%30)+30)%30,gz=((wz%28)+28)%28;
    const cellx=Math.floor(wx/30),cellz=Math.floor(wz/28);
    const hash=((cellx*7+cellz*11)%5+5)%5;
    if(hash>1&&gx>5&&gx<23&&gz>5&&gz<21)c=p.edge;
   }
  }
  if(Math.abs(v)<.55)c=p.accent;
  if(thermal){
   let heat=heatColors[c]??64;
   if(sensor==='blackhot')heat=255-heat;
   c='#'+heat.toString(16).padStart(2,'0').repeat(3);
  }else if(sensor==='cam')c=daylightColors[c]??c;
  pixel(x,y,c);
 }
 // Two short pitch rungs rotate with the horizon. Reticle stays screen-fixed.
 function attitudePoint(u,v){
  v+=pitch;const x=31.5+u*cosBank-v*sinBank,y=28.5+u*sinBank+v*cosBank;
  return approach?[viewX+(x-focusX)*magnification,viewY+(y-focusY)*magnification]:[x,y];
 }
 // People are single pixels at survey scale; the close-up enlarges them with
 // the ground. Keep partial contacts visible at the camera's clipping edges.
 // Queue contacts until after HUD geometry so their identity colour stays visible.
 const contacts=[];
 function groundGroup(u,v,kind='unknown',count=3){
  const offsets=[[0,0],[-3,2],[3,2],[0,4]];
  for(const [du,dv] of offsets.slice(0,count)){
   const [px,py]=attitudePoint(u+du,v+dv),x=Math.round(px),y=Math.round(py);
   const size=approach?Math.max(1,Math.round(magnification)):1,half=size/2;
   const visible=approach?x+half>=0&&x-half<64&&y+half>=8&&y-half<50:x>=5&&x<=58&&y>=10&&y<=41;
   if(observationsEnabled&&visible)contacts.push({x,y,kind,size});
  }
  return attitudePoint(u,v).map(Math.round);
 }
 for(const v of [-8,8])for(const side of [-1,1]){
  const a=attitudePoint(side*8,v),b=attitudePoint(side*14,v);
  if(v<0)line(...a,...b,p.dim);
  else for(let u=8;u<=14;u+=3)pixel(...attitudePoint(side*u,v),p.dim);
 }
 if(observationsEnabled&&['SCAN','LOITER','SEEN','CHECK','DOUBT','FRIEND','TARGET','SHARE','ENGAGE','ZOOM'].includes(state)){
  groundGroup(-15+Math.sin(t*.25+index)*2,6,'unknown',2);
  groundGroup(15+Math.sin(t*.25+index+2)*2,7,'unknown',3);
 }
 const cx=32,cy=30,gap=state==='SCAN'||state==='LOST'?5+Math.round((Math.sin(t*1.8)+1)*2):state==='ENGAGE'?Math.max(2,7-Math.floor(motionPhase*4)):5;
 const cross=['DOUBT','ENGAGE','LOST'].includes(state)?p.warn:p.ink;
 line(cx-gap-4,cy,cx-gap,cy,cross);line(cx+gap,cy,cx+gap+4,cy,cross);line(cx,cy-gap-4,cx,cy-gap,cross);line(cx,cy+gap,cx,cy+gap+4,cross);pixel(cx,cy,p.ink);
 if(state==='SCAN'){
  const sweep=9+Math.floor((t*(4+profile.speed*2))%40);
  if(variant%2)for(let y=12;y<46;y+=3)pixel(sweep+6,y,p.dim);
  else for(let x=8;x<57;x+=3)pixel(x,sweep,p.dim);
 }
 let confirmed=null;
 if(['SEEN','SHARE','CHECK','DOUBT','ENGAGE','ZOOM','TARGET'].includes(state)){
  const centred=state==='ZOOM'||state==='ENGAGE';
  const [bx,by]=groundGroup(centred?0:Math.sin(t*.55*profile.rate+index)*profile.targetX,6,['ENGAGE','ZOOM','TARGET'].includes(state)?'target':'unknown',3);
  const radius=state==='ENGAGE'?Math.max(5,11-Math.floor(motionPhase*4)):approach?Math.min(96,Math.round(7*magnification)):7;
  if(['ENGAGE','ZOOM','TARGET'].includes(state))confirmed={x:bx,y:by,radius};
  else corners(bx,by,radius,state==='CHECK'?p.warn:p.accent);
  if(state==='CHECK')text(51,12,'?',p.warn);
  if(state==='DOUBT'){corners(variant%2?47:15,19+Math.round(Math.sin(t*.5)*profile.targetY),5,p.conflict,true);text(48,12,'?',p.conflict);}
 }
 if(['ALERT','PRIORITY','CLAIM','ASSIGN','YIELD'].includes(state)){
  const [bx,by]=groundGroup(Math.sin(t*.5*profile.rate)*profile.targetX*.45,6,'unknown',3);
  const primary=state==='YIELD'?p.dim:p.warn;
  corners(bx,by,6,primary,state==='CLAIM'||state==='YIELD');
  rect(2,10,12,7,p.bg);text(3,11,'P1',primary);
  if(state==='PRIORITY'){
   corners(51,40,4,p.dim,true);rect(48,11,13,7,p.bg);text(49,12,'P2',p.dim);
   line(15,13,21,13,p.warn);line(19,11,21,13,p.warn);line(19,15,21,13,p.warn);
  }
  if(state==='ALERT'){const radius=8+Math.floor((motionPhase%1)*6);corners(bx,by,radius,p.warn,true);}
  if(state==='CLAIM'){corners(bx,by,9+Math.round(Math.sin(motionPhase*4)),p.conflict,true);}
  if(state==='ASSIGN'){line(bx-3,by,bx,by+3,p.accent);line(bx,by+3,bx+5,by-3,p.accent);}
  if(state==='YIELD'){line(bx-4,by-4,bx+4,by+4,p.dim);}
 }
 if(state==='LOST'){const travel=Math.min(motionPhase,2)*(16+profile.speed*4),[x,y]=motionPhase<2?groundGroup(Math.cos(profile.exit)*travel,6,'unknown',1):attitudePoint(Math.cos(profile.exit)*travel,6).map(Math.round);if(motionPhase<2){corners(x,y,5,p.warn,true);}else corners(Math.max(7,Math.min(56,x)),Math.max(14,Math.min(43,y)),5,p.dim,true);}
 if(state==='LOITER'){
  const path=variant%2?[[16,18],[48,18],[48,26],[16,26],[16,34],[48,34],[48,42],[16,42],[16,18]]:[[21,18],[43,18],[49,29],[43,41],[21,41],[15,29],[21,18]];
  for(let i=1;i<path.length;i++)line(...path[i-1],...path[i],p.dim);
  const progress=((phase%8)+8)%8/8*(path.length-1),edge=Math.floor(progress),fraction=progress-edge,a=path[edge],b=path[edge+1];
  const x=a[0]+(b[0]-a[0])*fraction,y=a[1]+(b[1]-a[1])*fraction;
  rect(Math.round(x)-1,Math.round(y)-1,3,3,p.ink);
 }
 if(state==='R2B'||state==='LAND'){
  const y=state==='LAND'?33:29;
  line(24,y,32,y-7,p.accent);line(32,y-7,40,y,p.accent);line(26,y,26,y+9,p.accent);line(38,y,38,y+9,p.accent);line(26,y+9,38,y+9,p.accent);
  if(state==='R2B'){const shift=Math.floor(phase*2)%5;line(30,43-shift,32,41-shift,p.ink);line(32,41-shift,34,43-shift,p.ink);}
 }
 if(sensor==='ir'&&observationsEnabled&&!['CRASH','EMPTY','NOLINK'].includes(state)){
  // A detected optical pulse is a cue, not authenticated friendly identity.
  const pulse=((time%1.5)+1.5)%1.5,on=pulse<.125||(pulse>=.25&&pulse<.375),c=on?'#78dfff':p.dim;
  const x=17+Math.round(Math.sin(t*.3)*3),y=23;
  line(x,y-5,x+5,y,c);line(x+5,y,x,y+5,c);line(x,y+5,x-5,y,c);line(x-5,y,x,y-5,c);
  if(on)groundGroup(-14,6,'unknown',1);
  rect(2,43,25,7,p.bg);text(3,44,'IR CUE',c);
 }
 if(communication?.direction==='TX'&&communicationPulse(communication.age)){
  const k=Math.floor(t*3)%4;for(let i=0;i<=k;i++){line(50+i*2,39-i,52+i*2,41-i,p.accent);line(52+i*2,41-i,50+i*2,43-i,p.accent);}
 }
 // Designation outlines take visual priority over sensor cues and reticles.
 if(confirmed)square(confirmed.x,confirmed.y,confirmed.radius,designationColors.target);
 const friendly=designation?.kind==='friendly'?designation:state==='FRIEND'?{kind:'friendly',x:20,y:28,source:communication?.direction==='RX'?communication.peer:index}:null;
 if(friendly&&!['CRASH','EMPTY','NOLINK','ZOOM'].includes(state)){
  // Fixture coordinates identify a ground patch; project it with the attitude.
  const [fx,fy]=groundGroup(friendly.x-32,6,'friendly',3);
  square(fx,fy,5,designationColors.friendly);
  rect(2,42,40,8,p.bg);text(3,44,'FRIEND '+labelFor(friendly.source),designationColors.friendly);
 }
 for(const {x,y,kind,size} of contacts){
  const i=(Math.max(8,Math.min(49,y))*64+Math.max(0,Math.min(63,x)))*4,luma=.2126*rgba[i]+.7152*rgba[i+1]+.0722*rgba[i+2];
  const contrast=sensor==='whitehot'?'#ffffff':sensor==='blackhot'?'#000000':luma>127?'#000000':'#ffffff';
  const colour=designationColors[kind]??contrast;
  const left=x-Math.floor(size/2),top=y-Math.floor(size/2);
  for(let yy=Math.max(8,top);yy<Math.min(50,top+size);yy++)
   for(let xx=Math.max(0,left);xx<Math.min(64,left+size);xx++)pixel(xx,yy,colour);
 }
 // Roll only the camera region; identity and status remain upright.
 if(event.roll&&!world){const source=rgba.slice(),cos=Math.cos(event.roll),sin=Math.sin(event.roll);for(let y=8;y<50;y++)for(let x=0;x<64;x++){
  const dx=x-31.5,dy=y-28.5,sx=Math.round(31.5+dx*cos+dy*sin),sy=Math.round(28.5-dx*sin+dy*cos);
  if(sx<0||sx>63||sy<8||sy>49)pixel(x,y,p.bg);
  else for(let c=0;c<3;c++)rgba[(y*64+x)*4+c]=source[(sy*64+sx)*4+c];
 }}
 // As the camera reaches the dirt, the ground occludes the whole image.
 // Stable multiscale grains keep the final held frame textured, not flat sky.
 if(crashProgress>.75){
  const blend=Math.min(1,(crashProgress-.75)*4),mix=blend*blend*(3-2*blend);
  const soil=sensor==='cam'?['#33271b','#493725','#60472e','#795b3b','#99754d']:
   thermal?[40,62,84,106,128].map(v=>'#'+(sensor==='blackhot'?255-v:v).toString(16).padStart(2,'0').repeat(3)):
   [p.bg,p.ground,p.low,p.building,p.edge];
  for(let y=8;y<50;y++)for(let x=0;x<64;x++){
   const gx=Math.floor((x+variant*3)/3),gy=Math.floor((y+index*2)/3);
   let seed=(Math.imul(gx+1,73856093)^Math.imul(gy+1,19349663)^Math.imul(variant+index+1,83492791))>>>0;
   seed=Math.imul(seed^(seed>>>16),0x45d9f3b)>>>0;seed=(seed^(seed>>>16))>>>0;
   const speck=(Math.imul(x+1,0x45d9f3b)^Math.imul(y+1,0x27d4eb2d))>>>0;
   const grain=((speck^(speck>>>16))>>>0)%19===0?1:0,colour=soil[(seed%4+grain)%5],offset=(y*64+x)*4;
   const old=rgba.slice(offset,offset+3);pixel(x,y,colour);
   for(let c=0;c<3;c++)rgba[offset+c]=Math.round(old[c]*(1-mix)+rgba[offset+c]*mix);
  }
 }
 if(event.dim<1)for(let y=8;y<50;y++)for(let x=0;x<64;x++)for(let c=0;c<3;c++)rgba[(y*64+x)*4+c]*=event.dim;
 if(state==='NOLINK'){rect(14,25,36,9,p.bg);text(18,27,'NO LINK',p.warn);}
 // Solid bands keep labels legible regardless of scene motion.
 rect(0,0,64,8,p.bg);text(2,1,labelFor(index),p.ink);text(21,1,sensor==='cam'?'TV':sensor==='whitehot'?'WH':sensor==='blackhot'?'BH':sensor==='ir'?'IR':'NV',p.dim);text(33,1,String(heading).padStart(3,'0'),p.dim);text(50,1,distanceLabel(readouts?.distanceKm),p.accent);line(1,7,62,7,p.dim);
 const arrow=northArrow(heading),point=([x,y])=>[14+x,3+y];
 line(...point(arrow.tail),...point(arrow.tip),p.ink);line(...point(arrow.left),...point(arrow.tip),p.ink);line(...point(arrow.right),...point(arrow.tip),p.ink);
 const status=stateLabel(state);
 rect(0,50,64,14,p.bg);line(1,50,62,50,p.dim);text(2,52,status,state==='DOUBT'?p.conflict:['CHECK','ENGAGE','LOST','CRASH','EMPTY','NOLINK'].includes(state)?p.warn:p.ink);
 // Return readout is an explicit input; it does not drive mission decisions.
 const reserve=returnLabel(readouts?.returnSeconds);
 text(38,52,reserve,reserve==='BINGO'?p.warn:p.dim);
 // Battery represents simulated energy, independently of link state.
 rect(52,58,9,5,event.battery?p.dim:p.warn);rect(53,59,7,3,p.bg);rect(53,59,event.battery,3,p.accent);rect(61,59,1,3,event.battery?p.dim:p.warn);
 let detail='ALT '+String(world?Math.round(world.pose.position[2]):camera?.altitude??(40+index%5*3+Math.round(Math.sin(t*.2)*2)));
 if(state==='DEPLOY')detail='FORM UP';
 if(state==='LOITER')detail=variant%2?'GRID':'ORBIT';if(state==='R2B')detail='HOME';if(state==='LAND')detail='ALT '+Math.round(world?.pose.position[2]??(camera?.landingAltitude??40)*launch);
 if(state==='HOLD')detail='HQ WAIT';if(state==='SHARE')detail='REPORT';if(state==='CHECK')detail='VERIFY';if(state==='DOUBT')detail='2 CLAIMS';
 if(state==='FRIEND')detail='WARN ALL';if(state==='TARGET')detail='CONFIRMED';
 if(state==='ENGAGE')detail='SIM EVENT';if(state==='LOST')detail='SEARCH';if(state==='ZOOM')detail='00:'+String(Math.max(0,Math.ceil(10-phase))).padStart(2,'0');if(state==='CRASH')detail=event.grounded?'GROUND':'TUMBLE';if(state==='EMPTY')detail='BAT '+Math.round(event.battery*20);if(state==='NOLINK')detail='AGE '+Math.floor(phase)+'S';
 const owner=coordination?.owner??5;
 if(state==='ALERT')detail='BEACON P1';if(state==='PRIORITY')detail='P1 FIRST';if(state==='CLAIM')detail='CLAIM P1';
 if(state==='ASSIGN'||state==='YIELD')detail='OWNER '+labelFor(owner);
 if(!event.approach&&communication&&communication.age>=0&&communication.age<.625&&communicationColors[communication.direction])detail=communication.direction+' '+peerLabel(communication.peer);
 text(2,58,detail,p.dim);border();return rgba;
}
