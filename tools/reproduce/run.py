#!/usr/bin/env python3
"""Reproduce the flagship communication benchmark from a public checkout.

One command, offline, no credentials, no network, no model calls:

    uv run python tools/reproduce/run.py --out /tmp/flockinator-repro
    uv run python tools/reproduce/run.py --verify   # regression-check vs expected.json

Imports the existing scientific code (tools/mission-host/coordination_lab.py);
does not copy it. Writes:
  results.json  - canonical scientific content (stable key order, no timestamps)
  summary.txt   - short human-readable result
Canonical content is hashed (sha256) so reruns can be compared byte-for-byte
on the scientific payload, independent of run metadata.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "mission-host"))
from coordination_lab import learning_comparison  # noqa: E402

SEEDS = list(range(16))
EXPECTED_PATH = Path(__file__).resolve().parent / "expected.json"

def scientific_content() -> dict:
    per_seed = []
    totals = {}
    for seed in SEEDS:
        r = learning_comparison(seed, "Scrambled")
        clear = next(x for x in r["rows"] if x["train"] == "Clear" and x["test"] == "Clear")
        scram = next(x for x in r["rows"] if x["train"] == "Clear" and x["test"] == "Scrambled")
        solo = r["solo"]
        row = {"seed": seed}
        for name, src in (("clear", clear), ("scrambled", scram), ("private", solo)):
            row[f"{name}_recoveries"] = src["recoveries"]
            row[f"{name}_tasks"] = src["tasks"]
            t = totals.setdefault(name, {"recoveries": 0, "tasks": 0})
            t["recoveries"] += src["recoveries"]; t["tasks"] += src["tasks"]
        per_seed.append(row)
    pooled = {k: {"recoveries": v["recoveries"], "tasks": v["tasks"],
                  "rate": round(v["recoveries"] / v["tasks"], 6)} for k, v in totals.items()}
    return {"experiment": "field-signals-v1", "source": "tools/mission-host/coordination_lab.py",
            "definition": "team success = at least 3 of 4 agents choose the correct sector; "
                          "4 teams x 32 held-out rounds per seed (team tasks within a seed are not independent)",
            "seeds": SEEDS, "per_seed": per_seed, "pooled": pooled}

def canonical_hash(content: dict) -> str:
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None, help="output directory for results.json + summary.txt")
    ap.add_argument("--verify", action="store_true", help="compare canonical content to expected.json; exit 1 on mismatch")
    args = ap.parse_args()
    content = scientific_content()
    digest = canonical_hash(content)
    if args.verify:
        expected = json.loads(EXPECTED_PATH.read_text())
        if expected.get("scientific_content") != content:
            print("VERIFY FAILED: canonical scientific content differs from expected.json", file=sys.stderr)
            return 1
        print(f"VERIFY OK sha256={digest}")
        return 0
    pooled = content["pooled"]
    summary = (
        "Flockinator flagship communication benchmark (field-signals-v1)\n"
        f"Clear peer messages:      {pooled['clear']['rate']:.3%} "
        f"({pooled['clear']['recoveries']}/{pooled['clear']['tasks']} team tasks)\n"
        f"Private cues only (muted): {pooled['private']['rate']:.3%} "
        f"({pooled['private']['recoveries']}/{pooled['private']['tasks']})\n"
        f"Scrambled peer messages:   {pooled['scrambled']['rate']:.3%} "
        f"({pooled['scrambled']['recoveries']}/{pooled['scrambled']['tasks']})\n"
        "Host simulation only. Muted baseline receives no peer messages by design "
        "(different information budget). Team tasks within a seed are not independent.\n"
        f"canonical sha256: {digest}\n")
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "results.json").write_text(json.dumps(
            {"scientific_content": content, "canonical_sha256": digest}, indent=1) + "\n")
        (args.out / "summary.txt").write_text(summary)
        print(f"wrote {args.out}/results.json and summary.txt")
    print(summary, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
