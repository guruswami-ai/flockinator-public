"""Offline, scheduled-trial fault-localisation scoring; no devices or model calls.

See docs/research/fault-evaluation-tooling.md. Unknown/missing attempts cannot
silently improve accuracy by disappearing from its denominator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

CELLS = tuple(f"{row}{col}" for row in "ABCD" for col in range(1, 5))
SCHEMA = "flockinator-fault-eval/1"


def _number(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return value


def _id(value):
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError("IDs must be nonempty strings of at most 128 characters")
    return value


def _nodes(value):
    if not isinstance(value, list) or any(x not in CELLS for x in value):
        raise ValueError("nodes must be a list of A1..D4 labels")
    if len(value) != len(set(value)):
        raise ValueError("duplicate node label")
    return set(value)


def _keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys():
        raise ValueError(f"required fields: {sorted(required)}")
    if value.keys() - set(required) - set(optional):
        raise ValueError("unknown fields (keep truth/annotations outside observer inputs)")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def score(protocol, answers, responses):
    """Score every preassigned trial, then compare arm means within each unit.

    unit_id is a participant for human trials, an independent case/block for
    automated trials. Trial and tick rows are not independent replicates.
    """
    _keys(protocol, ("schema", "evidence_kind", "arms", "assignments"))
    if protocol["schema"] != SCHEMA:
        raise ValueError("unsupported protocol schema")
    if protocol["evidence_kind"] not in ("synthetic_smoke", "observed"):
        raise ValueError("evidence_kind must be synthetic_smoke or observed")
    arms = protocol["arms"]
    if not isinstance(arms, list) or len(arms) < 2:
        raise ValueError("at least two arms required; first is reference")
    if len(set(map(_id, arms))) != len(arms):
        raise ValueError("duplicate arm")
    _keys(answers, ("schema", "cases"))
    if answers["schema"] != SCHEMA or not isinstance(answers["cases"], dict):
        raise ValueError("invalid answer schema")
    truth = {_id(k): _nodes(v) for k, v in answers["cases"].items()}
    assignments = protocol["assignments"]
    if not isinstance(assignments, list) or not assignments:
        raise ValueError("nonempty assignments required")
    plan = {}
    seen = set()
    for a in assignments:
        _keys(a, ("trial_id", "unit_id", "case_id", "arm", "timeout_seconds"))
        trial = _id(a["trial_id"])
        unit, case = _id(a["unit_id"]), _id(a["case_id"])
        if trial in plan or (unit, case, a["arm"]) in seen:
            raise ValueError("duplicate trial or unit/case/arm assignment")
        if a["arm"] not in arms or case not in truth:
            raise ValueError("unknown arm or case")
        if _number(a["timeout_seconds"], "timeout_seconds") <= 0:
            raise ValueError("timeout must be positive")
        plan[trial] = a
        seen.add((unit, case, a["arm"]))
    if set(truth) != {a["case_id"] for a in assignments}:
        raise ValueError("answer cases must exactly match assigned cases")
    if not isinstance(responses, list):
        raise ValueError("responses must be a list")
    submitted = {}
    for r in responses:
        _keys(r, ("trial_id", "status", "detected_nodes", "elapsed_seconds"))
        trial = _id(r["trial_id"])
        if trial not in plan or trial in submitted:
            raise ValueError("unknown or duplicate response; do not select best retry")
        if r["status"] not in ("completed", "timeout", "error"):
            raise ValueError("invalid response status")
        _nodes(r["detected_nodes"])
        _number(r["elapsed_seconds"], "elapsed_seconds")
        if r["status"] != "completed" and r["detected_nodes"]:
            raise ValueError("failed responses must have empty detected_nodes")
        submitted[trial] = r
    rows = []
    for trial, a in plan.items():
        expected, deadline = truth[a["case_id"]], a["timeout_seconds"]
        r = submitted.get(trial)
        status = r["status"] if r else "missing"
        if r and r["elapsed_seconds"] > deadline:
            status = "timeout"
        complete = status == "completed"
        reported = _nodes(r["detected_nodes"]) if complete else set()
        correct = complete and reported == expected
        rows.append({**a, "status": status, "fault_present": bool(expected),
                     "exact_correct": correct,
                     "fault_detected": bool(expected) and complete and bool(reported),
                     "false_alarm": not expected and complete and bool(reported),
                     "reported_nodes": sorted(reported),
                     "capped_time_to_correct_localisation":
                         (r["elapsed_seconds"] if correct else deadline) if expected else None})

    def aggregate(selected):
        faults = [r for r in selected if r["fault_present"]]
        clean = [r for r in selected if not r["fault_present"]]
        ratio = lambda n, d: n / d if d else None
        return {"scheduled": len(selected),
                "completed": sum(r["status"] == "completed" for r in selected),
                "status_counts": {s: sum(r["status"] == s for r in selected)
                                  for s in ("completed", "timeout", "error", "missing")},
                "exact_correct": sum(r["exact_correct"] for r in selected),
                "exact_accuracy": ratio(sum(r["exact_correct"] for r in selected), len(selected)),
                "fault_trials": len(faults), "clean_trials": len(clean),
                "fault_detection_rate": ratio(sum(r["fault_detected"] for r in faults), len(faults)),
                "fault_localisation_rate": ratio(sum(r["exact_correct"] for r in faults), len(faults)),
                "false_alarm_rate": ratio(sum(r["false_alarm"] for r in clean), len(clean)),
                "clean_correct_rate": ratio(sum(r["exact_correct"] for r in clean), len(clean)),
                "mean_capped_time_to_correct_localisation": ratio(
                    sum(r["capped_time_to_correct_localisation"] for r in faults), len(faults))}

    by_arm = {arm: aggregate([r for r in rows if r["arm"] == arm]) for arm in arms}
    units = sorted({r["unit_id"] for r in rows})
    by_unit = {u: {arm: aggregate([r for r in rows if r["unit_id"] == u and r["arm"] == arm])
                   for arm in arms} for u in units}
    paired = {}
    for arm in arms[1:]:
        diffs = []
        for u in units:
            a, b = by_unit[u][arms[0]], by_unit[u][arm]
            if not a["scheduled"] or not b["scheduled"]:
                raise ValueError("each unit needs scheduled trials in every arm")
            diffs.append({"unit_id": u, "difference": b["exact_accuracy"] - a["exact_accuracy"]})
        mean = sum(d["difference"] for d in diffs) / len(diffs)
        # Hoeffding: independent bounded [-1,1] unit differences. Pointwise,
        # conservative; NOT a registered acceptance test or multiplicity fix.
        radius = math.sqrt(2 * math.log(2 / 0.05) / len(diffs))
        paired[arm] = {"reference": arms[0], "units": len(diffs), "per_unit": diffs,
                       "mean_exact_accuracy_difference": mean,
                       "pointwise_95pct_hoeffding_interval":
                           [max(-1, mean-radius), min(1, mean+radius)]}
    return {"schema": SCHEMA, "evidence_kind": protocol["evidence_kind"],
            "inference_assumption": "independent units; pointwise intervals, no causal or benefit verdict",
            "arms": by_arm, "units": by_unit, "paired": paired, "trials": rows}


def baseline(cases, threshold):
    """RGB-distance baseline over supplied expected/observed per-cell grids.

    Expected grids must be available equally to all arms. This detects display
    differences only, not mission correctness or independent sensor truth.
    """
    _number(threshold, "threshold")
    output = []
    if not isinstance(cases, list) or not cases:
        raise ValueError("nonempty cases required")
    ids = set()
    for case in cases:
        _keys(case, ("case_id", "reference_rgb", "observed_rgb"))
        key = _id(case["case_id"])
        if key in ids:
            raise ValueError("duplicate case")
        ids.add(key)
        for field in ("reference_rgb", "observed_rgb"):
            grid = case[field]
            if not isinstance(grid, dict) or set(grid) != set(CELLS):
                raise ValueError("grid must contain exactly A1..D4")
            for rgb in grid.values():
                if not isinstance(rgb, list) or len(rgb) != 3:
                    raise ValueError("RGB must be a three-element list")
                if any(_number(v, "RGB") > 255 for v in rgb):
                    raise ValueError("RGB outside 0..255")
        nodes = [cell for cell in CELLS if math.dist(case["reference_rgb"][cell],
                                                   case["observed_rgb"][cell]) > threshold]
        output.append({"case_id": key, "detected_nodes": nodes})
    return output


def demo(out):
    """Small disclosed synthetic fixture, never an evaluation dataset."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    public, private = out / "observer", out / "evaluator"
    public.mkdir()
    private.mkdir()
    cases, truth, assignments, responses = [], {}, [], []
    for i, affected in enumerate(([], ["A1"], ["D4"], ["B2", "C3"])):
        cid = f"case-{i+1:03}"
        reference = {c: [80, 80, 80] for c in CELLS}
        observed = {c: ([160, 80, 80] if c in affected else [80, 80, 80]) for c in CELLS}
        cases.append({"case_id": cid, "reference_rgb": reference, "observed_rgb": observed})
        truth[cid] = affected
        for arm in ("reference", "candidate"):
            trial = f"trial-{len(assignments)+1:03}"
            assignments.append({"trial_id": trial, "case_id": cid, "unit_id": "smoke-block",
                                "arm": arm, "timeout_seconds": 30})
            responses.append({"trial_id": trial, "status": "completed", "detected_nodes": affected,
                              "elapsed_seconds": 1})
    files = {public / "cases.json": cases,
             private / "answers.json": {"schema": SCHEMA, "cases": truth},
             private / "protocol.json": {"schema": SCHEMA, "evidence_kind": "synthetic_smoke",
                                          "arms": ["reference", "candidate"], "assignments": assignments},
             private / "responses.json": responses}
    for path, payload in files.items():
        path.write_text(json.dumps(payload, indent=2) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo_parser = sub.add_parser("demo")
    demo_parser.add_argument("--out", required=True)
    base_parser = sub.add_parser("baseline")
    base_parser.add_argument("--cases", required=True)
    base_parser.add_argument("--threshold", type=float, required=True)
    base_parser.add_argument("--out", required=True)
    score_parser = sub.add_parser("score")
    for field in ("protocol", "answers", "responses", "out"):
        score_parser.add_argument(f"--{field}", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            demo(args.out)
            return 0
        fields = ("cases",) if args.command == "baseline" else ("protocol", "answers", "responses")
        paths = [Path(getattr(args, f)) for f in fields]
        out = Path(args.out)
        if out.exists():
            raise ValueError("output already exists; use a fresh path")
        raw = [p.read_bytes() for p in paths]
        data = [json.loads(b, object_pairs_hook=_unique_object) for b in raw]
        result = baseline(data[0], args.threshold) if args.command == "baseline" else score(*data)
        result = {"schema": SCHEMA, "command": args.command,
                  "parameters": {"threshold": args.threshold} if args.command == "baseline" else {},
                  "result": result, "input_sha256":
                  {field: hashlib.sha256(b).hexdigest() for field, b in zip(fields, raw)}}
        serialized = json.dumps(result, indent=2, allow_nan=False) + "\n"
        with out.open("x") as handle:
            handle.write(serialized)
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
