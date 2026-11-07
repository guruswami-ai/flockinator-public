"""Unregistered matched-control implementation for feedback-trust proposal #172.

The sequence API evaluates supplied inputs. The CLI only checks compatibility on
already exposed historical seeds; it cannot register or launch a fresh study.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random

from .feedback_trust import score_sequence_feedback
from .relay_attack import NODES
from .reputation import generate_sequence

ARMS = {"L1": (True, 1.0), "F1": (False, 1.0),
        "L2": (True, 2.0), "F2": (False, 2.0)}


def _validate(seq, delay, availability, reveal_seed, start, stop):
    if not isinstance(seq, (list, tuple)):
        raise ValueError("sequence must be a list or tuple")
    if type(delay) is not int or delay < 0:
        raise ValueError("delay must be a nonnegative integer")
    if type(availability) not in (int, float) or not 0 <= availability <= 1 or not math.isfinite(availability):
        raise ValueError("availability must be finite and in [0,1]")
    if type(reveal_seed) is not int:
        raise ValueError("reveal_seed must be an integer")
    if not (type(start) is int and type(stop) is int and 0 <= start < stop <= len(seq)):
        raise ValueError("invalid evaluation window")
    for i, contact in enumerate(seq):
        if not isinstance(contact, dict):
            raise ValueError("each contact must be an object")
        if type(contact.get("contact")) is not int or contact["contact"] != i:
            raise ValueError("contacts must be contiguous, ordered and zero-based")
        if contact.get("truth") not in ("survivor", "hazard"):
            raise ValueError("unknown truth class")
        if not isinstance(contact.get("reports"), (list, tuple)):
            raise ValueError("reports must be a list or tuple")
        for report in contact["reports"]:
            if (not isinstance(report, (list, tuple)) or len(report) != 5 or not isinstance(report[0], str) or not report[0]
                    or report[1] not in NODES or report[3] not in ("survivor", "hazard")):
                raise ValueError("invalid historical report tuple")


def _metrics(seq, decisions, start, stop):
    rows = list(zip(seq[start:stop], decisions[start:stop]))
    hazards = sum(c["truth"] == "hazard" for c, _ in rows)
    survivors = len(rows)-hazards
    dangerous = sum(ok and c["truth"] == "hazard" for c, ok in rows)
    found = sum(ok and c["truth"] == "survivor" for c, ok in rows)
    commits = dangerous+found
    return {"contacts": len(rows), "hazards": hazards, "survivors": survivors,
            "dangerous": dangerous, "found": found, "commits": commits,
            "abstentions": len(rows)-commits,
            "harm_rate": dangerous/hazards if hazards else None,
            "recall": found/survivors if survivors else None,
            "coverage": commits/len(rows)}


def _difference(candidate, reference):
    return {key: candidate[key]-reference[key] if candidate[key] is not None and reference[key] is not None else None
            for key in ("dangerous", "found", "commits", "harm_rate", "recall", "coverage")}


def score_sequence_matched(seq, delay=0, availability=1.0, reveal_seed=0,
                           start=30, stop=60):
    """Run the 2x2 arms on exactly one supplied sequence and reveal schedule.

No caller object is mutated. Current truth enters the update queue only after
all four current decisions; future truth cannot affect an earlier decision.
Frozen arms receive the same events, but apply no weight changes. Report-ID
first-occurrence deduplication and update ordering match the historical runner.
"""
    _validate(seq, delay, availability, reveal_seed, start, stop)
    rng = random.Random(reveal_seed)
    reveal_mask = [rng.random() < availability for _ in seq]
    weights = {arm: {node: 1.0 for node in NODES} for arm in ARMS}
    decisions = {arm: [] for arm in ARMS}
    pending = []
    applied_counts = []
    offered = 0

    def apply(events):
        for _, node, correct in events:
            for arm, (learned, _) in ARMS.items():
                if learned:
                    weights[arm][node] = min(1.0, max(0.1, weights[arm][node]
                                                    + (0.05 if correct else -0.15)))

    for i, contact in enumerate(seq):
        due = [event for event in pending if event[0] <= i]
        apply(due)
        applied_counts.append(len(due))
        pending = [event for event in pending if event[0] > i]
        pool = {}
        for report in contact["reports"]:
            pool.setdefault(report[0], report)
        pool = list(pool.values())
        for arm, (_, margin) in ARMS.items():
            survivor = sum(weights[arm][r[1]] for r in pool if r[3] == "survivor")
            hazard = sum(weights[arm][r[1]] for r in pool if r[3] == "hazard")
            decisions[arm].append(survivor >= 1.5 and survivor-hazard >= margin)
        if reveal_mask[i]:
            offered += len(pool)
            pending.extend((i+delay, r[1], r[3] == contact["truth"]) for r in pool)
    flush = len(pending)
    apply(sorted(pending))  # diagnostic final state; never feeds an earlier decision
    before = sum(applied_counts)
    arms = {}
    for arm, (learned, margin) in ARMS.items():
        arms[arm] = {
            "updating": learned, "survivor_floor": 1.5, "margin": margin,
            "decision_log": decisions[arm],
            "metrics": _metrics(seq, decisions[arm], start, stop),
            "processed_report_reveals_before_decisions": before,
            "weight_update_applications_before_decisions": before if learned else 0,
            "weight_update_applications_in_window": sum(applied_counts[start:stop]) if learned else 0,
            "weight_update_applications_in_final_flush": flush if learned else 0,
            "final_weights_after_flush": weights[arm],
        }
    contrasts = {name: _difference(arms[left]["metrics"], arms[right]["metrics"])
                 for name, left, right in (("L1_minus_F1", "L1", "F1"),
                                           ("L2_minus_F2", "L2", "F2"),
                                           ("L2_minus_L1", "L2", "L1"))}
    contrasts["updating_by_margin_interaction"] = _difference(
        contrasts["L2_minus_F2"], contrasts["L1_minus_F1"])
    return {
        "schema": "flockinator-feedback-matched/1", "status": "unregistered_implementation",
        "window": {"start_inclusive": start, "stop_exclusive": stop},
        "reveal_mask": reveal_mask,
        "shared_budget": {"outcome_draws": len(seq), "selected_outcomes": sum(reveal_mask),
                          "offered_report_updates": offered,
                          "applications_before_each_decision": applied_counts,
                          "post_horizon_flush": flush},
        "arms": arms, "paired_contrasts": contrasts,
    }


def historical_smoke():
    """Compatibility checks only; no scientific result table or acceptance test."""
    comparisons = 0
    for seed in range(220, 260):
        seq = generate_sequence(seed)
        for delay, availability in ((0, 1.0), (15, 0.25)):
            out = score_sequence_matched(seq, delay, availability, seed ^ 0xFEED)
            rep = score_sequence_feedback(seq, "REP", delay, availability, seed ^ 0xFEED)
            strict = score_sequence_feedback(seq, "E", delay, availability, seed ^ 0xFEED)
            frozen = score_sequence_feedback(seq, "REP", delay, 0.0, seed ^ 0xFEED)
            for arm, reference in (("L1", rep), ("F2", strict), ("F1", frozen)):
                if out["arms"][arm]["decision_log"] != reference["decision_log"]:
                    raise ValueError(f"historical compatibility failed: {seed}, {arm}")
                if out["arms"][arm]["metrics"]["dangerous"] != reference["dangerous_second"]:
                    raise ValueError("second-half denominator/window mismatch")
                comparisons += 1
            budget = out["shared_budget"]
            if sum(budget["applications_before_each_decision"])+budget["post_horizon_flush"] != budget["offered_report_updates"]:
                raise ValueError("shared reveal budget mismatch")
    package = Path(__file__).parent
    return {"status": "historical_compatibility_only_not_a_study_result",
            "exposed_seeds": list(range(220, 260)), "sequences_checked": 80,
            "historical_arm_comparisons": comparisons,
            "source_sha256": {name: hashlib.sha256((package/name).read_bytes()).hexdigest()
                              for name in ("feedback_matched.py", "feedback_trust.py", "reputation.py", "relay_attack.py")}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-smoke", action="store_true", required=True)
    parser.add_argument("--out", type=Path, required=True, help="new JSON path; never overwritten")
    args = parser.parse_args(argv)
    payload = json.dumps(historical_smoke(), indent=2, sort_keys=True, allow_nan=False)+"\n"
    try:
        with args.out.open("x") as target:
            target.write(payload)
    except OSError as exc:
        parser.exit(2, f"matched compatibility: {exc}\n")


if __name__ == "__main__":
    main()
