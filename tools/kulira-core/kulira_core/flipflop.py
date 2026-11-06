"""Flip-flopping credentialed source vs hysteresis (pre-registered).

Same sequential world as modality_betrayal / feedback_delay (2 nodes x
ir/co2, trust learned from revealed outcomes, +0.10/-0.15 clamped to
[0.05, 1.0]). One credentialed source, (A1, ir), behaves until onset,
then alternates its alarm every contact regardless of truth - survivor,
hazard, survivor, hazard - so its agreement hovers near chance and
modality trust can never settle. Question: does the swarm's dispatch
decision flap with it, and does a persistence latch (trust must stay
low for D contacts to be discounted, high for R contacts to return)
stop the flapping, at what cost in rechecks and dangerous commits?
"""
from __future__ import annotations

import random

from .modality_betrayal import MODALITIES, NODES, _reading

FLIP = (NODES[0], "ir")
LO, HI = 0.30, 0.70


def run_seed_flip(seed, drop=1, restore=1, contacts=60, onset=30):
    rng = random.Random(seed)
    mod_trust = {m: 1.0 for m in MODALITIES}
    latched = {m: False for m in MODALITIES}
    low = {m: 0 for m in MODALITIES}
    high = {m: 0 for m in MODALITIES}
    post = {"dangerous": 0, "hazards": 0, "survivors": 0, "found": 0}
    decision_flips = rechecks = latch_toggles_ir = 0
    first_latch = None
    prev_dispatch = None
    for t in range(contacts):
        truth = "survivor" if rng.random() < 0.5 else "hazard"
        readings = []
        for n in NODES:
            for m in MODALITIES:
                if (n, m) == FLIP and t >= onset:
                    a = ((t - onset) % 2 == 0)  # alternates, no RNG drawn
                else:
                    a = _reading(rng, truth, m, False)
                readings.append((n, m, a))
        eff = {m: (0.0 if latched[m] else mod_trust[m]) for m in MODALITIES}
        score = sum(eff[m] for n, m, a in readings if a)
        dispatch = score >= 1.0
        if t >= onset:
            if truth == "hazard":
                post["hazards"] += 1
                post["dangerous"] += bool(dispatch)
            else:
                post["survivors"] += 1
                post["found"] += bool(dispatch)
            flip_alarm = next(a for n, m, a in readings if (n, m) == FLIP)
            noflip = score - (eff["ir"] if flip_alarm else 0.0)
            if (score >= 1.0) != (noflip >= 1.0):
                rechecks += 1  # this contact's outcome hinged on the flipper
            if prev_dispatch is not None and dispatch != prev_dispatch:
                decision_flips += 1
        prev_dispatch = dispatch
        for n, m, a in readings:
            agree = (a == (truth == "survivor"))
            mod_trust[m] = min(1.0, max(0.05, mod_trust[m] + (0.1 if agree else -0.15)))
        for m in MODALITIES:
            if not latched[m]:
                low[m] = low[m] + 1 if mod_trust[m] < LO else 0
                if low[m] >= drop:
                    latched[m] = True
                    low[m] = high[m] = 0
                    if m == "ir" and t >= onset:
                        latch_toggles_ir += 1
                        if first_latch is None:
                            first_latch = t - onset
            else:
                high[m] = high[m] + 1 if mod_trust[m] > HI else 0
                if high[m] >= restore:
                    latched[m] = False
                    low[m] = high[m] = 0
                    if m == "ir" and t >= onset:
                        latch_toggles_ir += 1
    post["recall"] = round(post["found"] / post["survivors"], 4) if post["survivors"] else None
    return {"post_flip": post, "decision_flips": decision_flips,
            "latch_toggles_ir": latch_toggles_ir, "rechecks": rechecks,
            "first_latch_contact": first_latch}


def run_flipflop(seeds, conditions=((1, 1), (2, 2), (3, 2), (3, 4), (5, 5))):
    seeds = list(seeds)
    out = {}
    for d, r in conditions:
        per = [run_seed_flip(s, d, r) for s in seeds]
        latches = sorted(p["first_latch_contact"] for p in per
                         if p["first_latch_contact"] is not None)
        flips = sorted(p["decision_flips"] for p in per)
        out[f"D{d}-R{r}"] = {
            "dangerous": sum(p["post_flip"]["dangerous"] for p in per),
            "hazards": sum(p["post_flip"]["hazards"] for p in per),
            "mean_recall": round(sum(p["post_flip"]["recall"] or 0 for p in per) / len(per), 4),
            "median_decision_flips": flips[len(flips) // 2] if flips else None,
            "mean_rechecks": round(sum(p["rechecks"] for p in per) / len(per), 4),
            "latched_seeds": len(latches),
            "median_first_latch": latches[len(latches) // 2] if latches else None}
    return out
