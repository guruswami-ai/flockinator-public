#!/usr/bin/env python3
"""Host-replay baseline for the self-improving firmware loop.

Generates journal runs with the desktop twin (tools/mission-host/
planner.py, parity-proven against board_model.cpp over seeds 0..99 by
firmware/korvo-monitor/tests/compare_boards.py), extracts each run zip,
and scores it with score.py. Aggregates are plain means over runs;
per-seed scores are kept in full.

Usage:
  python3 baseline.py --seeds 0-19 --out <dir> --label dev
  python3 baseline.py --seeds 100-109 --out <dir> --label holdout
"""
import argparse
import io
import json
import pathlib
import statistics
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]
                       / "mission-host"))
import exercise_memory  # noqa: E402
import planner          # noqa: E402

from score import score_run  # noqa: E402

EPOCH = 1_700_000_000.0  # fixed synthetic clock; journals are replay data
AGGREGATE_KEYS = (
    "recall", "contacts_found", "discoveries", "mislabelled",
    "mislabel_rate", "mislabelled_enemy_as_friendly",
    "enemy_as_friendly_per_discovery", "duplicate_discovery_rate",
    "high_found", "high_multi_sighted",
    "unique_tiles_covered", "checks_assigned",
    "checks_completed_with_discovery", "checks_completed_scan",
    "checks_negative", "high_checked_completed", "units_landed",
    "reserve_floor_violations", "abandoned_waypoints",
    "total_energy_spent", "discoveries_per_energy",
)


def generate(seed: int, dest: pathlib.Path) -> dict:
    plan = planner.random_scenario(seed)
    plan["episode"] = f"baseline-seed-{seed}"
    plan["segments"] = [[0, EPOCH]]
    sim = planner.simulate(plan, 46)
    events = []
    sim = planner.simulate(plan, sim["turn"], events)
    blob = exercise_memory.bundle(plan, "Complete", sim, events)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        z.extractall(dest)
    return score_run(dest)


def parse_seeds(spec: str):
    seeds = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            seeds.extend(range(int(lo), int(hi) + 1))
        else:
            seeds.append(int(part))
    return seeds


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="e.g. 0-19 or 100-109")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--candidate", default="search-board-1-host-replay",
                    help="candidate identity recorded beside producer ruleset")
    args = ap.parse_args(argv)

    out = pathlib.Path(args.out)
    per_seed = []
    for seed in parse_seeds(args.seeds):
        scores = generate(seed, out / "runs" / f"seed-{seed}")
        scores["seed"] = seed
        per_seed.append(scores)

    aggregate = {}
    for key in AGGREGATE_KEYS:
        values = [s[key] for s in per_seed if s.get(key) is not None]
        if values:
            aggregate[key] = round(statistics.mean(values), 4)
    payload = {"label": args.label, "candidate": args.candidate,
               "scorer_version": per_seed[0].get("scorer_version"),
               "reported_ruleset": per_seed[0]["ruleset"],
               "ruleset": per_seed[0]["ruleset"],
               "source": "host-replay (python twin, parity-proven)",
               "seeds": [s["seed"] for s in per_seed],
               "aggregate_means": aggregate, "per_seed": per_seed}
    target = out / f"baseline-{args.label}.json"
    target.write_text(json.dumps(payload, indent=1, sort_keys=True))
    print(f"{args.label}: {len(per_seed)} runs -> {target}")
    for key, value in aggregate.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
