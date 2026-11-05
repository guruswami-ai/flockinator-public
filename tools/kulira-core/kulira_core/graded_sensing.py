"""Graded sensing: policy E+R - buy one better sighting on abstention.

World: relay-attack trials. Deciding pool is policy-D (direct only).
E abstains on margin <2. E+R spends one extra direct sighting (90%
identify accuracy, fresh node) on would-abstain contacts with at
least one survivor sighting, then reapplies the E margin rule once.
"""
from __future__ import annotations
import random
from .relay_attack import MODALITIES, NODES, generate_trial

def _pool(reports):
    seen = {}
    for r in reports:
        if not r[4]:  # direct only; forged/hearsay never decide
            seen.setdefault(r[0], r)
    return list(seen.values())

def _e_commit(pool):
    surv = [r for r in pool if r[3] == "survivor"]
    haz = [r for r in pool if r[3] == "hazard"]
    return len(surv) >= 2 and len(surv) - len(haz) >= 2, surv, haz

def score_trial_graded(trial, seed):
    out = {"E": {"dangerous": 0, "survivors": 0, "committed": 0},
           "E+R": {"dangerous": 0, "survivors": 0, "committed": 0, "rechecks": 0}}
    for c in trial:
        pool = _pool(c["reports"])
        ok, surv, haz = _e_commit(pool)
        # policy E
        if c["truth"] == "survivor":
            out["E"]["survivors"] += 1; out["E"]["committed"] += bool(ok)
        elif ok:
            out["E"]["dangerous"] += 1
        # policy E+R
        ok_r, rechecked = ok, False
        if not ok and surv:
            rng = random.Random(str(seed) + ":" + str(c["contact"]))
            used = {r[1] for r in pool}
            fresh = [n for n in NODES if n not in used]
            if fresh:
                rechecked = True
                label = c["truth"] if rng.random() < 0.90 else (
                    "hazard" if c["truth"] == "survivor" else "survivor")
                pool2 = pool + [(f"recheck-{c['contact']}", fresh[0],
                                 rng.choice(MODALITIES), label, False)]
                ok_r, _, _ = _e_commit(pool2)
        out["E+R"]["rechecks"] += bool(rechecked)
        if c["truth"] == "survivor":
            out["E+R"]["survivors"] += 1; out["E+R"]["committed"] += bool(ok_r)
        elif ok_r:
            out["E+R"]["dangerous"] += 1
    for p in out.values():
        p["recall"] = round(p["committed"] / p["survivors"], 4) if p["survivors"] else None
        p["contacts"] = len(trial)
    return out

def run_graded(seeds):
    agg = {}
    for s in seeds:
        r = score_trial_graded(generate_trial(s), s)
        for pol, v in r.items():
            a = agg.setdefault(pol, {"dangerous": 0, "survivors": 0, "committed": 0, "rechecks": 0, "contacts": 0})
            for k in a: a[k] += v.get(k, 0)
    for v in agg.values():
        v["recall"] = round(v["committed"] / v["survivors"], 4) if v["survivors"] else None
        v["rechecks_per_contact"] = round(v["rechecks"] / v["contacts"], 4) if v["contacts"] else None
    return agg
