"""Record one Meta build-assistant request; never execute model output.

Python standard library only. Supply MODEL_API_KEY in the process environment.
The input and output directories must contain public-safe material. This records
client observations, not cryptographic provider attestation or build success.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import time

HOST = "api.meta.ai"
ENDPOINT = "/v1/responses"
MAX_BYTES = 8 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def scrub(value, key):
    """Inspect decoded strings, including JSON object keys and nested usage fields."""
    if isinstance(value, str):
        return value.replace(key, "[REDACTED]")
    if isinstance(value, list):
        return [scrub(item, key) for item in value]
    if isinstance(value, dict):
        return {scrub(name, key): scrub(item, key) for name, item in value.items()}
    return value


def record(request_path, output, *, connection_factory=http.client.HTTPSConnection):
    key = os.environ.get("MODEL_API_KEY", "")
    if not key:
        raise ValueError("MODEL_API_KEY is required")
    raw = Path(request_path).read_bytes()
    if len(raw) > MAX_BYTES or key.encode() in raw:
        raise ValueError("request too large or contains the credential")
    request = json.loads(raw, object_pairs_hook=unique)
    if scrub(request, key) != request:
        raise ValueError("request contains the credential")
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    if set(request) - {"model", "input", "instructions", "reasoning", "max_output_tokens", "store"}:
        raise ValueError("unsupported request field")
    if request.get("model") not in {"muse-spark-1.3-contributor", "muse-spark-1.3", "muse-wonder-1.0"}:
        raise ValueError("unsupported model")
    if request.get("store") is not False:
        raise ValueError("explicit store:false required")
    if type(request.get("max_output_tokens")) is not int or not 1 <= request["max_output_tokens"] <= 16384:
        raise ValueError("bounded max_output_tokens required")
    output = Path(output)
    output.mkdir(parents=False, exist_ok=False)
    (output / "request.json").write_bytes(raw)
    meta = {"schema": "flockinator-meta-build-call/1", "endpoint": "https://" + HOST + ENDPOINT,
            "started_at": utc(), "requested_model": request["model"],
            "request_sha256": digest(raw), "attempts": 1, "automatic_retries": 0,
            "http_status": None, "provider_request_id": None, "outcome": "started"}
    (output / "started.json").write_text(json.dumps(meta, indent=2) + "\n")
    start = time.monotonic()
    conn = None
    try:
        conn = connection_factory(HOST, timeout=180)
        # http.client performs no automatic redirects or retries.
        conn.request("POST", ENDPOINT, body=raw,
                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        response = conn.getresponse()
        meta["http_status"] = response.status
        headers = {name: response.getheader(name) for name in ("content-type", "date", "x-request-id", "request-id")}
        # Header values are provider-controlled; never persist a reflected key.
        headers = {name: value.replace(key, "[REDACTED]") if value else value for name, value in headers.items()}
        meta["response_headers"] = headers
        meta["provider_request_id"] = headers["x-request-id"] or headers["request-id"]
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            meta["outcome"] = "response_too_large"
            return False
        try:
            parsed = json.loads(body, object_pairs_hook=unique)
        except (ValueError, UnicodeError):
            # An ambiguous/malformed envelope cannot be safely inspected. Do not
            # persist it: escaped credential text may bypass a raw-byte check.
            meta["outcome"] = "invalid_response"
            return False
        if not isinstance(parsed, dict):
            meta["outcome"] = "invalid_response"
            return False
        sanitized = scrub(parsed, key)
        redacted = sanitized != parsed or key.encode() in body
        if redacted:
            parsed = sanitized
            body = json.dumps(parsed, ensure_ascii=True).encode()
        # Safe envelopes retain their exact wire bytes; altered ones are marked
        # as redacted failures, and their hashes describe the sanitized bytes.
        (output / "response.json").write_bytes(body)
        meta["response_sha256"] = digest(body)
        meta["credential_redacted"] = redacted
        meta["reported_model"] = parsed.get("model")
        meta["response_id"] = parsed.get("id")
        meta["usage"] = parsed.get("usage")
        meta["provider_status"] = parsed.get("status")
        ok = 200 <= response.status < 300 and parsed.get("status") == "completed" and not redacted
        meta["outcome"] = "completed" if ok else "provider_failure"
        return ok
    except Exception as exc:
        # Exception text can contain provider-controlled content. Keep only type.
        meta["outcome"] = "transport_failure"
        meta["exception_type"] = type(exc).__name__
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                meta["close_failed"] = True
        meta["finished_at"] = utc()
        meta["elapsed_seconds"] = round(time.monotonic() - start, 6)
        (output / "receipt.json").write_text(json.dumps(scrub(meta, key), indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        ok = record(args.request, args.out)
    except (ValueError, OSError):
        parser.exit(2, "Invalid request, missing credential, or output path unavailable.\n")
    print("Call completed; inspect receipt and response." if ok else "Call failed; inspect receipt. No retry performed.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
