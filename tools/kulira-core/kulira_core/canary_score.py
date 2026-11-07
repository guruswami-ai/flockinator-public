"""Score a canary device journal against the host twin.

Input: device CSV with the contract header
tick,seed,input_hash,decision,latency_us (canary-contract v1.1).
Output: per-seed parity report using twin.parity semantics -
joint identity+hash+decision agreement, missing-input rows
counted separately, >50% missing or any length mismatch is a
link/journal failure (parity None), never a policy score.
"""
from __future__ import annotations

import csv
import io

from .twin import parity, run_twin

HEADER = ["tick", "seed", "input_hash", "decision", "latency_us"]


def load_device_csv(text: str) -> list[dict]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or rows[0] != HEADER:
        raise ValueError(f"device journal header must be {HEADER}, "
                         f"got {rows[0] if rows else None}")
    out = []
    for r in rows[1:]:
        if not r:
            continue
        out.append({"tick": int(r[0]), "seed": int(r[1]),
                    "input_hash": r[2], "decision": int(r[3]),
                    "latency_us": int(r[4])})
    return out


def score_journal(device_rows: list[dict], ticks: int = 500,
                  expected_seeds=None) -> dict:
    """Score per-seed parity reports.

    Gate A journals carry 100 ticks for each of seeds 80, 81, 82;
    Gate B carries 500 ticks for one seed. The caller must state
    the expected manifest: a seed absent from the journal is a
    completeness failure (parity None), never silently omitted,
    and an empty journal against an expected manifest fails per
    expected seed instead of returning {}.
    """
    seeds = sorted({r["seed"] for r in device_rows})
    reports = {}
    for seed in seeds:
        dev = [r for r in device_rows if r["seed"] == seed]
        host = run_twin(seed, ticks, p_loss=0.0)
        rep = parity(host, dev)
        rep["latency_us_max"] = max((r["latency_us"] for r in dev), default=0)
        reports[str(seed)] = rep
    for seed in sorted(set(expected_seeds or []) - set(seeds)):
        reports[str(seed)] = {
            "compared": 0, "agree": 0, "missing_input_rows": 0,
            "link_failure": True, "parity": None,
            "length_mismatch": True, "missing_seed": True,
            "identity_mismatches": 0, "hash_mismatches": 0,
            "decision_mismatches": 0, "host_rows": ticks,
            "device_rows": 0, "latency_us_max": 0}
    return reports


def main(argv=None) -> int:
    import argparse
    import json
    import pathlib
    import sys
    parser = argparse.ArgumentParser(
        prog="canary_score",
        description="Score a canary device journal against the host twin.")
    parser.add_argument("journal", help="device journal CSV")
    parser.add_argument("--ticks", type=int, default=500,
                        help="ticks per seed (Gate A: 100, Gate B: 500)")
    parser.add_argument("--seeds", default=None,
                        help="expected seed manifest, e.g. 80,81,82; "
                             "asserts gate acceptance (parity 1.0)")
    args = parser.parse_args(argv)
    if args.seeds is not None and not args.seeds.strip():
        parser.error("--seeds manifest must name at least one seed")
    expected = ([int(s) for s in args.seeds.split(",")]
                if args.seeds else None)
    text = pathlib.Path(args.journal).read_text()
    reports = score_journal(load_device_csv(text), ticks=args.ticks,
                            expected_seeds=expected)
    print(json.dumps(reports, indent=1))
    # The JSON is the verdict; the exit code must not contradict it.
    # Any parity None (length mismatch, missing seed, link failure)
    # or an empty report set is a failed gate, not a pass.
    failed = not reports or any(
        r["parity"] is None or r["link_failure"] for r in reports.values())
    # With an explicit --seeds manifest the CLI asserts gate
    # acceptance, not mere scorability: Gate A passes only when
    # every expected seed matches on every row (parity 1.0), and
    # any unmanifested seed in the journal also fails acceptance.
    # Without a manifest the command is scoring-only and a
    # numerical parity below 1.0 is a publishable result.
    if expected:
        # Exact integer agreement, never the rounded parity value:
        # at large tick counts round(agree/n, 4) can display 1.0
        # with real mismatches (issue #174).
        failed = failed or any(
            reports[str(s)]["compared"] == 0
            or reports[str(s)]["agree"] != reports[str(s)]["compared"]
            for s in expected)
        failed = failed or any(
            int(s) not in expected for s in reports)
        # Gate acceptance is exact agreement on supplied rows:
        # a missing-marker row is a valid loss-aware score, but it
        # is not a supplied golden hash and never passes a gate.
        failed = failed or any(
            reports[str(s)]["missing_input_rows"] for s in expected)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
