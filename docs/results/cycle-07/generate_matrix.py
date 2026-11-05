#!/usr/bin/env python3
"""Cycle-07 dev-matrix generator: T0-T4 x seeds 0-19 journals + engagement.

Uses the provenance trust twin (provenance/planner.py) with the same
two-pass mechanics as baseline.py: simulate(plan, 46) for the turn count,
then re-simulate to that turn collecting events, bundle with phase
'Complete', extract per-seed run dirs. Scores every run with the frozen
scorer. Deterministic: fixed synthetic clock, no wall time, sorted seeds.
"""

import io
import json
import pathlib
import sys
import zipfile

CYCLE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(CYCLE.parents[3] / "tools" / "fleet-score"))
sys.path.insert(0, str(CYCLE.parents[3] / "tools" / "mission-host"))
sys.path.insert(0, str(CYCLE / "provenance"))
import planner as twin  # noqa: E402  (provenance twin, not production)
import exercise_memory as mem  # noqa: E402
from score import score_run  # noqa: E402

assert "provenance" in twin.__file__, twin.__file__

EPOCH = 1_700_000_000.0
TREATMENTS = ("T0", "T1", "T2", "T3", "T4")
SEEDS = list(range(20))


def engage(treatment, plan, designated, events):
    """Instrumented engagement counts (no hand-counting)."""
    discs = [e for e in events if e[2] == "discovery"]
    genuine = [e for e in discs
               if e[3].get("auth_status") == "direct_verified"]
    out = {"designated": designated, "units": plan["count"]}
    out["forged_emitted"] = sum(
        1 for e in discs if e[3].get("auth_status") == "forged_rejected")
    des = [e for e in genuine if e[0] == designated]
    out["designated_sightings"] = len(des)
    opps = [e for e in des
            if plan["contacts"][e[3]["contact"] - 1]["kind"] == "Enemy"]
    out["designated_true_enemy_opportunities"] = len(opps)
    if treatment == "T2":
        out["degraded_sightings"] = len(des)
    if treatment in ("T3", "T4"):
        late = [e for e in opps if e[1] >= 30]
        out["late_opportunities"] = len(late)
        out["flips_applied"] = sum(
            1 for e in (opps if treatment == "T3" else late)
            if e[3]["reported_label"] == "Friendly")
        out["early_flips"] = sum(
            1 for e in opps if e[1] < 30
            and e[3]["reported_label"] == "Friendly") \
            if treatment == "T4" else 0
    return out


def main():
    engagement = {}
    for treatment in TREATMENTS:
        engagement[treatment] = {"seeds": {}}
        for seed in SEEDS:
            p = twin.random_scenario(seed)
            p.update(episode=f"cycle07-{treatment}-seed-{seed}",
                     segments=[[0, EPOCH]], revision=0, turn=0,
                     phase="Running", since=EPOCH)
            designated = twin.designated_unit(p, treatment) \
                if treatment in ("T2", "T3", "T4") else None
            kw = dict(treatment=treatment)
            if designated is not None:
                kw["designated"] = designated
            s1 = twin.simulate(p, 46, None, **kw)
            ev = []
            s2 = twin.simulate(p, s1["turn"], ev, **kw)
            blob = mem.bundle(p, "Complete", s2, ev)
            dest = CYCLE / "runs" / treatment / f"seed-{seed}"
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                z.extractall(dest)
            engagement[treatment]["seeds"][str(seed)] = \
                engage(treatment, p, designated, ev)
            scored = score_run(dest)
            scored["seed"] = seed
            sdir = CYCLE / "scores" / treatment
            sdir.mkdir(parents=True, exist_ok=True)
            (sdir / f"seed-{seed}.json").write_text(
                json.dumps(scored, indent=1, sort_keys=True))
            print(f"{treatment} seed {seed}: turn={s2['turn']} "
                  f"units={len(s2['units'])} events={len(ev)}", flush=True)
        pool = engagement[treatment]["seeds"].values()
        keys = ("forged_emitted", "designated_sightings",
                "designated_true_enemy_opportunities", "degraded_sightings",
                "flips_applied", "late_opportunities", "early_flips")
        engagement[treatment]["pooled"] = {
            k: sum(v.get(k, 0) for v in pool) for k in keys}
    (CYCLE / "engagement.json").write_text(
        json.dumps(engagement, indent=1, sort_keys=True))
    print("wrote engagement.json")


if __name__ == "__main__":
    main()
