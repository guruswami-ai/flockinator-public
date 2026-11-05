import io, json, sys, zipfile
sys.path.insert(0, 'tools/mission-host')          # production
import planner as prod, exercise_memory as prod_mem
sys.path.insert(0, '/tmp/cycle07-twins')          # twin first
import importlib
sys.path = ['/tmp/cycle07-twins', 'tools/mission-host']
if 'planner' in sys.modules: del sys.modules['planner']
import planner as twin
sys.path.remove('/tmp/cycle07-twins')
import exercise_memory as mem  # production bundle (shared, unmodified)
EPOCH = 1700000000.0
AUTH_KEYS = {'auth_status','claimed_sender','l2_source','origin_turn'}
def build(mod, seed, treatment):
    p = mod.random_scenario(seed)
    p.update(episode=f'identity-seed-{seed}', segments=[[0, EPOCH]],
             revision=0, turn=0, phase='Running', since=EPOCH)
    kw = {} if mod is prod else dict(treatment=treatment)
    ev = []
    sim = mod.simulate(p, 46, ev, **kw)
    # second pass like baseline.py: rerun to sim turn with events
    ev2 = []
    sim2 = mod.simulate(p, sim['turn'], ev2, **kw)
    blob = mem.bundle(p, 'Complete', sim2, ev2)
    return sim2, ev2, blob
for seed in (0, 1):
    ps, es, bs = build(prod, seed, None)
    # None path: byte-identical bundle
    tn, en, bn = build(twin, seed, None)
    print(f'seed {seed}: None==prod bytes:', bn == bs, f'({len(bs)} B)')
    # T0 path: decisions identical, only additive auth keys differ
    t0, e0, b0 = build(twin, seed, 'T0')
    # sim decisions compare (strip nothing: sim has no auth fields)
    js = json.dumps(ps, sort_keys=True); jt = json.dumps(t0, sort_keys=True)
    print(f'seed {seed}: T0 sim==prod sim:', js == jt)
    # events compare modulo AUTH_KEYS
    def strip(ev):
        return sorted((i, t, e, sorted((k, json.dumps(v, sort_keys=True))
                      for k, v in d.items() if k not in AUTH_KEYS)) for i, t, e, d in ev)
    print(f'seed {seed}: T0 events==prod modulo auth:', strip(e0) == strip(es),
          f'n={len(es)}/{len(e0)}')
    # every T0 discovery/message carries the pinned fields
    bad = [e for e in e0 if e[2] in ('discovery','message_sent','message_received','check_assigned')
           and not (e[3].get('auth_status') in ('direct_verified','hearsay_relayed')
                    and 'claimed_sender' in e[3] and 'l2_source' in e[3])]
    print(f'seed {seed}: pinned fields on all discovery/message events:', not bad, f'(checked {sum(1 for e in e0 if e[2] in ("discovery","message_sent","message_received","check_assigned"))})')
