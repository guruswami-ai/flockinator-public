"""Behavioural reputation vs verified colluders.

Sequential contacts; 2 of 8 verified nodes lie on hazards.
REP weights deciding sightings by per-node reputation learned
from revealed outcomes; E counts unweighted with abstention.
"""
from __future__ import annotations
import random
from .relay_attack import MODALITIES, NODES

COLLUDERS = set(NODES[:2])

def generate_sequence(seed, contacts=60):
    rng = random.Random(seed)
    seq = []
    for i in range(contacts):
        truth = "survivor" if rng.random() < 0.5 else "hazard"
        nodes = rng.sample(NODES, rng.choice((2, 3)))
        reports = []
        for j, node in enumerate(nodes):
            if truth == "hazard" and node in COLLUDERS:
                label = "survivor"
            else:
                label = truth if rng.random() < 0.75 else (
                    "hazard" if truth == "survivor" else "survivor")
            reports.append((f"s{i}-{j}", node, rng.choice(MODALITIES), label, False))
        seq.append({"contact": i, "truth": truth, "reports": reports})
    return seq

def score_sequence(seq, policy):
    rep = {n: 1.0 for n in NODES}
    halves = {0: {"dangerous": 0}, 1: {"dangerous": 0}}
    survivors = committed = 0
    for c in seq:
        pool = {}
        for r in c["reports"]:
            pool.setdefault(r[0], r)
        pool = list(pool.values())
        surv = [r for r in pool if r[3] == "survivor"]
        haz = [r for r in pool if r[3] == "hazard"]
        if policy == "E":
            ok = len(surv) >= 2 and len(surv) - len(haz) >= 2
        else:
            ws = sum(rep[r[1]] for r in surv); wh = sum(rep[r[1]] for r in haz)
            ok = ws >= 1.5 and (ws - wh) >= 1.0
        if c["truth"] == "survivor":
            survivors += 1; committed += bool(ok)
        elif ok:
            halves[0 if c["contact"] < 30 else 1]["dangerous"] += 1
        for r in pool:
            good = (r[3] == c["truth"])
            rep[r[1]] = min(1.0, max(0.1, rep[r[1]] + (0.05 if good else -0.15)))
    honest = [v for n, v in rep.items() if n not in COLLUDERS]
    coll = [rep[n] for n in COLLUDERS]
    return {"dangerous_first": halves[0]["dangerous"], "dangerous_second": halves[1]["dangerous"],
            "recall": round(committed / survivors, 4) if survivors else None,
            "rep_colluders": round(sum(coll) / len(coll), 3),
            "rep_honest": round(sum(honest) / len(honest), 3)}

def run_reputation(seeds):
    out = {}
    for pol in ("E", "REP"):
        per = [score_sequence(generate_sequence(s), pol) for s in seeds]
        out[pol] = {"dangerous_first": sum(p["dangerous_first"] for p in per),
                    "dangerous_second": sum(p["dangerous_second"] for p in per),
                    "mean_recall": round(sum(p["recall"] or 0 for p in per) / len(per), 4),
                    "rep_colluders": round(sum(p["rep_colluders"] for p in per) / len(per), 3),
                    "rep_honest": round(sum(p["rep_honest"] for p in per) / len(per), 3)}
    return out
