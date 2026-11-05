"""Priority-split graded sensing (Policy F).

High-priority (irreversible) contacts: policy E abstention only.
Low-priority (reversible) contacts: E+R, one bought second look.
References E and E+R recomputed on identical trials.
"""
from __future__ import annotations
import random
from .graded_sensing import _e_commit, _pool
from .relay_attack import MODALITIES, NODES, generate_trial

def _priority(seed, contact):
    return "high" if random.Random(str(seed) + ":prio:" + str(contact)).random() < 0.5 else "low"

def _recheck(c, pool, surv, seed):
    rng = random.Random(str(seed) + ":" + str(c["contact"]))
    used = {r[1] for r in pool}
    fresh = [n for n in NODES if n not in used]
    if not fresh:
        return None
    label = c["truth"] if rng.random() < 0.90 else (
        "hazard" if c["truth"] == "survivor" else "survivor")
    return pool + [(f"recheck-{c['contact']}", fresh[0], rng.choice(MODALITIES), label, False)]

def score_trial_split(trial, seed):
    agg = {p: {"dangerous": 0, "dangerous_high": 0, "survivors": 0, "committed": 0}
           for p in ("E", "E+R", "F")}
    for c in trial:
        prio = _priority(seed, c["contact"])
        pool = _pool(c["reports"])
        ok_e, surv, _ = _e_commit(pool)
        ok_r = ok_e
        if not ok_e and surv:
            p2 = _recheck(c, pool, surv, seed)
            if p2 is not None:
                ok_r, _, _ = _e_commit(p2)
        decisions = {"E": ok_e, "E+R": ok_r, "F": ok_e if prio == "high" else ok_r}
        for pol, ok in decisions.items():
            a = agg[pol]
            if c["truth"] == "survivor":
                a["survivors"] += 1; a["committed"] += bool(ok)
            elif ok:
                a["dangerous"] += 1
                if prio == "high": a["dangerous_high"] += 1
    for a in agg.values():
        a["recall"] = round(a["committed"] / a["survivors"], 4) if a["survivors"] else None
    return agg

def run_split(seeds):
    tot = {}
    for s in seeds:
        r = score_trial_split(generate_trial(s), s)
        for pol, v in r.items():
            a = tot.setdefault(pol, {"dangerous": 0, "dangerous_high": 0, "survivors": 0, "committed": 0})
            for k in a: a[k] += v[k]
    for a in tot.values():
        a["recall"] = round(a["committed"] / a["survivors"], 4) if a["survivors"] else None
    return tot
