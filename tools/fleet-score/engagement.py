#!/usr/bin/env python3
"""Audit prospective liar-treatment instrumentation; never emits a gate PASS.

See ENGAGEMENT.md for the versioned evidence contract. Independent of score.py
and gate_runner.py: a counted commit is not evidence of treatment engagement.
"""
import argparse
import json
import pathlib
import sys

SCHEMA = "flockinator-treatment-evidence/1"
AUDIT_SCHEMA = "flockinator-engagement-audit/1"
LABELS = {"hazard", "survivor"}


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


def audit(evidence):
    """Validate one run's instrumentation and count eligible/applied events.

    Completeness and intervention flags are producer attestations, not proved
    by this checker. Never infer them from ordinary commits or wrong labels.
    """
    if not isinstance(evidence, dict) or evidence.get("schema") != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA}")
    run = _text(evidence.get("run"), "run")
    seed = _integer(evidence.get("seed"), "seed")
    treatment = evidence.get("treatment")
    if treatment not in ("T3", "T4"):
        raise ValueError("treatment must be T3 or T4")
    designated = _text(evidence.get("designated_unit"), "designated_unit")
    start = _integer(evidence.get("start_turn"), "start_turn")
    if treatment == "T3" and start != 0:
        raise ValueError("T3 start_turn must be zero")
    if type(evidence.get("complete")) is not bool:
        raise ValueError("complete must be a boolean")
    observations = evidence.get("observations")
    if not isinstance(observations, list):
        raise ValueError("observations must be a list (including when empty)")
    ids = set()
    opportunities = applied = changed = 0
    for row in observations:
        if not isinstance(row, dict):
            raise ValueError("each observation must be an object")
        identity = _text(row.get("id"), "observation id")
        if identity in ids:
            raise ValueError(f"duplicate observation id {identity!r}")
        ids.add(identity)
        unit = _text(row.get("unit"), "unit")
        turn = _integer(row.get("turn"), "turn")
        for key in ("truth", "untreated_label", "treated_label"):
            if not isinstance(row.get(key), str) or row[key] not in LABELS:
                raise ValueError(f"{key} must be hazard or survivor")
        if type(row.get("applied")) is not bool:
            raise ValueError("applied must be a boolean")
        eligible = (unit == designated and row["truth"] == "hazard"
                    and turn >= start)
        opportunities += eligible
        if row["applied"]:
            if not eligible or row["treated_label"] != "survivor":
                raise ValueError("applied intervention outside eligible hazard-to-survivor scope")
            applied += 1
            changed += row["untreated_label"] != row["treated_label"]
        elif row["untreated_label"] != row["treated_label"]:
            raise ValueError("label changed without an applied intervention")
    if not evidence["complete"]:
        status = "UNMEASURED"
    elif not opportunities:
        status = "NO_OPPORTUNITY"
    elif not applied:
        status = "NOT_EXERCISED"
    else:
        status = "ENGAGED"
    return {"schema": AUDIT_SCHEMA, "run": run, "seed": seed,
            "treatment": treatment, "designated_unit": designated,
            "start_turn": start, "complete": evidence["complete"],
            "observations": len(observations), "opportunities": opportunities,
            "applied": applied, "labels_changed": changed, "status": status}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        result = audit(json.loads(args.evidence.read_text()))
    except (OSError, ValueError) as exc:
        print(json.dumps({"schema": AUDIT_SCHEMA, "status": "ERROR",
                          "error": str(exc)}, sort_keys=True))
        return 3
    print(json.dumps(result, indent=2, sort_keys=True))
    # Success means internally valid and exercised evidence, not policy success.
    return 0 if result["status"] == "ENGAGED" else 2


if __name__ == "__main__":
    sys.exit(main())
