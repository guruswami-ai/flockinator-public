"""Cross-implementation check: the firmware header signs the golden vectors exactly as the host does.

Compiles tests/vectors/check_response_auth.cpp against the authoritative
firmware/shared/management/response_auth.h with OpenSSL as the HMAC backend and compares
canonical bytes, signatures and verify() outcomes with the vectors and with the Python
module. Skipped when the header, g++ or OpenSSL headers are absent; set
FLOCK_RESPONSE_AUTH_HEADER to point at a header outside this checkout.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
import pytest
from node_commissioner import response_auth as ra

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HEADER = Path(os.environ.get("FLOCK_RESPONSE_AUTH_HEADER") or REPO / "firmware/shared/management/response_auth.h")
OPENSSL = Path("/usr/include/openssl/hmac.h")
VECTORS = json.loads((HERE / "vectors/response_auth_v1.json").read_text())
MISSING = [name for name, present in ((str(HEADER), HEADER.is_file()), ("g++", bool(shutil.which("g++"))), (str(OPENSSL), OPENSSL.is_file())) if not present]
if MISSING and os.environ.get("FLOCK_REQUIRE_CXX"):
    raise RuntimeError(f"FLOCK_REQUIRE_CXX is set but the C++ cross-check cannot run; missing: {', '.join(MISSING)}")
pytestmark = pytest.mark.skipif(bool(MISSING), reason=f"needs {HEADER}, g++ and OpenSSL development headers (FLOCK_REQUIRE_CXX=1 fails instead of skipping)")


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    binary = tmp_path_factory.mktemp("response-auth-cxx") / "check_response_auth"
    subprocess.run(["g++", "-std=c++17", "-O1", "-Wall", "-Wextra", "-Wno-deprecated-declarations", "-I", str(HEADER.parent),
                    str(HERE / "vectors/check_response_auth.cpp"), "-o", str(binary), "-lcrypto"], check=True, timeout=300)
    return binary


def run(harness, rows):
    lines = "".join("\t".join(str(x) for x in row) + "\n" for row in rows)
    result = subprocess.run([str(harness)], input=lines, capture_output=True, text=True, check=True, timeout=60)
    return {line.split("\t")[0]: line.split("\t")[1:] for line in result.stdout.splitlines()}


def row(name, key_hex, binding, status, body_hex, signature):
    b, h = binding, (lambda s: s.encode("utf-8").hex())
    return (name, key_hex, h(b["challenge"]), h(b["node"]), h(b["method"]), h(b["path"]), h(b["request_hash"]), h(b["nonce"]), h(b["count"]), h(b["request_signature"]), status, body_hex, h(signature))


def test_cxx_header_agrees_with_vectors_and_python(harness):
    rows = [row(c["name"], c["key_hex"], c["binding"], c["status"], c["body_hex"], c["signature"]) for c in VECTORS["cases"]]
    out = run(harness, rows)
    assert len(out) == len(VECTORS["cases"])
    for case in VECTORS["cases"]:
        verdict, canonical_hex, signature, given, replay, tampered_status, tampered_body = out[case["name"]]
        assert verdict == "VALID", case["name"]
        assert bytes.fromhex(canonical_hex) == case["canonical"].encode("ascii") == ra.canonical(ra.Binding(**case["binding"]), case["status"], case["body_sha256"]), case["name"]
        assert signature == case["signature"] == ra.sign(ra.Binding(**case["binding"]), case["status"], case["body_sha256"], bytes.fromhex(case["key_hex"])), case["name"]
        assert (given, replay, tampered_status, tampered_body) == ("1", "0", "0", "0"), case["name"]


def test_cxx_header_rejects_the_same_invalid_bindings(harness):
    rows = [row(e["name"], "00" * 32, e["binding"], 200, "", "0" * 64) for e in VECTORS["invalid_bindings"]]
    out = run(harness, rows)
    assert len(out) == len(VECTORS["invalid_bindings"])
    for entry in VECTORS["invalid_bindings"]:
        assert out[entry["name"]] == ["INVALID"], entry["name"]
        assert not ra.valid_binding(type("B", (), entry["binding"])()), entry["name"]


def test_cxx_header_rejects_wrong_signature_version_and_status_range(harness):
    case = VECTORS["cases"][1]
    wrong = dict(case["binding"])
    out = run(harness, [row("wrong-signature", case["key_hex"], wrong, case["status"], case["body_hex"], "0" * 64),
                        row("status-99", case["key_hex"], wrong, 99, case["body_hex"], case["signature"]),
                        row("status-600", case["key_hex"], wrong, 600, case["body_hex"], case["signature"])])
    assert out["wrong-signature"][0] == "VALID" and out["wrong-signature"][3] == "0"
    assert out["status-99"] == ["INVALID"] and out["status-600"] == ["INVALID"]
