"""End-to-end lab evidence run (one thin slice).

Simulated swarm -> Kulira deceive reports -> bridge (Contract v1) ->
scorer-format journals. The fleet scorer (tools/fleet-score, consumed
read-only) then scores the run directory this writes. No transmission.
"""
from __future__ import annotations
import json
from pathlib import Path
from .bridge import to_journal_events

TRUTH = [
    {"pos": [7, 7], "kind": "Friendly", "priority": "High"},
    {"pos": [8, 8], "kind": "Enemy", "priority": "High"},
    {"pos": [9, 9], "kind": "Friendly", "priority": "Low"},
    {"pos": [10, 10], "kind": "Enemy", "priority": "Low"},
]
UNITS = ["A1", "B1", "C1", "D1"]

def build_run(out_dir, seed: int = 42) -> Path:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    # honest direct sightings of contact 1
    reports = [
        {"reporter": u, "originator": u, "sighting_id": "s-true-1", "claim": "Friendly",
         "verified": True, "forwarded": False, "contact": 1, "tile": [7, 7]}
        for u in UNITS[:2]
    ]
    # Kulira deceive: one direct false sighting (Enemy reported Friendly),
    # amplified by two forwarded copies - hearsay, not independent sightings
    reports.append({"reporter": "K1", "originator": "K1", "sighting_id": "s-false-1",
                    "claim": "Friendly", "verified": True, "forwarded": False,
                    "contact": 2, "tile": [8, 8]})
    for relay in ("C1", "D1"):
        reports.append({"reporter": relay, "originator": "K1", "sighting_id": "s-false-1",
                        "claim": "Friendly", "verified": True, "forwarded": True,
                        "origin_turn": 4, "contact": 2, "tile": [8, 8]})
    events = to_journal_events(reports)
    by_unit: dict[str, list[dict]] = {}
    for report, ev in zip(reports, events):
        ev = {**ev, "contact": report["contact"], "tile": report["tile"],
              "schema": 1, "source": "kulira_lab_simulation", "run": f"kulira-e2e-{seed}"}
        by_unit.setdefault(ev["unit"], []).append(ev)
    for unit, evs in by_unit.items():
        (out / f"{unit}.jsonl").write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in evs))
    (out / "director.json").write_text(json.dumps(
        {"schema": 1, "source": "kulira_lab_simulation", "run": f"kulira-e2e-{seed}",
         "units": sorted(by_unit), "ground_truth": TRUTH}, indent=2) + "\n")
    return out
