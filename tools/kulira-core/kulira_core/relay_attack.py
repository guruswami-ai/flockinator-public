"""Relay-attack corroboration experiment (see pre-registration).

Synthetic lab simulation: an adversary forges one sighting of a hazard
contact and relays copies through other reporters. Three policies try
to commit contacts as survivor:
  A reporter-count   - relayed copies count as witnesses (vulnerable)
  B sighting-id dedup - copies share an ID and count once
  C direct multi-modal - B, plus >=2 modalities from >=2 nodes
  D direct-verified only - only non-forged (direct_verified) sightings
    may decide; unverified/hearsay never enter the deciding pool
  E verified + abstention - D, plus commit only on a clear margin
    (survivor minus hazard >= 2); close calls stay Unassessed
A forged-origin dangerous commit is one whose deciding sightings
include the forged sighting ID.
"""
from __future__ import annotations
import random

MODALITIES = ("ir", "co2", "sound")
NODES = ("A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2")

def generate_trial(seed: int, contacts: int = 40, identify_p: float = 0.75,
                   adversary_p: float = 0.5) -> list[dict]:
    rng = random.Random(seed)
    trial = []
    for i in range(contacts):
        truth = "survivor" if rng.random() < 0.5 else "hazard"
        reports = []  # (sighting_id, node, modality, label, forged)
        for k in range(rng.choice((1, 2, 3))):
            label = truth if rng.random() < identify_p else (
                "hazard" if truth == "survivor" else "survivor")
            reports.append((f"s{i}-{k}", NODES[(i + k) % len(NODES)],
                            rng.choice(MODALITIES), label, False))
        forged_id = None
        if truth == "hazard" and rng.random() < adversary_p:
            forged_id = f"forge-{i}"
            reports.append((forged_id, "K1", "ir", "survivor", True))
            for relay in ("B1", "C1", "D1"):  # copies: same ID, other reporters
                reports.append((forged_id, relay, "ir", "survivor", True))
        trial.append({"contact": i, "truth": truth, "reports": reports,
                      "forged_id": forged_id})
    return trial

def _commit(reports, policy: str):
    """Return (committed_survivor, deciding_ids) for one contact."""
    if policy == "A":
        pool = list(reports)
    else:  # B, C, D dedup by sighting ID, first report wins
        seen = {}
        for r in reports:
            seen.setdefault(r[0], r)
        pool = list(seen.values())
    if policy in ("D", "E", "E-M"):  # verified-origin only
        pool = [r for r in pool if not r[4]]
    surv = [r for r in pool if r[3] == "survivor"]
    haz = [r for r in pool if r[3] == "hazard"]
    if len(surv) < 2 or len(surv) <= len(haz):
        return False, set()
    if policy in ("E", "E-M") and len(surv) - len(haz) < 2:
        return False, set()  # close call: explicitly Unassessed
    if policy == "E-M" and len({r[2] for r in surv}) < 2:
        return False, set()  # collusion must span modalities to commit
    if policy == "C":
        if len({r[2] for r in surv}) < 2 or len({r[1] for r in surv}) < 2:
            return False, set()
    return True, {r[0] for r in surv}

def score_trial(trial, policy: str) -> dict:
    dangerous = forged_dangerous = survivors = committed_survivors = 0
    for c in trial:
        ok, deciding = _commit(c["reports"], policy)
        if c["truth"] == "survivor":
            survivors += 1
            committed_survivors += bool(ok)
        elif ok:
            dangerous += 1
            if c["forged_id"] and c["forged_id"] in deciding:
                forged_dangerous += 1
    unassessed = None
    if policy == "E":
        unassessed = 0
        for c in trial:
            ok, _ = _commit(c["reports"], policy)
            pool = [r for r in c["reports"] if not r[4]]
            if not ok and any(r[3] == "survivor" for r in pool):
                unassessed += 1
    return {"dangerous": dangerous, "forged_dangerous": forged_dangerous,
            "survivor_recall": round(committed_survivors / survivors, 4) if survivors else None,
            "survivors": survivors, "committed_survivors": committed_survivors,
            "unassessed": unassessed}

def run_experiment(seeds) -> dict:
    out = {}
    for policy in ("A", "B", "C", "D", "E", "E-M"):
        per_seed = {s: score_trial(generate_trial(s), policy) for s in seeds}
        tot_d = sum(v["dangerous"] for v in per_seed.values())
        tot_f = sum(v["forged_dangerous"] for v in per_seed.values())
        tot_s = sum(v["survivors"] for v in per_seed.values())
        tot_c = sum(v["committed_survivors"] for v in per_seed.values())
        out[policy] = {"per_seed": per_seed, "pooled": {
            "dangerous": tot_d, "forged_dangerous": tot_f,
            "survivor_recall": round(tot_c / tot_s, 4) if tot_s else None}}
    return out
