"""Post hoc same-window audit of the already exposed feedback-trust seeds.

No policy implementation, thresholds, historical outputs or registrations change.
The CLI deliberately has no seed-selection option: it replays only 220..259.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random

from .feedback_trust import score_sequence_feedback
from .reputation import generate_sequence

POLICIES = ("E", "REP", "REP-P")
COUNT_FIELDS = ("contacts", "hazards", "survivors", "dangerous", "found", "commits", "abstentions")
RATE_FIELDS = ("harm_rate", "recall", "coverage")


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


def window_metrics(seq, decisions, start=30, stop=60):
    """Evaluate decisions after execution; truth is never returned to a policy."""
    if len(seq) != len(decisions) or any(type(x) is not bool for x in decisions):
        raise ValueError("one boolean decision is required for every contact")
    contacts = [c["contact"] for c in seq]
    if contacts != list(range(len(seq))):
        raise ValueError("contacts must be contiguous, ordered and zero-based")
    if not (type(start) is int and type(stop) is int and 0 <= start < stop <= len(seq)):
        raise ValueError("invalid evaluation window")
    if any(c["truth"] not in ("hazard", "survivor") for c in seq):
        raise ValueError("unknown truth class")
    rows = list(zip(seq[start:stop], decisions[start:stop]))
    hazards = sum(c["truth"] == "hazard" for c, _ in rows)
    survivors = len(rows) - hazards
    dangerous = sum(ok and c["truth"] == "hazard" for c, ok in rows)
    found = sum(ok and c["truth"] == "survivor" for c, ok in rows)
    commits = dangerous + found
    return dict(contacts=len(rows), hazards=hazards, survivors=survivors,
                dangerous=dangerous, found=found, commits=commits,
                abstentions=len(rows)-commits, harm_rate=_rate(dangerous, hazards),
                recall=_rate(found, survivors), coverage=commits/len(rows))


def reveal_counts(seq, delay, availability, reveal_seed, start=30, stop=60):
    """Reconstruct event counts, not elapsed time or effective weight changes.

A label is selected after the decision at its originating contact. Its report
updates are first processed at max(i+1,i+delay); anything beyond the sequence
is processed only by the historical final flush. Truth/labels are not read.
"""
    if type(delay) is not int or delay < 0:
        raise ValueError("delay must be a nonnegative integer")
    if isinstance(availability, bool) or not isinstance(availability, (int, float)) or not math.isfinite(availability) or not 0 <= availability <= 1:
        raise ValueError("availability must be finite and in [0,1]")
    if [c["contact"] for c in seq] != list(range(len(seq))):
        raise ValueError("contacts must be contiguous, ordered and zero-based")
    if not (type(start) is int and type(stop) is int and 0 <= start < stop <= len(seq)):
        raise ValueError("invalid evaluation window")
    out = dict(outcome_draws=len(seq), selected_outcomes=0,
               selected_outcomes_in_window=0, offered_report_updates=0,
               applied_before_decisions=0, applied_before_window_decisions=0,
               post_horizon_flush=0)
    rng = random.Random(reveal_seed)
    for c in seq:
        i = c["contact"]
        if rng.random() >= availability:
            continue
        out["selected_outcomes"] += 1
        out["selected_outcomes_in_window"] += start <= i < stop
        count = len({report[0] for report in c["reports"]})
        out["offered_report_updates"] += count
        applied = max(i+1, i+delay)
        if applied < len(seq):
            out["applied_before_decisions"] += count
            if start <= applied < stop:
                out["applied_before_window_decisions"] += count
        else:
            out["post_horizon_flush"] += count
    return out


def paired_metrics(candidate, reference):
    return {key: None if candidate[key] is None or reference[key] is None
            else candidate[key]-reference[key]
            for key in ("dangerous", "found", "commits", *RATE_FIELDS)}


def difference_summary(values):
    """Marginal descriptive 95% Hoeffding interval, explicitly post hoc.

Each value is a paired per-seed rate difference in [-1,1]. These wide intervals
are not multiplicity-adjusted or a substitute for historical point criteria.
"""
    valid = [v for v in values if v is not None]
    if any(not math.isfinite(v) or not -1 <= v <= 1 for v in valid):
        raise ValueError("paired rate differences must be finite and in [-1,1]")
    if not valid:
        return {"n": 0, "undefined": len(values), "mean": None, "interval": None}
    mean = sum(valid)/len(valid)
    width = math.sqrt(2*math.log(40)/len(valid))
    return {"n": len(valid), "undefined": len(values)-len(valid), "mean": mean,
            "interval": [max(-1.0, mean-width), min(1.0, mean+width)]}


def audit_seed(seed, delay, availability):
    if type(seed) is not int or seed not in range(220, 260):
        raise ValueError("historical audit is restricted to exposed seeds 220..259")
    seq = generate_sequence(seed)
    policies = {}
    for policy in POLICIES:
        original = score_sequence_feedback(seq, policy, delay, availability, seed ^ 0xFEED)
        metrics = window_metrics(seq, original["decision_log"])
        if metrics["dangerous"] != original["dangerous_second"]:
            raise ValueError("audit window does not reproduce historical dangerous_second")
        policies[policy] = metrics
    return {"seed": seed, "feedback": reveal_counts(seq, delay, availability, seed ^ 0xFEED),
            "policies": policies,
            "paired": {f"{policy}_minus_E": paired_metrics(policies[policy], policies["E"])
                       for policy in ("REP", "REP-P")}}


def _cell_summary(rows):
    out = {"policies": {}, "paired": {}, "feedback_totals": {}}
    for policy in POLICIES:
        counts = {key: sum(r["policies"][policy][key] for r in rows) for key in COUNT_FIELDS}
        counts["pooled_harm_rate"] = _rate(counts["dangerous"], counts["hazards"])
        counts["pooled_recall"] = _rate(counts["found"], counts["survivors"])
        counts["pooled_coverage"] = _rate(counts["commits"], counts["contacts"])
        out["policies"][policy] = counts
    for contrast in ("REP_minus_E", "REP-P_minus_E"):
        out["paired"][contrast] = {key: difference_summary([r["paired"][contrast][key] for r in rows])
                                   for key in RATE_FIELDS}
    for key in rows[0]["feedback"]:
        out["feedback_totals"][key] = sum(r["feedback"][key] for r in rows)
    return out


def build_report():
    package = Path(__file__).parent
    names = ("feedback_audit.py", "feedback_trust.py", "reputation.py", "relay_attack.py")
    out = {
        "schema": "flockinator-feedback-audit/1",
        "status": "post_hoc_exposed_seeds_not_a_registered_test",
        "source_sha256": {name: hashlib.sha256((package/name).read_bytes()).hexdigest() for name in names},
        "window": {"start_inclusive": 30, "stop_exclusive": 60},
        "uncertainty": "Marginal descriptive 95% Hoeffding intervals across paired seeds; not multiplicity-adjusted; no verdict.",
        "cost_scope": "Reconstructed report-update applications, including non-decision E bookkeeping; not effective weight changes. Historical wall-clock/energy unavailable.",
        "splits": {},
    }
    for split, seeds, delays, avails in (
        ("dev", range(220, 240), (0, 5, 15), (1.0, 0.5, 0.25)),
        ("confirmatory", range(240, 260), (0, 15), (1.0, 0.25)),
    ):
        cells = []
        for delay in delays:
            for availability in avails:
                rows = [audit_seed(seed, delay, availability) for seed in seeds]
                cells.append({"delay": delay, "availability": availability,
                              "summary": _cell_summary(rows), "per_seed": rows})
        out["splits"][split] = {"seeds": list(seeds), "cells": cells}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True,
                        help="new JSON file; existing paths are never overwritten")
    args = parser.parse_args(argv)
    payload = json.dumps(build_report(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    try:
        with args.out.open("x") as target:
            target.write(payload)
    except OSError as exc:
        parser.exit(2, f"feedback audit: {exc}\n")


if __name__ == "__main__":
    main()
