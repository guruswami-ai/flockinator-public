"""Regenerate response_auth_v1.json, the golden vectors shared with the firmware C++ tests.

Deterministic and dependency-free: synthetic key, fixed challenges, no devices. Run with
``uv run python tests/vectors/make_response_auth_vectors.py`` from tools/node-commissioner.
The canonical string is spelled out here from firmware/shared/management/response_auth.h
rather than imported from node_commissioner.response_auth, so the host module is checked
against this file (test_response_auth.py) and the C++ header is checked against it too
(test_response_auth_cxx.py). Agreement of all three is the interoperability evidence.
"""
import hashlib
import hmac
import json
from pathlib import Path

KEY = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
MAC = "00:11:22:33:44:55"
NONCE = "0123456789abcdef0123456789abcdef"
EMPTY = hashlib.sha256(b"").hexdigest()
OUT = Path(__file__).with_name("response_auth_v1.json")


def request_signature(method, path, body, count, mac=MAC, nonce=NONCE, key=KEY):
    digest = hashlib.sha256(body).hexdigest()
    message = f"v1\n{nonce}\n{count}\n{mac}\n{method}\n{path}\n{digest}".encode()
    return digest, hmac.new(key, message, hashlib.sha256).hexdigest()


def case(name, challenge, method, path, status, body, request_body=None, count=None, node=MAC, key=KEY, note=""):
    if path == "/v1/challenge":
        request_hash, nonce, count, signature = EMPTY, "-", "0", "-"
    else:
        request_hash, signature = request_signature(method, path, request_body, count, mac=node, key=key)
        nonce = NONCE
    binding = dict(challenge=challenge, node=node, method=method, path=path, request_hash=request_hash,
                   nonce=nonce, count=count, request_signature=signature)
    body_sha256 = hashlib.sha256(body).hexdigest()
    canonical = "flock-management-response-v1\n" + "\n".join(binding[k] for k in (
        "challenge", "node", "method", "path", "request_hash", "nonce", "count", "request_signature")) + f"\n{status}\n{body_sha256}"
    return dict(name=name, note=note, key_hex=key.hex(), binding=binding, status=status, body_hex=body.hex(),
                body_text=body.decode("ascii") if all(32 <= b < 127 or b == 10 for b in body) else None,
                body_sha256=body_sha256, canonical=canonical,
                signature=hmac.new(key, canonical.encode("ascii"), hashlib.sha256).hexdigest())


def main():
    challenge_body = json.dumps(dict(v=1, base_mac=MAC, nonce=NONCE, next_counter=1, key_id="0123456789abcdef", configured=True), separators=(",", ":")).encode()
    status_body = json.dumps(dict(type="status", v=1, base_mac=MAC, label="A1", boot_count=5, firmware="0.9.0"), separators=(",", ":")).encode()
    journal = b'{"tick":1,"state":"WAIT"}\n{"tick":2,"state":"COMMIT"}\n'
    journal_id = hashlib.sha256(journal).hexdigest()
    cases = [
        case("challenge-get-200", "11" * 16, "GET", "/v1/challenge", 200, challenge_body, note="Initial unauthenticated-request exchange; nonce/count/signature placeholders"),
        case("status-get-200", "22" * 16, "GET", "/v1/status", 200, status_body, request_body=b"", count="1"),
        case("status-get-401-html", "33" * 16, "GET", "/v1/status", 401, b"Authentication failed", request_body=b"", count="2", note="Error bodies are signed too"),
        case("control-post-tone-200", "44" * 16, "POST", "/v1/control", 200, b'{"ok":true}', request_body=b"tone", count="3"),
        case("control-post-sd-409", "55" * 16, "POST", "/v1/control", 409, b'{"ok":false,"error":"invalid_sd_operation"}', request_body=b'{"op":"sd_explode"}', count="4"),
        case("update-post-503", "66" * 16, "POST", "/v1/update", 503, b'{"error":"busy_or_timeout"}', request_body=bytes(288), count="5"),
        case("update-post-200", "77" * 16, "POST", "/v1/update", 200, b'{"ok":true,"rebooting":true}', request_body=bytes(range(256)) * 2, count="6"),
        case("journal-read-200-ndjson", "88" * 16, "POST", "/v1/journal/read", 200, journal, request_body=journal_id.encode(), count="4294967295", note="Largest counter"),
        case("journal-read-404", "99" * 16, "POST", "/v1/journal/read", 404, b"Unknown journal", request_body=("d" * 64).encode(), count="7"),
        case("journal-post-200", "aa" * 16, "POST", "/v1/journal", 200, json.dumps(dict(ok=True, sha256=journal_id, bytes=len(journal)), separators=(",", ":")).encode(), request_body=journal, count="8"),
        case("empty-body-200", "bb" * 16, "GET", "/v1/status", 200, b"", request_body=b"", count="9", note="Body hash is the empty SHA-256"),
        case("lowercase-node-mac", "cc" * 16, "GET", "/v1/status", 200, status_body, request_body=b"", count="10", node="aa:bb:cc:dd:ee:ff", note="Header mac() accepts either case; the bytes differ"),
        case("longest-path-404", "dd" * 16, "GET", "/" + "p" * 255, 404, b"Nothing matches the given URI", request_body=b"", count="11", note="256-character path"),
        case("status-100-edge", "ee" * 16, "GET", "/v1/status", 100, b"", request_body=b"", count="12"),
        case("status-599-edge", "ff" * 16, "GET", "/v1/status", 599, b"x", request_body=b"", count="13"),
        case("other-key", "0f" * 16, "POST", "/v1/control", 200, b'{"ok":true}', request_body=b"next_page", count="14", key=bytes.fromhex("ff" * 32)),
    ]
    base = dict(challenge="11" * 16, node=MAC, method="GET", path="/v1/status", request_hash=EMPTY, nonce=NONCE, count="1", request_signature="0" * 64)
    chal = dict(challenge="11" * 16, node=MAC, method="GET", path="/v1/challenge", request_hash=EMPTY, nonce="-", count="0", request_signature="-")
    invalid = [
        ("challenge-uppercase-hex", dict(base, challenge="AA" * 16)), ("challenge-31-chars", dict(base, challenge="a" * 31)), ("challenge-33-chars", dict(base, challenge="a" * 33)),
        ("node-missing-colon", dict(base, node="00:11:22:33:4455")), ("node-too-long", dict(base, node=MAC + ":66")), ("node-dash-separated", dict(base, node=MAC.replace(":", "-"))),
        ("method-put", dict(base, method="PUT")), ("method-lowercase", dict(base, method="get")),
        ("path-no-leading-slash", dict(base, path="v1/status")), ("path-with-space", dict(base, path="/v1/sta tus")), ("path-empty", dict(base, path="")),
        ("path-257-chars", dict(base, path="/" + "p" * 256)), ("path-non-ascii", dict(base, path="/v1/stätus")), ("path-with-tab", dict(base, path="/v1/\tstatus")),
        ("request-hash-uppercase", dict(base, request_hash=EMPTY.upper())), ("request-hash-short", dict(base, request_hash=EMPTY[:63])),
        ("nonce-uppercase", dict(base, nonce=NONCE.upper())), ("nonce-placeholder-on-status", dict(base, nonce="-")),
        ("count-zero", dict(base, count="0")), ("count-leading-zero", dict(base, count="01")), ("count-too-large", dict(base, count="4294967296")),
        ("count-eleven-digits", dict(base, count="10000000000")), ("count-placeholder-on-status", dict(base, count="0")), ("count-signed", dict(base, count="+1")),
        ("signature-uppercase", dict(base, request_signature="A" * 64)), ("signature-short", dict(base, request_signature="a" * 63)), ("signature-placeholder-on-status", dict(base, request_signature="-")),
        ("challenge-path-post", dict(chal, method="POST")), ("challenge-path-nonempty-hash", dict(chal, request_hash="a" * 64)),
        ("challenge-path-real-nonce", dict(chal, nonce=NONCE)), ("challenge-path-count-1", dict(chal, count="1")), ("challenge-path-real-signature", dict(chal, request_signature="a" * 64)),
    ]
    document = dict(
        format="flock-management-response-v1 golden vectors",
        source="firmware/shared/management/response_auth.h",
        schema=dict(
            cases="Valid bindings. canonical is the exact LF-joined signing input (no trailing LF); signature = lowercase hex HMAC-SHA256(key, canonical); body_sha256 = SHA-256 of body_hex bytes.",
            invalid_bindings="bind()/valid() must return false for every entry; nothing may be signed or verified with them.",
            verify="verify(version='1', signature, status, body_sha256) must succeed exactly once per pending exchange and fail for any altered status, body, signature, key or challenge."),
        cases=cases,
        invalid_bindings=[dict(name=name, binding=binding) for name, binding in invalid],
    )
    OUT.write_text(json.dumps(document, indent=1, sort_keys=False) + "\n")
    print(f"wrote {OUT} ({len(cases)} cases, {len(invalid)} invalid bindings)")


if __name__ == "__main__":
    main()
