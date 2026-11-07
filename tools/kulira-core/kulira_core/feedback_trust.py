"""Delayed / incomplete outcome feedback vs learned reputation (#134).

Separate versioned runner reusing reputation.generate_sequence.
The policy sees outcomes only at their declared reveal event:
an outcome from contact i becomes usable at contact i+delay,
and only with probability `availability` (separate seeded RNG
stream). Truth is never consulted for a decision before its
reveal. Full-feedback settings (delay=0, availability=1.0)
reproduce reputation.score_sequence exactly for REP/REP-P/E.
"""
from __future__ import annotations

import random

from .relay_attack import NODES
from .reputation import COLLUDERS, PROBATION, generate_sequence


def score_sequence_feedback(seq, policy, delay: int = 0,
                            availability: float = 1.0,
                            reveal_seed: int = 0) -> dict:
    rep = {n: 1.0 for n in NODES}
    seen = {n: 0 for n in NODES}
    rng_reveal = random.Random(reveal_seed)
    pending = []  # (apply_at_contact, node, correct)
    halves = {0: 0, 1: 0}
    survivors = committed = decisions = 0
    decision_log = []
    for c in seq:
        i = c["contact"]
        for apply_at, node, good in [p for p in pending if p[0] <= i]:
            rep[node] = min(1.0, max(0.1, rep[node] + (0.05 if good else -0.15)))
            seen[node] += 1
        pending = [p for p in pending if p[0] > i]
        pool = {}
        for r in c["reports"]:
            pool.setdefault(r[0], r)
        pool = list(pool.values())
        surv = [r for r in pool if r[3] == "survivor"]
        haz = [r for r in pool if r[3] == "hazard"]
        if policy == "E":
            ok = len(surv) >= 2 and len(surv) - len(haz) >= 2
        else:
            def w(r):
                if policy == "REP-P" and seen[r[1]] < PROBATION:
                    return 1.0
                return rep[r[1]]
            ws = sum(w(r) for r in surv)
            wh = sum(w(r) for r in haz)
            ok = ws >= 1.5 and (ws - wh) >= 1.0
        decision_log.append(bool(ok))
        if c["truth"] == "survivor":
            survivors += 1
            committed += bool(ok)
        elif ok:
            halves[0 if i < 30 else 1] += 1
        decisions += bool(ok)
        if rng_reveal.random() < availability:
            for r in pool:
                pending.append((i + delay, r[1], r[3] == c["truth"]))
    for apply_at, node, good in sorted(pending):  # flush: learning is
        rep[node] = min(1.0, max(0.1, rep[node] + (0.05 if good else -0.15)))  # real even
        seen[node] += 1  # if its reveal lands after the last decision
    honest = [v for n, v in rep.items() if n not in COLLUDERS]
    coll = [rep[n] for n in COLLUDERS]
    return {"dangerous_first": halves[0], "dangerous_second": halves[1],
            "recall": round(committed / survivors, 4) if survivors else None,
            "decisions": decisions, "decision_log": decision_log,
            "rep_colluders": round(sum(coll) / len(coll), 3),
            "rep_honest": round(sum(honest) / len(honest), 3)}


def run_feedback(seeds, delays=(0, 5, 15), avails=(1.0, 0.5, 0.25),
                 policies=("E", "REP", "REP-P")) -> dict:
    out = {}
    for policy in policies:
        for delay in delays:
            for avail in avails:
                per = [score_sequence_feedback(generate_sequence(s), policy,
                                               delay=delay, availability=avail,
                                               reveal_seed=s ^ 0xFEED)
                       for s in seeds]
                key = f"{policy} d={delay} a={avail}"
                out[key] = {
                    "dangerous_first": sum(p["dangerous_first"] for p in per),
                    "dangerous_second": sum(p["dangerous_second"] for p in per),
                    "mean_recall": round(sum(p["recall"] or 0 for p in per) / len(per), 4),
                    "mean_decisions": round(sum(p["decisions"] for p in per) / len(per), 2),
                    "rep_colluders": round(sum(p["rep_colluders"] for p in per) / len(per), 3)}
    return out
