"""Delayed/missing revealed-outcome feedback for modality trust.

Same world as modality_betrayal (ir inverts at contact 30), but the
outcome that teaches trust arrives d contacts late and is dropped
with probability m. Trust still learns only from revealed outcomes.
"""
from __future__ import annotations
import random
from collections import deque
from .modality_betrayal import MODALITIES, NODES, _reading

def run_seed_delayed(seed, delay=0, missing=0.0, contacts=60, onset=30):
    rng = random.Random(seed)
    mod_trust = {m: 1.0 for m in MODALITIES}
    pending = deque()  # (apply_at, readings, truth)
    discount = None
    post = {"dangerous": 0, "hazards": 0, "survivors": 0, "found": 0}
    def apply(readings, truth):
        for n, m, a in readings:
            agree = (a == (truth == "survivor"))
            mod_trust[m] = min(1.0, max(0.05, mod_trust[m] + (0.1 if agree else -0.15)))
    for t in range(contacts + delay + 1):
        if t < contacts:
            truth = "survivor" if rng.random() < 0.5 else "hazard"
            betrayed = t >= onset
            readings = [(n, m, _reading(rng, truth, m, betrayed))
                        for n in NODES for m in MODALITIES]
            score = sum(mod_trust[m] for n, m, a in readings if a)
            if t >= onset:
                if truth == "hazard": post["hazards"] += 1; post["dangerous"] += bool(score >= 1.0)
                else: post["survivors"] += 1; post["found"] += bool(score >= 1.0)
            if rng.random() >= missing:
                pending.append((t + delay, readings, truth))
        while pending and pending[0][0] <= t:
            _, r, tr = pending.popleft(); apply(r, tr)
        if t >= onset and discount is None and mod_trust["ir"] < 0.3:
            discount = t - onset
    post["recall"] = round(post["found"] / post["survivors"], 4) if post["survivors"] else None
    return {"post_betrayal": post, "ir_discount_contacts": discount}

def run_feedback(seeds, conditions=((0, 0.0), (5, 0.0), (5, 0.5), (15, 0.0), (15, 0.5))):
    out = {}
    for d, m in conditions:
        per = [run_seed_delayed(s, d, m) for s in seeds]
        discs = sorted(p["ir_discount_contacts"] for p in per if p["ir_discount_contacts"] is not None)
        out[f"d{d}-m{m}"] = {
            "dangerous": sum(p["post_betrayal"]["dangerous"] for p in per),
            "hazards": sum(p["post_betrayal"]["hazards"] for p in per),
            "mean_recall": round(sum(p["post_betrayal"]["recall"] or 0 for p in per) / len(per), 4),
            "discounted_seeds": len(discs),
            "median_discount_contacts": discs[len(discs) // 2] if discs else None}
    return out
