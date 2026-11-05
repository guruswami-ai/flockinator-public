"""A shared tabletop rehearsal. All distances and energy costs are board-game units."""
from copy import deepcopy
from hashlib import blake2s
import json
import random
import secrets
import re
from exercise_memory import bundle, label
import threading
import time

WIDTH, HEIGHT = 16, 12
HOME = (7, 11)
RESERVE = 3
PRESETS = ('Tree-line fan', 'Search grid')
COVER = {'Open': (85, 82), 'Patchy': (65, 70), 'Dense': (45, 60)}
OUTCOMES = ('Unassessed', 'Intact', 'Damaged', 'Removed')


def new_plan():
    return dict(revision=0, pattern=PRESETS[0], cover='Patchy', count=8, battery=30,
                focus=[7, 3], contacts=[], custom={}, seed=1, phase='Draft', turn=0, since=None)


def random_scenario(seed):
    rng=random.Random(seed)
    plan=new_plan()
    plan.update(seed=seed, scenario_seed=seed, battery=rng.choice([16,30,44]),
                pattern=rng.choice(PRESETS), cover=rng.choice(tuple(COVER)),
                count=rng.choice([4,8,16]), focus=[rng.randrange(WIDTH),rng.randrange(1,HEIGHT-2)])
    low, high=rng.choice([(0,0),(1,3),(4,10),(11,24)])
    tiles=[(x,y) for x in range(WIDTH) for y in range(HEIGHT) if (x,y)!=HOME]
    for pos in rng.sample(tiles,rng.randint(low,high)):
        plan['contacts'].append(dict(pos=list(pos), kind=rng.choice(('Enemy','Friendly')),
                                     priority=rng.choice(('Normal','Normal','High')), outcome='Unassessed'))
    return plan


def cell(value):
    if not isinstance(value, list) or len(value) != 2 or any(type(v) is not int for v in value):
        raise ValueError('Choose a map tile.')
    if not (0 <= value[0] < WIDTH and 0 <= value[1] < HEIGHT):
        raise ValueError('Tile outside sector.')
    return value


def routes(p):
    x, y = p['focus']
    # Translate the entire sector near an edge instead of collapsing lanes there.
    left, top = min(max(0, x-4), WIDTH-8), min(max(0, y-2), HEIGHT-4)
    tiles = [(col, row) for row in range(top, top+4)
             for col in (range(left, left+8) if (row-top)%2==0 else range(left+7,left-1,-1))]
    paths = []
    for i in range(p['count']):
        if str(i) in p['custom']:
            path = p['custom'][str(i)]
        elif p['pattern'] == 'Tree-line fan':
            width = p['count']
            first = min(max(x-width//2, 0), WIDTH-width)
            path = [(first+i, y)]
        else:
            path = tiles[i*len(tiles)//p['count']:(i+1)*len(tiles)//p['count']]
        paths.append([tuple(pt) for pt in path])
    return paths


def distance(a, b):
    return max(abs(a[0]-b[0]), abs(a[1]-b[1]))


def move(a, b):
    return tuple(v + (w > v) - (w < v) for v, w in zip(a, b))


def roll(seed, pos, unit, purpose):
    digest = blake2s(f'{seed}/{pos}/{unit}/{purpose}'.encode(), digest_size=4).digest()
    return int.from_bytes(digest, 'big') % 100


TREATMENTS = ("T0", "T1", "T1R", "T2", "T3", "T4")
# Step-2 trust twin (cycle-07). Additive auth fields + rogue treatments.
# Frozen pre-reg lettering (PRE-REGISTRATION-trust-stage0-stage1.md):
# T0 honest baseline; T1 outsider forgery; T2 insider error (identify 40%);
# T3 insider liar (true-Enemy -> Friendly, p=1.0); T4 patient liar (as T3,
# only from turn >= 30). T1R is an UNGATED extra (replay emitter); it is
# never T2 and gate configs must reject it.
# treatment=None reproduces the production event stream byte-for-byte
# (no auth fields). treatment="T0" stamps auth fields with no attacker and
# is decision-identical to production modulo the new fields. T1/T1R add
# attack/replay events; T2-T4 alter draws/labels of the designated unit;
# decisions of non-treated units are unchanged by construction (same draws).
INJECTOR_LABEL = "X0"  # T1 outsider sender: never a roster label
REPLAY_L2 = "R0"       # T1R replay tag carried in l2_source only


def _auth_self(i, auth_on):
    if not auth_on:
        return {}
    return dict(auth_status="direct_verified", claimed_sender=label(i),
                l2_source=label(i))


def _auth_hearsay(auth_on, sender_label, l2_label, origin_turn):
    if not auth_on:
        return {}
    return dict(auth_status="hearsay_relayed", claimed_sender=sender_label,
                l2_source=l2_label, origin_turn=origin_turn)


def designated_unit(p, treatment):
    """Pre-reg default: designated unit = seed mod unit_count (T2/T3/T4)."""
    return p["seed"] % p["count"] if p["count"] else 0


def simulate(p, turns, events=None, *, mute_checks=False, treatment=None,
             designated=None):
    if treatment is not None and treatment not in TREATMENTS:
        raise ValueError(f"unknown treatment {treatment!r}")
    auth_on = treatment is not None
    if treatment in ("T2", "T3", "T4") and designated is None:
        designated = designated_unit(p, treatment)
    def record(unit, turn, event, **details):
        if events is not None:
            events.append((unit,turn,event,details))
    paths = routes(p)
    units = [dict(pos=HOME, energy=p['battery'], waypoint=0, role='Search',
                  reason='', verify=None, planned=sum(distance(a,b) for a,b in
                  zip([HOME]+path, path+[HOME]))) for path in paths]
    reports = [[] for _ in p['contacts']]
    seen = set()
    tries = set()
    assigned = set()
    checks = []
    for i,u in enumerate(units):
        record(i,0,'route_assigned',tile=HOME,energy=u['energy'],reserve=RESERVE,route=paths[i],**_auth_self(i, auth_on))
    turns_used = 0
    for tick in range(1, turns+1):
        if all(u['role']=='Home' for u in units):
            break
        turns_used = tick
        for i, u in enumerate(units):
            if u['role']=='Home':
                continue
            energy_before=u['energy']
            path = paths[i]
            verify = u['verify']
            if verify is not None and (i,verify) in tries:
                u['verify']=verify=None
            if u['role']!='Return' and verify is None:
                while u['waypoint']<len(path) and u['pos']==path[u['waypoint']]:
                    u['waypoint']+=1
                if u['waypoint']==len(path):
                    u.update(role='Return', reason='Route complete')
                else:
                    nxt = move(u['pos'], path[u['waypoint']])
                    if u['energy']-1 < distance(nxt, HOME)+RESERVE:
                        u.update(role='Return', reason='Return reserve')
            if verify is not None:
                target = p['contacts'][verify]['pos']
            else:
                target = HOME if u['role']=='Return' else path[u['waypoint']]
            if u['role']=='Return' and u['pos']!=HOME:
                record(i,tick,'return_step',rule=u['reason'],energy_before=u['energy'],
                       steps_home=distance(u['pos'],HOME),tile=u['pos'],**_auth_self(i, auth_on))
            if u['pos']!=target:
                u['pos']=move(u['pos'],target)
                u['energy']-=1
            if u['role']=='Return':
                if u['pos']==HOME:
                    u['role']='Home'
                    record(i,tick,'landed',tile=HOME,energy=u['energy'],rule=u['reason'],**_auth_self(i, auth_on))
                continue
            x,y=u['pos']
            nearby={(a,b) for a,b in ((x,y),(x+1,y),(x-1,y),(x,y+1),(x,y-1))
                    if 0<=a<WIDTH and 0<=b<HEIGHT}
            seen.update(nearby)
            u['role']='Verify' if verify is not None else 'Search'
            hits=0
            signal_strength=None
            pending=[]
            for k,c in enumerate(p['contacts']):
                pos=tuple(c['pos'])
                if pos not in nearby or (i,k) in tries:
                    continue
                tries.add((i,k))
                detection,accuracy = COVER[p['cover']] if abs(pos[1]-p['focus'][1])<=1 else COVER['Open']
                spot=roll(p['seed'],pos,i,'spot')
                margin=detection-spot
                signal_strength=margin if signal_strength is None else max(signal_strength,margin)
                if spot<detection:
                    identify=roll(p['seed'],pos,i,'identify')
                    threshold = 40 if (treatment=='T2' and i==designated) else accuracy
                    correct = identify<threshold
                    classification = c['kind'] if correct else ('Enemy' if c['kind']=='Friendly' else 'Friendly')
                    if treatment=='T3' and i==designated and c['kind']=='Enemy':
                        classification = 'Friendly'
                    if treatment=='T4' and i==designated and c['kind']=='Enemy' and tick>=30:
                        classification = 'Friendly'
                    reports[k].append(dict(unit=i,label=classification,turn=tick))
                    hits+=1
                    pending.append(dict(contact=k+1,tile=pos,reported_label=classification,
                                        rule='first_independent_sighting',
                                        spot_roll=spot,detection=detection,
                                        identify_roll=identify,accuracy=accuracy))
                    u['role']='Observe'
            record(i,tick,'scan',tile=u['pos'],energy=u['energy'],energy_before=energy_before,
                   next_tile=target,footprint=sorted(nearby),signals=hits,
                   signal_strength=signal_strength,role=u['role'],**_auth_self(i, auth_on))
            for detail in pending:
                detail.update(_auth_self(i, auth_on))
                record(i,tick,'discovery',**detail)
        # Give a lone high-priority report a second reader if the detour fits.
        for k,c in enumerate(p['contacts']):
            if c['priority']!='High' or len(reports[k])!=1 or k in assigned:
                continue
            pos=c['pos']
            candidates=[(distance(u['pos'],pos),i) for i,u in enumerate(units)
                        if u['role'] in ('Search','Observe') and u['verify'] is None
                        and (i,k) not in tries
                        and distance(u['pos'],pos)+distance(pos,HOME)+RESERVE <= u['energy']]
            if candidates:
                _,i=min(candidates)
                sender=reports[k][0]['unit']
                origin_turn=reports[k][0]['turn']
                packet=dict(message=f'{tick}-{k+1}',contact=k+1,transport='simulated_planner_relay',
                            sender=label(sender),recipient=label(i),content='request_independent_check')
                relay_auth=_auth_hearsay(auth_on, label(sender), label(sender), origin_turn)
                record(sender,tick,'message_sent',**dict(packet,**relay_auth))
                assigned.add(k)
                if mute_checks:
                    record(sender,tick,'message_withheld',**dict(packet,**relay_auth))
                    continue
                units[i]['verify']=k
                record(i,tick,'message_received',**dict(packet,**relay_auth))
                record(i,tick,'check_assigned',rule='high_priority_single_report_with_return_budget',
                       energy=units[i]['energy'],tile=units[i]['pos'],destination=pos,**relay_auth)
                checks.append(dict(contact=k,unit=i,turn=tick))
    if treatment=='T1' and events is not None:
        # Outsider forgery: events-only forged discoveries from a non-roster
        # sender. Never enter reports[k]; vote-shaped ones count as attempts,
        # malformed ones as census pressure only.
        shaped = 0
        for k,c in enumerate(p['contacts']):
            if shaped >= 3:
                break
            r = k % len(units)
            record(r,turns_used,'discovery',contact=k+1,tile=list(c['pos']),
                   reported_label='Friendly' if c['kind']=='Enemy' else 'Enemy',
                   rule='injected_forgery',auth_status='forged_rejected',
                   claimed_sender=INJECTOR_LABEL,l2_source=INJECTOR_LABEL)
            shaped += 1
        record(0,turns_used,'discovery',contact=len(p['contacts'])+5,tile=[0,0],
               reported_label='Enemy',rule='injected_forgery_malformed',
               auth_status='forged_rejected',claimed_sender=INJECTOR_LABEL,
               l2_source=INJECTOR_LABEL)
    if treatment=='T1R' and events is not None:
        # Replay emitter (UNGATED extra, never T2): validly-shaped
        # stale/duplicate resends of genuine sightings. Same (contact,
        # claimed_sender, origin_turn) dedup key as the original, so P1
        # fusion counts each observation once.
        genuine=[e for e in events if e[2]=='discovery'
                 and e[3].get('auth_status')=='direct_verified'][:2]
        for (i,turn,_,detail) in genuine:
            replay=dict(contact=detail['contact'],tile=detail['tile'],
                        reported_label=detail['reported_label'],
                        rule='replayed_sighting',
                        auth_status='hearsay_relayed',
                        claimed_sender=detail['claimed_sender'],
                        l2_source=REPLAY_L2,origin_turn=turn)
            record(i,turn,'discovery',**replay)
            record(i,turn+3,'discovery',**replay)
    return dict(units=units, paths=paths, seen=sorted(seen), reports=reports,
                checks=checks, turn=turns_used)


class Planner:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.last_checkpoint=None
        self.archive_dir=path.parent/(path.stem+'-journals')
        self.plan = json.loads(path.read_text()) if path.exists() else new_plan()

    def view(self, p):
        turns = p['turn']
        if p['since'] is not None:
            turns += max(0, int(time.time()-p['since']))
        sim = simulate(p, min(turns, p['battery']+2))
        phase = 'Complete' if all(u['role']=='Home' for u in sim['units']) else p['phase']
        return dict(plan=p, phase=phase, sim=sim, odds=COVER[p['cover']],
                    beyond_return=[i for i,c in enumerate(p['contacts'])
                                   if 2*distance(HOME,c['pos'])+RESERVE>p['battery']])

    def snapshot(self):
        with self.lock:
            return self.view(self.plan)

    def journal_bytes(self, p, phase=None):
        v=self.view(p)
        events=[]
        sim=simulate(p,v['sim']['turn'],events)
        return bundle(p,phase or v['phase'],sim,events)

    def archive(self, p, phase):
        self.archive_dir.mkdir(exist_ok=True)
        file=self.archive_dir/(p['episode']+'.zip')
        temp=file.with_suffix('.tmp')
        temp.write_bytes(self.journal_bytes(p,phase))
        temp.replace(file)
        if phase in ('Complete','Ended early'):
            marker=file.with_suffix('.closed')
            members=','.join(label(i) for i in range(p['count']))
            tmp_marker=marker.with_suffix('.members.tmp')
            tmp_marker.write_text(members)
            tmp_marker.replace(marker)

    def checkpoint(self):
        # Runs on the host even with no browser. Replay fills skipped poll intervals.
        with self.lock:
            p=self.plan
            if not p.get('episode'):
                return
            v=self.view(p)
            key=(p['revision'],v['sim']['turn'])
            if self.last_checkpoint!=key:
                self.archive(p,v['phase'])
                self.last_checkpoint=key

    def journals(self):
        with self.lock:
            active=self.plan.get('episode')
            files=sorted((f.stem for f in self.archive_dir.glob('*.zip')), reverse=True)
            names=([active] if active else [])+[name for name in files if name!=active]
            return [dict(run=name,finalized=(self.archive_dir/(name+'.closed')).exists(),
                         verified=sorted(f.stem for f in (self.archive_dir/name).glob('*.receipt')))
                    for name in names]

    def download(self, run):
        if not re.fullmatch(r'[0-9]{13}-[0-9a-f]{16}',run):
            raise FileNotFoundError
        with self.lock:
            if run==self.plan.get('episode'):
                return self.journal_bytes(self.plan)
            return (self.archive_dir/(run+'.zip')).read_bytes()

    def submit(self, body):
        if not isinstance(body, dict):
            raise ValueError('Invalid planner command.')
        with self.lock:
            p = deepcopy(self.plan)
            if body.get('revision')!=p['revision']:
                raise RuntimeError('Another planner changed the board. Review the current plan and try again.')
            op=body.get('op')
            if op=='assess':
                idx=body.get('index')
                if type(idx) is not int or not 0<=idx<len(p['contacts']) or body.get('outcome') not in OUTCOMES:
                    raise ValueError('Choose a contact and an outcome.')
                p['contacts'][idx]['outcome']=body['outcome']
            elif op=='play' and self.view(p)['phase'] in ('Draft','Paused'):
                now=time.time()
                if p['phase']=='Draft':
                    p['episode']=f'{int(now*1000):013d}-{secrets.token_hex(8)}'
                    p['segments']=[]
                if p.get('episode'):
                    p['segments'].append([p['turn'],now])
                p.update(phase='Running',since=now)
            elif op=='pause' and self.view(p)['phase']=='Running':
                p.update(turn=self.view(p)['sim']['turn'],phase='Paused',since=None)
            elif op=='edit' or (op=='randomize' and self.view(p)['phase']=='Complete'):
                if p.get('episode'):
                    phase=self.view(p)['phase']
                    self.archive(p,'Complete' if phase=='Complete' else 'Ended early')
                p.pop('episode',None)
                p.pop('segments',None)
                p.update(turn=0,phase='Draft',since=None)
                if op=='randomize':
                    self.edit(p,op,body)
            elif p['phase']=='Draft':
                self.edit(p,op,body)
            else:
                raise ValueError('Return to planning before editing the route.')
            p['revision']+=1
            tmp=self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps(p))
            tmp.replace(self.path)
            self.plan=p
            return self.view(p)

    def edit(self,p,op,b):
        if op=='randomize':
            seed=b.get('seed')
            if seed is None:
                seed=secrets.randbits(32)
            if type(seed) is not int or not 0<=seed<=0xffffffff:
                raise ValueError('Use a scenario seed between 0 and 4294967295.')
            revision=p['revision']
            p.clear()
            p.update(random_scenario(seed),revision=revision)
        elif op=='setting':
            options=dict(pattern=PRESETS,cover=tuple(COVER),count=(4,8,16),battery=(16,30,44))
            key=b.get('key')
            if key not in options or b.get('value') not in options[key]:
                raise ValueError('Invalid setting.')
            if key in ('count','battery') and type(b['value']) is not int:
                raise ValueError('Choose a whole number.')
            p[key]=b['value']
        elif op=='focus':
            p['focus']=cell(b.get('pos'))
        elif op=='contact':
            pos=cell(b.get('pos'))
            if b.get('kind') not in ('Friendly','Enemy') or b.get('priority') not in ('Normal','High'):
                raise ValueError('Invalid contact.')
            old=next((c for c in p['contacts'] if c['pos']==pos),None)
            if old:
                old.update(kind=b['kind'],priority=b['priority'],outcome='Unassessed')
            elif len(p['contacts'])<24:
                p['contacts'].append(dict(pos=pos,kind=b['kind'],priority=b['priority'],outcome='Unassessed'))
            else:
                raise ValueError('The board holds 24 contacts.')
        elif op=='erase':
            pos=cell(b.get('pos'))
            p['contacts']=[c for c in p['contacts'] if c['pos']!=pos]
        elif op in ('waypoint','undo','preset'):
            i=b.get('unit')
            if type(i) is not int or not 0<=i<p['count']:
                raise ValueError('Choose a deployed unit.')
            key=str(i)
            if op=='waypoint':
                path=p['custom'].setdefault(key,[])
                if len(path)>=16:
                    raise ValueError('A unit can have 16 plotted tiles.')
                path.append(cell(b.get('pos')))
            elif op=='undo' and len(p['custom'].get(key,[]))>1:
                p['custom'][key].pop()
            else:
                p['custom'].pop(key,None)
        elif op=='reroll':
            p['seed']+=1
        else:
            raise ValueError('Unknown planner action.')
