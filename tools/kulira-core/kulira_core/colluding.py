"""Colluding minorities vs policy E (see pre-registration).

k of 8 verified nodes hold valid keys but label every hazard they
sight as survivor. Policies E and E-M (E + >=2 modalities) are scored
for the collusion tolerance curve: dangerous commits vs k.
"""
from __future__ import annotations
import random
from .relay_attack import MODALITIES, NODES, _commit

def generate_trial_colluding(seed: int, k: int, contacts: int = 40,
                             identify_p: float = 0.75) -> list[dict]:
    rng = random.Random(seed)  # paired: same contacts for every k; only collusion varies
    colluders = set(NODES[:k])
    trial = []
    for i in range(contacts):
        truth = "survivor" if rng.random() < 0.5 else "hazard"
        reports = []
        for j in range(rng.choice((1, 2, 3))):
            node = NODES[(i + j) % len(NODES)]
            if truth == "hazard" and node in colluders:
                label = "survivor"  # verified lie
            else:
                label = truth if rng.random() < identify_p else (
                    "hazard" if truth == "survivor" else "survivor")
            reports.append((f"s{i}-{j}", node, rng.choice(MODALITIES), label, False, node in colluders))
        trial.append({"contact": i, "truth": truth, "reports": reports})
    return trial

def score_colluding(trial, policy: str) -> dict:
    dangerous = colluder_dangerous = survivors = committed = 0
    by_id = {}
    for c in trial:
        by_id.update({r[0]: r for r in c["reports"]})
        ok, deciding = _commit(c["reports"], policy)
        if c["truth"] == "survivor":
            survivors += 1; committed += bool(ok)
        elif ok:
            dangerous += 1
            if any(by_id[sid][5] for sid in deciding if sid in by_id):
                colluder_dangerous += 1
    return {"dangerous": dangerous, "colluder_dangerous": colluder_dangerous,
            "survivor_recall": round(committed / survivors, 4) if survivors else None}

def run_colluding(seeds, ks=(0, 1, 2, 3)) -> dict:
    out = {}
    for policy in ("E", "E-M"):
        out[policy] = {}
        for k in ks:
            per = [score_colluding(generate_trial_colluding(s, k), policy) for s in seeds]
            out[policy][str(k)] = {
                "dangerous": sum(v["dangerous"] for v in per),
                "colluder_dangerous": sum(v["colluder_dangerous"] for v in per),
                "mean_recall": round(sum(v["survivor_recall"] or 0 for v in per) / len(per), 4)}
    return out
