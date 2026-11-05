"""Composite defence: D admission + abstention + modality trust.

One world, two attacks: unverified forgeries with relays (from
contact 0) and an ir-modality betrayal (from contact 20). COMP
weights deciding sightings by learned modality trust; E does not.
Trust learns only from revealed outcomes.
"""
from __future__ import annotations
import random
from .relay_attack import MODALITIES, NODES

ONSET = 20

def generate_world(seed, contacts=40):
    rng = random.Random(seed)
    world = []
    for i in range(contacts):
        truth = "survivor" if rng.random() < 0.5 else "hazard"
        reports = []
        for k in range(rng.choice((1, 2, 3))):
            modality = rng.choice(MODALITIES)
            label = truth if rng.random() < 0.75 else (
                "hazard" if truth == "survivor" else "survivor")
            if i >= ONSET and modality == "ir" and rng.random() < 0.8:
                label = "hazard" if truth == "survivor" else "survivor"
            reports.append((f"s{i}-{k}", NODES[(i + k) % len(NODES)], modality, label, False))
        forged_id = None
        if truth == "hazard" and rng.random() < 0.5:
            forged_id = f"forge-{i}"
            reports.append((forged_id, "K1", "ir", "survivor", True))
            for relay in ("B1", "C1", "D1"):
                reports.append((forged_id, relay, "ir", "survivor", True))
        world.append({"contact": i, "truth": truth, "reports": reports, "forged_id": forged_id})
    return world

def _pool(reports):
    seen = {}
    for r in reports:
        if not r[4]:
            seen.setdefault(r[0], r)
    return list(seen.values())

def score_world(world, policy):
    trust = {m: 1.0 for m in MODALITIES}
    out = {"dangerous_post": 0, "forged_dangerous": 0, "survivors": 0, "committed": 0}
    for c in world:
        pool = _pool(c["reports"])
        surv = [r for r in pool if r[3] == "survivor"]
        haz = [r for r in pool if r[3] == "hazard"]
        if policy == "E":
            ok = len(surv) >= 2 and len(surv) - len(haz) >= 2
            deciding = {r[0] for r in surv} if ok else set()
        else:  # COMP
            ws = sum(trust[r[2]] for r in surv); wh = sum(trust[r[2]] for r in haz)
            ok = ws >= 1.5 and (ws - wh) >= 1.0
            deciding = {r[0] for r in surv} if ok else set()
        if c["truth"] == "survivor":
            out["survivors"] += 1; out["committed"] += bool(ok)
        elif ok:
            if c["contact"] >= ONSET: out["dangerous_post"] += 1
            if c["forged_id"] and c["forged_id"] in deciding: out["forged_dangerous"] += 1
        # learn from revealed outcome (direct sightings only)
        for r in pool:
            good = (r[3] == c["truth"])
            trust[r[2]] = min(1.0, max(0.1, trust[r[2]] + (0.05 if good else -0.10)))
    out["recall"] = round(out["committed"] / out["survivors"], 4) if out["survivors"] else None
    return out

def run_composite(seeds):
    out = {}
    for pol in ("E", "COMP"):
        per = [score_world(generate_world(s), pol) for s in seeds]
        out[pol] = {"dangerous_post": sum(p["dangerous_post"] for p in per),
                    "forged_dangerous": sum(p["forged_dangerous"] for p in per),
                    "mean_recall": round(sum(p["recall"] or 0 for p in per) / len(per), 4)}
    return out
