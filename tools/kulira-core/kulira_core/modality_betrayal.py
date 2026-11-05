"""Modality betrayal: can trust attach to a sensor type, not a node?

Sequential contacts; at onset the ir modality inverts while co2
stays honest. Arms differ only in where trust lives: nowhere
(static), per node, per modality, or both. Outcomes are revealed
after each contact (field confirmation), and trust updates only
from revealed outcomes.
"""
from __future__ import annotations
import random

NODES = ("A1", "B1")
MODALITIES = ("ir", "co2")

def _reading(rng, truth, modality, betrayed):
    p = 0.85 if truth == "survivor" else 0.10
    if betrayed and modality == "ir":
        p = 0.10 if truth == "survivor" else 0.85
    return rng.random() < p  # True = anomalous

def run_seed(seed, arm, contacts=60, onset=30):
    rng = random.Random(seed)
    node_trust = {n: 1.0 for n in NODES}
    mod_trust = {m: 1.0 for m in MODALITIES}
    ir_discount_at = None
    post = {"dangerous": 0, "survivors": 0, "found": 0, "hazards": 0}
    for t in range(contacts):
        truth = "survivor" if rng.random() < 0.5 else "hazard"
        betrayed = t >= onset
        readings = [(n, m, _reading(rng, truth, m, betrayed))
                    for n in NODES for m in MODALITIES]
        def w(n, m):
            if arm == "static": return 1.0
            if arm == "node": return node_trust[n]
            if arm == "modality": return mod_trust[m]
            return node_trust[n] * mod_trust[m]
        score = sum(w(n, m) for n, m, a in readings if a)
        dig = score >= 1.0
        if t >= onset:
            if truth == "hazard":
                post["hazards"] += 1; post["dangerous"] += bool(dig)
            else:
                post["survivors"] += 1; post["found"] += bool(dig)
            if arm in ("modality", "both") and ir_discount_at is None and mod_trust["ir"] < 0.3:
                ir_discount_at = t - onset
        # update from revealed outcome only
        for n, m, a in readings:
            agree = (a == (truth == "survivor"))
            delta = 0.1 if agree else -0.15
            if arm in ("node", "both"):
                node_trust[n] = min(1.0, max(0.05, node_trust[n] + delta))
            if arm in ("modality", "both"):
                mod_trust[m] = min(1.0, max(0.05, mod_trust[m] + delta))
    post["recall"] = round(post["found"] / post["survivors"], 4) if post["survivors"] else None
    return {"post_betrayal": post, "ir_discount_contacts": ir_discount_at,
            "final_modality_trust": {m: round(v, 3) for m, v in mod_trust.items()}}

def run_experiment(seeds, arms=("static", "node", "modality", "both")):
    out = {}
    for arm in arms:
        per = [run_seed(s, arm) for s in seeds]
        discs = [p["ir_discount_contacts"] for p in per if p["ir_discount_contacts"] is not None]
        out[arm] = {
            "dangerous": sum(p["post_betrayal"]["dangerous"] for p in per),
            "hazards": sum(p["post_betrayal"]["hazards"] for p in per),
            "mean_recall": round(sum(p["post_betrayal"]["recall"] or 0 for p in per) / len(per), 4),
            "ir_discounted_seeds": len(discs),
            "median_discount_contacts": sorted(discs)[len(discs) // 2] if discs else None}
    return out
