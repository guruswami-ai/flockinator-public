import sys
sys.path.insert(0, 'tools/mission-host')
sys.path.insert(0, '/tmp/cycle07-twins')
import planner as twin
assert 'cycle07' in twin.__file__, twin.__file__
# Frozen pre-reg lettering: T2 error(40), T3 liar, T4 patient liar(turn>=30).
for seed in (0, 1):
    p = twin.random_scenario(seed)
    base = twin.simulate(p, 46)
    for t in ('T1', 'T1R', 'T2', 'T3', 'T4'):
        ev = []
        s = twin.simulate(p, 46, ev, treatment=t)
        forged = [e for e in ev if e[3].get('auth_status') == 'forged_rejected']
        hear = [e for e in ev if e[3].get('auth_status') == 'hearsay_relayed']
        same = (s['reports'] == base['reports']) if t in ('T1', 'T1R') else 'n/a(liar/error alter labels by design)'
        desig = twin.designated_unit(p, t) if t in ('T2', 'T3', 'T4') else '-'
        print(f'seed {seed} {t}: designated={desig} forged={len(forged)} hearsay={len(hear)} reports_untouched={same} units={len(s["units"])}')
# T4 gate: FORCED flips happen only at turn>=30. Natural mislabels still
# occur, so prove it differentially: early-turn designated-unit labels under
# T4 must equal the untreated (None) run label-for-label.
early_mismatch = []
late_forced = []
for seed in range(20):
    p = twin.random_scenario(seed)
    d = twin.designated_unit(p, 'T4')
    ev0, ev4 = [], []
    twin.simulate(p, 46, ev0, treatment=None, designated=d)
    twin.simulate(p, 46, ev4, treatment='T4', designated=d)
    base = {(e[0], e[1], e[3]['contact']): e[3]['reported_label']
            for e in ev0 if e[2] == 'discovery'}
    for e in ev4:
        if e[2] != 'discovery' or e[0] != d:
            continue
        true_kind = p['contacts'][e[3]['contact'] - 1]['kind']
        key = (e[0], e[1], e[3]['contact'])
        if e[1] < 30:
            if base.get(key) != e[3]['reported_label']:
                early_mismatch.append((seed, e[1], key))
        elif true_kind == 'Enemy' and e[3]['reported_label'] == 'Friendly' \
                and base.get(key) == 'Enemy':
            late_forced.append((seed, e[1]))
print('T4 early-turn label mismatches vs untreated (must be []):',
      early_mismatch)
found_early_flip = early_mismatch
found_late_flip = late_forced
t3flips = 0
for seed in range(20):
    p = twin.random_scenario(seed)
    d = twin.designated_unit(p, 'T3')
    ev = []
    twin.simulate(p, 46, ev, treatment='T3', designated=d)
    t3flips += sum(1 for e in ev if e[2] == 'discovery' and e[0] == d
                   and p['contacts'][e[3]['contact'] - 1]['kind'] == 'Enemy'
                   and e[3]['reported_label'] == 'Friendly')
print('T3 total true-Enemy->Friendly flips by designated unit:', t3flips)
assert not found_early_flip, 'T4 flipped before turn 30'
print('T4-GATE-OK: no flips before turn 30;', len(found_late_flip), 'late flips observed')
