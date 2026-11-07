"""Single-attempt structured fault-task tracing; no network or credentials.

The injected callable receives immutable JSON text and returns allowlisted
metadata. These records show what this wrapper observed, not provider attestation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

SCHEMA = "flockinator-model-trace/1"
CELLS = tuple(f"{r}{c}" for r in "ABCD" for c in range(1, 5))
INSTRUCTION = ("Compare the reference and observed RGB grids. Identify cells with "
               "a display difference and return their A1..D4 labels as detected_nodes. "
               "These grids do not establish mission truth.")
ERROR_CODES = {"provider_error", "transport_error", "timeout", "invalid_response",
               "invoke_exception"}


def _keys(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise ValueError("unexpected or missing fields")


def _label(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", value):
        raise ValueError(f"invalid {name}")
    return value


def _number(value, name, maximum=None, integer=False):
    if type(value) not in (int, float) or (integer and type(value) is not int):
        raise ValueError(f"invalid {name}")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value < 0 or (maximum is not None and value > maximum):
        raise ValueError(f"invalid {name}")
    return value


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _decode(raw):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("duplicate JSON object key")
            obj[key] = value
        return obj
    return json.loads(raw, object_pairs_hook=unique)


def validate_request(request):
    _keys(request, ("schema", "trial_id", "requested_model", "parameters", "instruction", "case"))
    if request["schema"] != SCHEMA or request["instruction"] != INSTRUCTION:
        raise ValueError("unsupported schema or instruction")
    for key in ("trial_id", "requested_model"):
        _label(request[key], key)
    parameters = request["parameters"]
    allowed = {"temperature", "top_p", "max_output_tokens", "seed"}
    if not isinstance(parameters, dict) or set(parameters) - allowed:
        raise ValueError("unsupported parameters")
    for key, value in parameters.items():
        maximum = 2 if key == "temperature" else 1 if key == "top_p" else None
        _number(value, key, maximum, integer=key in ("seed", "max_output_tokens"))
        if key == "max_output_tokens" and value == 0:
            raise ValueError("max_output_tokens must be positive")
    case = request["case"]
    _keys(case, ("case_id", "reference_rgb", "observed_rgb"))
    _label(case["case_id"], "case_id")
    for field in ("reference_rgb", "observed_rgb"):
        grid = case[field]
        if not isinstance(grid, dict) or set(grid) != set(CELLS):
            raise ValueError("grid must contain exactly A1..D4")
        for rgb in grid.values():
            if not isinstance(rgb, list) or len(rgb) != 3:
                raise ValueError("RGB requires three numbers")
            for value in rgb:
                _number(value, "RGB", 255)


def fault_request(trial_id, requested_model, parameters, case):
    request = {"schema": SCHEMA, "trial_id": trial_id, "requested_model": requested_model,
               "parameters": parameters, "instruction": INSTRUCTION, "case": case}
    validate_request(request)
    # Snapshot caller-owned structures; mutation later cannot rewrite this task.
    return _decode(_json(request))


def _response(response):
    _keys(response, ("status", "detected_nodes", "reported_model", "usage",
                     "cost_usd", "cost_source", "error_code"))
    if response["status"] not in ("completed", "error"):
        raise ValueError("invalid response status")
    nodes = response["detected_nodes"]
    if (not isinstance(nodes, list) or any(n not in CELLS for n in nodes)
            or len(set(nodes)) != len(nodes)):
        raise ValueError("invalid detected_nodes")
    if response["status"] == "error":
        if nodes or response["error_code"] not in ERROR_CODES:
            raise ValueError("error needs an allowed code and empty predictions")
    elif response["error_code"] is not None:
        raise ValueError("completed response cannot carry an error code")
    if response["reported_model"] is not None:
        _label(response["reported_model"], "reported_model")
    usage = response["usage"]
    if usage is not None:
        _keys(usage, ("input_tokens", "output_tokens"))
        for value in usage.values():
            if value is not None:
                _number(value, "usage", integer=True)
    if response["cost_usd"] is None:
        if response["cost_source"] is not None:
            raise ValueError("unavailable cost needs a null source")
    else:
        _number(response["cost_usd"], "cost_usd")
        if response["cost_source"] not in ("provider_reported", "adapter_estimated"):
            raise ValueError("cost source must distinguish reported and estimated")
    return _decode(_json(response))


def _failure(code):
    return {"status": "error", "detected_nodes": [], "reported_model": None,
            "usage": None, "cost_usd": None, "cost_source": None, "error_code": code}


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("invalid timestamp")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must have UTC offset")


def _write(path, raw):
    # Exclusive creation prevents evidence from being replaced by a concurrent writer.
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def run_attempt(directory, request, invoke, *, evidence_kind):
    """Invoke once, recording start before the call and a bounded result afterward.

    invoke(request_json_text) must return _response's exact structured contract.
    It owns provider transport, credentials and extraction; no retry is performed
    here. Exceptions lose unreported usage/cost rather than inventing zero cost.
    KeyboardInterrupt/SystemExit propagate and leave an incomplete attempt.
    """
    validate_request(request)
    if evidence_kind not in ("synthetic_test", "observed"):
        raise ValueError("evidence_kind must be synthetic_test or observed")
    raw_request = _json(request).encode()
    directory = Path(directory)
    directory.mkdir(mode=0o700, exist_ok=False)
    _write(directory / "request.json", raw_request)
    start = {"schema": SCHEMA, "evidence_kind": evidence_kind,
             "started_at": _utc(), "request_sha256": _hash(raw_request)}
    raw_start = _json(start).encode()
    _write(directory / "start.json", raw_start)
    before = time.monotonic()
    try:
        response = invoke(raw_request.decode())
    except Exception:
        # Never store free-form exception messages (URLs, headers and secrets can leak).
        response = _failure("invoke_exception")
    else:
        try:
            response = _response(response)
        except (ValueError, TypeError, OverflowError):
            response = _failure("invalid_response")
    elapsed = time.monotonic() - before
    _number(elapsed, "elapsed_seconds")
    outcome = {"schema": SCHEMA, "request_sha256": _hash(raw_request),
               "start_sha256": _hash(raw_start), "finished_at": _utc(),
               "elapsed_seconds": elapsed, "response": response}
    _write(directory / "outcome.json", _json(outcome).encode())
    return verify(directory)


def verify(directory):
    """Verify internal binding; missing outcome is INCOMPLETE, never success."""
    directory = Path(directory)
    names = {p.name for p in directory.iterdir()}
    if names - {"request.json", "start.json", "outcome.json"}:
        raise ValueError("unexpected trace files")
    def read(name):
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or non-regular trace file")
        return path.read_bytes()
    raw_request, raw_start = read("request.json"), read("start.json")
    request, start = _decode(raw_request), _decode(raw_start)
    validate_request(request)
    _keys(start, ("schema", "evidence_kind", "started_at", "request_sha256"))
    if (start["schema"] != SCHEMA or start["request_sha256"] != _hash(raw_request)
            or start["evidence_kind"] not in ("synthetic_test", "observed")):
        raise ValueError("invalid start binding")
    _timestamp(start["started_at"])
    summary = {"schema": SCHEMA, "trial_id": request["trial_id"],
               "requested_model": request["requested_model"],
               "evidence_kind": start["evidence_kind"], "status": "INCOMPLETE",
               "request_sha256": _hash(raw_request), "start_sha256": _hash(raw_start)}
    if "outcome.json" not in names:
        return summary
    raw_outcome = read("outcome.json")
    outcome = _decode(raw_outcome)
    _keys(outcome, ("schema", "request_sha256", "start_sha256", "finished_at",
                    "elapsed_seconds", "response"))
    if (outcome["schema"] != SCHEMA or outcome["request_sha256"] != _hash(raw_request)
            or outcome["start_sha256"] != _hash(raw_start)):
        raise ValueError("invalid outcome binding")
    _timestamp(outcome["finished_at"])
    _number(outcome["elapsed_seconds"], "elapsed_seconds")
    response = _response(outcome["response"])
    return {**summary, "status": response["status"].upper(), "response": response,
            "elapsed_seconds": outcome["elapsed_seconds"], "outcome_sha256": _hash(raw_outcome)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", help="existing attempt directory to verify")
    args = parser.parse_args(argv)
    try:
        summary = verify(args.directory)
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        # No paths or parser exception content in the public status output.
        parser.exit(3, "trace verification failed\n")
    print(json.dumps(summary, indent=2, allow_nan=False))
    return 0 if summary["status"] == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
