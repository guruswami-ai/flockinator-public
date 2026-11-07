#!/usr/bin/env python3
"""Exact generation recipe for canary-host-rehearsal-001.json (#151).

Original script (run 2026-11-07 against the then-current
kulira_core), preserved with its mask construction. Run from the
repo root:

    uv run --project tools/kulira-core python \
        validation/kulira/canary-host-rehearsal-recipe.py

It regenerates the rehearsal values and verifies the headline
counts against the archived JSON (parity 1.0; missing rows
21/38/79; simloop missing 14/42/134; found ticks 149/163/191/283).
The hash_mismatches fields in the archived JSON predate the
#143 comparator fix and are NOT regenerated here (see the dated
correction in docs/experiments/canary-host-rehearsal-results.md).
"""
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]
                       / "tools" / "kulira-core"))
from kulira_core.twin import (WAIT, distribution_sweep, missing_hash,  # noqa: E402
                              parity, run_twin)
from kulira_core.simloop import run_loop  # noqa: E402


def main():
    levels = {}
    for p in (0.0, 0.05, 0.10, 0.20):
        host = run_twin(80, 500, p_loss=0.0)
        drop_rng = random.Random(80 ^ 0xD90F)
        device = []
        for row in host:
            if drop_rng.random() < p:
                device.append({**row, "input_hash": missing_hash(row["tick"], 80),
                               "decision": WAIT})
            else:
                device.append(dict(row))
        levels[str(p)] = parity(host, device)
    sweep = distribution_sweep(80, ticks=2000)
    deg = {}
    for frac in (0.0, 0.1, 0.25, 0.5):
        drops = frozenset(t for t in range(300) if (t * 97) % 100 < frac * 100)
        out = run_loop(42, ticks=300, drop_ticks=drops)
        deg[str(frac)] = {
            "found_tick": out["found_tick"], "ticks_run": out["ticks_run"],
            "missing_rows": sum(1 for r in out["journal"]
                                if r["input_hash"] == missing_hash(r["tick"], 42))}
    arch = json.loads(pathlib.Path(
        "validation/kulira/canary-host-rehearsal-001.json").read_text())
    ok = True
    for k in levels:
        a, b = arch["parity_levels"][k], levels[k]
        match = (a["missing_input_rows"] == b["missing_input_rows"]
                 and a["parity"] == b["parity"])
        ok &= match
        print(f"parity loss={k}: archived missing={a['missing_input_rows']} "
              f"regen={b['missing_input_rows']} parity={b['parity']} "
              f"{'MATCH' if match else 'MISMATCH'}")
    for k in deg:
        a, b = arch["simloop_degradation"][k], deg[k]
        match = a == b
        ok &= match
        print(f"simloop drop={k}: archived={a} regen={b} "
              f"{'MATCH' if match else 'MISMATCH'}")
    print("sweep archived keys:", sorted(arch["distribution_sweep"]) ==
          sorted(sweep))
    print("RECIPE VERIFY:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
