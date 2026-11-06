<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

# Controller Sim Core — 16-Robot Prototype (simulated data only)

Pre-registered, seeded simulation. No hardware / human data. Fixed seeds. Falsification: any non-determinism, `len(snapshot)!=392`, or float usage fails the run. Logical time: **10 ticks/s**.

## 1. State layout

World bounds: `[-2000,2000]` dm (±200 m). All `int`.

```text
World: tick:u32, surv_x:i16, surv_y:i16, robots[16] in id order 0..15
Robot internal:
  id:u8, mode:u8(0 idle,1 search,2 return,3 assist)
  x,y:i16 dm, vx,vy:i16 dm/s, heading:u16 decideg 0..3599 (0=E, CCW)
  battery:u8 0..100, sensor:u8, flags:u8 (bit0 wall, bit1 survivor-seen)
  acc_x,acc_y:int -9..9 (sub-dm residue, NOT transmitted)
  ix,iy:i16 last clamped intent
Intent in per tick per robot: (vx,vy:i16 dm/s, mode:u8, sensor:u8)
```

Constants: `VMAX=30 dm/s, ACC=10, DVMAX=6, TURN2=36, DT=0.1s, R_SEEN2=225 (15dm)`

Init `new_world(seed)`: `tick=0`, survivor from `random.Random(seed)` in `[-1000,1000]`, robots on grid `(-750+(i%4)*500, -750+(i//4)*500)`, `v=0, heading=0, battery=100`.

## 2. Step equations (integer only)

Per tick, robots `0..15` in order:

```text
1. ixc=clamp(ix,-VMAX,VMAX), iyc=clamp(iy,-VMAX,VMAX)
2. dvx=clamp(ixc-vx,-ACC,ACC), dvy=clamp(iyc-vy,-ACC,ACC)
3. turn cap: n2=dvx²+dvy²; if n2>TURN2: n=isqrt(n2); dvx=trunc(dvx*DVMAX/n); dvy=trunc(dvy*DVMAX/n)
4. vx+=dvx; vy+=dvy
5. heading: if vx,vy!=0: heading=quantize8(vx,vy)*450  # 8-sector, integer test below
6. integrate: acc_x+=vx; dx=trunc(acc_x/10); acc_x-=dx*10; x=sat16(clamp(x+dx,XMIN,XMAX))
   same for y. If clamped: vx/vy=0 on hit axis, flags|=0x01
7. dist2=(x-sx)²+(y-sy)²; flags survivor bit = 1 if dist2<=225
8. if tick%10==0 and (vx!=0 or vy!=0): battery=max(0,battery-1)
9. tick=(tick+1) mod 2³²
```

`trunc(a/b)`: toward zero: `abs(a)//b * sign(a)`, `b>0`. `sat16`: saturate, never wrap. `quantize8`: `ax=|vx|,ay=|vy|`; if `ay*12<ax*5`: E/W; elif `ax*12<ay*5`: N/S (`y+=N`); else diagonal by signs. No float, no `atan`.

## 3. Determinism rules

* Fixed order `0..15`, single thread, no wall-clock/`sleep`.
* Integer ops only: `+ - * // isqrt`, `clamp`, `trunc`. No `float`, no `hash()`, no dict iteration.
* Canonical little-endian `struct`. Saturation, never overflow-wrap.
* Randomness only via `random.Random(fixed_seed)`. Canonical seeds: `0xC0FFEE, 1, 2`.
* Snapshot residue `acc_x/y` not transmitted; re-simulation only from full `World`, not from snapshot.

## 4. Snapshot codec — 392 B

`8 B header + 16×24 B = 392 B`. LE.

Header: `<Ihh`: `tick:U32, surv_x:I16, surv_y:I16`.
Robot: `<BBhhhhHBBBBhhI` (24 B): `id:B, mode:B, x:h, y:h, vx:h, vy:h, heading:H, batt:B, sens:B, flags:B, rsv:B(0), ix:h, iy:h, tick:I`.

## 5. Prototype (stdlib only)

```python
import struct, math, random
from dataclasses import dataclass, field
VMAX,ACC,DVMAX=30,10,6
TURN2=DVMAX*DVMAX
XMIN=XMAX=YMIN=YMAX=2000
XMIN,YMIN=-2000,-2000
HDR=struct.Struct('<Ihh')
REC=struct.Struct('<BBhhhhHBBBBhhI')
assert HDR.size==8 and REC.size==24

def clamp(v,lo,hi): return lo if v<lo else hi if v>hi else v
def sat16(v): return clamp(v,-32768,32767)
def trunc_div(a,b): return (abs(a)//b)*(1 if a>=0 else -1)  # b>0

@dataclass
class Robot:
    id:int; x:int=0; y:int=0; vx:int=0; vy:int=0
    heading:int=0; mode:int=0; battery:int=100
    sensor:int=0; flags:int=0; accx:int=0; accy:int=0; ix:int=0; iy:int=0
@dataclass
class World:
    tick:int=0; sx:int=0; sy:int=0; robots:list=field(default_factory=list)

def new_world(seed=0xC0FFEE):
    r=random.Random(seed)
    w=World(tick=0,sx=r.randint(-1000,1000),sy=r.randint(-1000,1000))
    for i in range(16):
        w.robots.append(Robot(id=i,x=-750+(i%4)*500,y=-750+(i//4)*500))
    return w

def quantize8(vx,vy):
    ax,ay=abs(vx),abs(vy)
    if ay*12 < ax*5: return 0 if vx>0 else 4
    if ax*12 < ay*5: return 2 if vy>0 else 6
    if vx>0 and vy>0: return 1
    if vx<0 and vy>0: return 3
    if vx<0 and vy<0: return 5
    return 7

def step(w:World,intents):
    # intents: list len 16 of (vx,vy,mode,sensor)
    for rb,(ix0,iy0,md,sn) in zip(w.robots,intents):
        ixc,iyc=clamp(int(ix0),-VMAX,VMAX),clamp(int(iy0),-VMAX,VMAX)
        rb.ix,rb.iy=ixc,iyc
        rb.mode=clamp(int(md),0,3); rb.sensor=int(sn)&0xFF
        dvx=clamp(ixc-rb.vx,-ACC,ACC); dvy=clamp(iyc-rb.vy,-ACC,ACC)
        n2=dvx*dvx+dvy*dvy
        if n2>TURN2:
            n=math.isqrt(n2)
            dvx=trunc_div(dvx*DVMAX,n); dvy=trunc_div(dvy*DVMAX,n)
        rb.vx+=dvx; rb.vy+=dvy
        if rb.vx!=0 or rb.vy!=0: rb.heading=quantize8(rb.vx,rb.vy)*450
        rb.accx+=rb.vx; dx=trunc_div(rb.accx,10); rb.accx-=dx*10
        rb.accy+=rb.vy; dy=trunc_div(rb.accy,10); rb.accy-=dy*10
        nx,ny=rb.x+dx,rb.y+dy
        hit=False
        if nx<XMIN or nx>XMAX: nx=clamp(nx,XMIN,XMAX); rb.vx=0; hit=True
        if ny<YMIN or ny>YMAX: ny=clamp(ny,YMIN,YMAX); rb.vy=0; hit=True
        rb.x,rb.y=sat16(nx),sat16(ny)
        rb.flags=(rb.flags&0x02)|(0x01 if hit else 0x00)
        ddx,ddy=rb.x-w.sx,rb.y-w.sy
        rb.flags=(rb.flags&0x01)|(0x02 if ddx*ddx+ddy*ddy<=225 else 0x00)
        if w.tick%10==0 and (rb.vx!=0 or rb.vy!=0):
            rb.battery=max(0,rb.battery-1)
    w.tick=(w.tick+1)%2**32

def encode(w:World)->bytes:
    b=bytearray(HDR.pack(w.tick,w.sx,w.sy))
    for rb in w.robots:
        b+=REC.pack(rb.id,rb.mode,rb.x,rb.y,rb.vx,rb.vy,rb.heading,
                    rb.battery,rb.sensor,rb.flags,0,rb.ix,rb.iy,w.tick)
    return bytes(b)

def decode(b:bytes)->World:
    assert len(b)==392
    tick,sx,sy=HDR.unpack(b[:8]); w=World(tick,sx,sy,[])
    for i in range(16):
        f=REC.unpack(b[8+i*24:8+(i+1)*24])
        assert f[0]==i
        w.robots.append(Robot(id=f[0],mode=f[1],x=f[2],y=f[3],vx=f[4],vy=f[5],
                              heading=f[6],battery=f[7],sensor=f[8],flags=f[9],ix=f[12],iy=f[13]))
    return w
```

## 6. Unit tests (6)

```python
import unittest
class T(unittest.TestCase):
    def test_len_roundtrip(self):
        w=new_world(1); s=encode(w)
        self.assertEqual(len(s),392)
        d=decode(s); self.assertEqual(encode(d),s)
    def test_deterministic(self):
        def run():
            w=new_world(42)
            for t in range(50):
                step(w,[(t+i)%31-15,(t*2-i)%31-15,i%4,i&0xFF] for i in range(16)))
            return encode(w)
        self.assertEqual(run(),run())
    def test_vmax(self):
        w=new_world(1); step(w,[(100,0,1,0)]*16)
        for _ in range(20): step(w,[(100,0,1,0)]*16)
        self.assertTrue(all(r.vx==30 for r in w.robots))
    def test_turn_cap(self):
        w=new_world(1); w.robots[0].vx=30
        step(w,[(-30,0,1,0)]+[(0,0,0,0)]*15)
        self.assertEqual(w.robots[0].vx,24)  # delta -6
    def test_integration(self):
        w=new_world(1); r=w.robots[0]; r.x=0; r.accx=0
        for _ in range(10): step(w,[(6,0,1,0)]+[(0,0,0,0)]*15)
        self.assertEqual(r.x,6)
    def test_wall(self):
        w=new_world(1); r=w.robots[0]; r.x=XMAX
        step(w,[(30,0,1,0)]+[(0,0,0,0)]*15)
        self.assertEqual((r.x,r.flags&1),(XMAX,1))
if __name__=='__main__': unittest.main()
```
