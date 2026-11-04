#!/usr/bin/env python3
"""Paired candidate-vs-baseline gates for the I2 pre-registration.

Computations are paired by seed. Contact-bearing seeds are those whose
baseline scenario contains at least one contact; zero-contact seeds are
excluded from recall gates because recall is undefined there. This file
implements the comparison step only: it never generates or tunes runs.

Usage:
  python3 compare.py --baseline baseline-dev.json \
      --candidate baseline-candidate-dev.json --set dev
"""
import argparse
import json
import pathlib
import statistics


def _by_seed(payload):
    return {row["seed"]: row for row in payload["per_seed"]}


def _pooled(rows, numerator, denominator):
    top = sum(row[numerator] for row in rows)
    bottom = sum(row[denominator] for row in rows)
    return round(top / bottom, 4) if bottom else None


def compare(baseline_payload, candidate_payload, seed_set):
    baseline = _by_seed(baseline_payload)
    candidate = _by_seed(candidate_payload)
    seeds = sorted(baseline)
    if seeds != sorted(candidate):
        raise ValueError("baseline and candidate seed sets differ")

    pairs = []
    for seed in seeds:
        base = baseline[seed]
        cand = candidate[seed]
        if base["contacts_total"] != cand["contacts_total"]:
            raise ValueError(f"seed {seed}: contact totals differ")
        if base["units"] != cand["units"]:
            raise ValueError(f"seed {seed}: unit counts differ")
        pairs.append({
            "seed": seed,
            "eligible": base["contacts_total"] > 0,
            "baseline": base,
            "candidate": cand,
            "recall_delta": (round(cand["recall"] - base["recall"], 4)
                             if base["recall"] is not None
                             and cand["recall"] is not None else None),
        })
    eligible = [p for p in pairs if p["eligible"]]
    base_rows = [p["baseline"] for p in eligible]
    cand_rows = [p["candidate"] for p in eligible]
    all_base = [p["baseline"] for p in pairs]
    all_cand = [p["candidate"] for p in pairs]

    base_recall = round(statistics.mean(r["recall"] for r in base_rows), 4)
    cand_recall = round(statistics.mean(r["recall"] for r in cand_rows), 4)
    non_worse = sum(1 for p in eligible if p["recall_delta"] >= 0)
    base_mislabel = _pooled(base_rows, "mislabelled", "discoveries")
    cand_mislabel = _pooled(cand_rows, "mislabelled", "discoveries")
    base_ef = _pooled(base_rows, "mislabelled_enemy_as_friendly",
                      "discoveries")
    cand_ef = _pooled(cand_rows, "mislabelled_enemy_as_friendly",
                      "discoveries")

    def mean_ratio(rows):
        values = [r["discoveries_per_energy"] for r in rows
                  if r.get("discoveries_per_energy") is not None]
        return round(statistics.mean(values), 4) if values else None

    base_energy = mean_ratio(all_base)
    cand_energy = mean_ratio(all_cand)
    all_landed_home = all(
        r["units_landed_home"] == r["units"] for r in all_cand)
    no_reserve_violations = all(
        r.get("reserve_floor_violations", 0) == 0 for r in all_cand)

    values = {
        "eligible_seeds": [p["seed"] for p in eligible],
        "baseline_recall": base_recall,
        "candidate_recall": cand_recall,
        "recall_delta": round(cand_recall - base_recall, 4),
        "non_worse_seeds": non_worse,
        "eligible_seed_count": len(eligible),
        "baseline_mislabel_rate": base_mislabel,
        "candidate_mislabel_rate": cand_mislabel,
        "baseline_enemy_as_friendly_per_discovery": base_ef,
        "candidate_enemy_as_friendly_per_discovery": cand_ef,
        "baseline_discoveries_per_energy": base_energy,
        "candidate_discoveries_per_energy": cand_energy,
        "all_units_landed_home": all_landed_home,
        "no_reserve_floor_violations": no_reserve_violations,
    }
    if seed_set == "dev":
        gates = {
            "1_recall_gain_at_least_0.15":
                values["recall_delta"] >= 0.15,
            "2_at_least_12_of_16_non_worse":
                len(eligible) == 16 and non_worse >= 12,
            "3_pooled_mislabel_rates_not_worse":
                cand_mislabel <= base_mislabel and cand_ef <= base_ef,
            "4_discoveries_per_energy_within_10pct":
                cand_energy >= round(base_energy * 0.9, 6),
            "5_all_home_no_reserve_violations":
                all_landed_home and no_reserve_violations,
        }
    elif seed_set == "holdout":
        gates = {
            "6_recall_and_rates_improve_or_hold":
                values["recall_delta"] > 0
                and cand_mislabel <= base_mislabel
                and cand_ef <= base_ef,
        }
    else:
        raise ValueError(f"unknown seed set {seed_set!r}")
    return {"set": seed_set, "values": values, "gates": gates,
            "all_gates_pass": all(gates.values()),
            "pairs": [{"seed": p["seed"], "eligible": p["eligible"],
                       "recall_delta": p["recall_delta"]}
                      for p in pairs]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--set", choices=("dev", "holdout"), required=True)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    result = compare(
        json.loads(pathlib.Path(args.baseline).read_text()),
        json.loads(pathlib.Path(args.candidate).read_text()), args.set)
    rendered = json.dumps(result, indent=1, sort_keys=True)
    if args.out:
        pathlib.Path(args.out).write_text(rendered + "\n")
    print(rendered)
    return 0 if result["all_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
