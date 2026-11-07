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


def score_journal(device_rows: list[dict], ticks: int = 500) -> dict:
    seeds = sorted({r["seed"] for r in device_rows})
    reports = {}
    for seed in seeds:
        dev = [r for r in device_rows if r["seed"] == seed]
        host = run_twin(seed, ticks, p_loss=0.0)
        rep = parity(host, dev)
        rep["latency_us_max"] = max((r["latency_us"] for r in dev), default=0)
        reports[str(seed)] = rep
    return reports


def main(argv=None) -> int:
    import json
    import pathlib
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: canary_score.py <device-journal.csv>", file=sys.stderr)
        return 2
    text = pathlib.Path(argv[0]).read_text()
    print(json.dumps(score_journal(load_device_csv(text)), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
