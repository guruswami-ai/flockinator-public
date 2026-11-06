"""Selective-silence experiment (pre-registered, kulira-next-preregistrations).

Synthetic lab simulation: the adversary adds nothing and forges
nothing. On hazard contacts it suppresses the honest hazard sightings,
leaving only survivor-labelled errors visible, so a naive majority can
commit a hazard as a survivor. Zero false messages exist to detect;
only counting rules, margin abstention, and modality diversity can
help. Policies are the relay-attack set A-E/E-M, reused verbatim via
relay_attack._commit so silence and forgery are paired-comparable on
the same honest report prefix (same RNG draw order before the
adversary gate).
"""
from __future__ import annotations

import random

from .relay_attack import MODALITIES, NODES, _commit

POLICIES = ("A", "B", "C", "D", "E", "E-M")


def generate_trial_silence(seed: int, contacts: int = 40,
                           identify_p: float = 0.75,
                           adversary_p: float = 0.5) -> list[dict]:
    """One seeded trial. `reports` is what policies see; `suppressed`
    holds the removed hazard sightings (never passed to _commit except
    in the counterfactual rescore inside score_trial_silence)."""
    rng = random.Random(seed)
    trial = []
    for i in range(contacts):
        truth = "survivor" if rng.random() < 0.5 else "hazard"
        honest = []
        for k in range(rng.choice((1, 2, 3))):
            label = truth if rng.random() < identify_p else (
                "hazard" if truth == "survivor" else "survivor")
            honest.append((f"s{i}-{k}", NODES[(i + k) % len(NODES)],
                           rng.choice(MODALITIES), label, False))
        targeted = False
        visible, suppressed = honest, []
        if truth == "hazard" and rng.random() < adversary_p:
            targeted = True
            suppressed = [r for r in honest if r[3] == "hazard"]
            visible = [r for r in honest if r[3] == "survivor"]
        trial.append({"contact": i, "truth": truth, "reports": visible,
                      "suppressed": suppressed, "targeted": targeted,
                      "forged_id": None})
    return trial


def score_trial_silence(trial, policy: str) -> dict:
    dangerous = silenced_dangerous = survivors = committed = 0
    targeted = suppressed_total = 0
    for c in trial:
        targeted += bool(c["targeted"])
        suppressed_total += len(c["suppressed"])
        ok, _ = _commit(c["reports"], policy)
        if c["truth"] == "survivor":
            survivors += 1
            committed += bool(ok)
        elif ok:
            dangerous += 1
            full_ok, _ = _commit(c["reports"] + c["suppressed"], policy)
            if not full_ok:
                silenced_dangerous += 1  # suppression was pivotal
    unassessed = None
    if policy == "E":
        unassessed = sum(
            1 for c in trial
            if not _commit(c["reports"], policy)[0]
            and any(r[3] == "survivor" for r in c["reports"] if not r[4]))
    return {"dangerous": dangerous, "silenced_dangerous": silenced_dangerous,
            "survivor_recall": round(committed / survivors, 4) if survivors else None,
            "survivors": survivors, "committed_survivors": committed,
            "targeted": targeted, "suppressed": suppressed_total,
            "unassessed": unassessed}


def run_silence(seeds, policies=POLICIES) -> dict:
    out = {}
    for policy in policies:
        per_seed = {s: score_trial_silence(generate_trial_silence(s), policy)
                    for s in seeds}
        tot_s = sum(v["survivors"] for v in per_seed.values())
        tot_c = sum(v["committed_survivors"] for v in per_seed.values())
        out[policy] = {"per_seed": per_seed, "pooled": {
            "dangerous": sum(v["dangerous"] for v in per_seed.values()),
            "silenced_dangerous": sum(v["silenced_dangerous"] for v in per_seed.values()),
            "survivor_recall": round(tot_c / tot_s, 4) if tot_s else None}}
    return out
