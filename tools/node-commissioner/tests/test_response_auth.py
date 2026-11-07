"""Host response-authentication primitives against the firmware contract and golden vectors."""
import email.parser
import hashlib
import hmac
import json
import re
from pathlib import Path
import pytest
from node_commissioner import response_auth as ra
from node_commissioner.response_auth import Binding, LegacyResponseError, Pending, ResponseAuthError

VECTORS = json.loads((Path(__file__).parent / "vectors/response_auth_v1.json").read_text())
KEY = bytes.fromhex("0b" * 32)
MAC = "00:11:22:33:44:55"
EMPTY = hashlib.sha256(b"").hexdigest()
STATUS = Binding("12" * 16, MAC, "GET", "/v1/status", EMPTY, "34" * 16, "7", "56" * 32)
CHALLENGE = Binding("12" * 16, MAC, "GET", "/v1/challenge", EMPTY)


def headers(text):
    return email.parser.Parser().parsestr(text, headersonly=True)


def test_constants_match_firmware_header():
    assert ra.EMPTY_HASH == EMPTY == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert (ra.BODY_LIMIT, ra.PATH_LIMIT, ra.MAX_AGE_MS, ra.CANONICAL_LIMIT) == (131072, 256, 10000, 768)
    assert (ra.VERSION_HEADER, ra.CHALLENGE_HEADER, ra.SIGNATURE_HEADER) == ("X-Flock-Response-Version", "X-Flock-Response-Challenge", "X-Flock-Response-Signature")
    assert ra.PREFIX == "flock-management-response-v1" and ra.VERSION == "1"


def test_clock_keeps_counting_through_host_sleep_where_available():
    import time
    reference = time.clock_gettime(time.CLOCK_BOOTTIME) if hasattr(time, "CLOCK_BOOTTIME") else time.monotonic()
    assert abs(ra.clock() - reference) < 1.0
    assert abs(Pending(STATUS, 5).started - ra.clock()) < 1.0


def test_new_challenge_is_fresh_lowercase_16_bytes():
    drawn = {ra.new_challenge() for _ in range(2000)}
    assert len(drawn) == 2000 and all(re.fullmatch(r"[0-9a-f]{32}", c) for c in drawn)


def test_canonical_bytes_are_exact_and_have_no_trailing_newline():
    digest = hashlib.sha256(b'{"ok":true}').hexdigest()
    expected = ("flock-management-response-v1\n" + "12" * 16 + f"\n{MAC}\nGET\n/v1/status\n{EMPTY}\n" + "34" * 16 + "\n7\n" + "56" * 32 + f"\n200\n{digest}").encode("ascii")
    assert ra.canonical(STATUS, 200, digest) == expected
    assert ra.canonical(CHALLENGE, 503, digest) == ("flock-management-response-v1\n" + "12" * 16 + f"\n{MAC}\nGET\n/v1/challenge\n{EMPTY}\n-\n0\n-\n503\n{digest}").encode()
    assert ra.sign(STATUS, 200, digest, KEY) == hmac.new(KEY, expected, hashlib.sha256).hexdigest()


@pytest.mark.parametrize("status, digest", [(99, EMPTY), (600, EMPTY), ("200", EMPTY), (200, EMPTY.upper()), (200, EMPTY[:63]), (200, None), (True, EMPTY)])
def test_canonical_rejects_bad_status_or_digest(status, digest):
    with pytest.raises(ResponseAuthError):
        ra.canonical(STATUS, status, digest)


@pytest.mark.parametrize("key", [b"", KEY[:31], KEY + b"x", KEY.hex(), bytearray(KEY)])
def test_sign_requires_exactly_32_key_bytes(key):
    with pytest.raises(ResponseAuthError):
        ra.sign(STATUS, 200, EMPTY, key)


def test_challenge_binding_special_case_is_exact():
    assert ra.valid_binding(CHALLENGE)
    for change in (dict(method="POST"), dict(request_hash="a" * 64), dict(nonce="34" * 16), dict(count="1"), dict(request_signature="56" * 32)):
        with pytest.raises(ResponseAuthError):
            Binding(**dict(challenge="12" * 16, node=MAC, method="GET", path="/v1/challenge", request_hash=EMPTY) | change)


def test_path_limit_boundary_and_charset():
    Binding("12" * 16, MAC, "GET", "/" + "p" * 255, EMPTY, "34" * 16, "7", "56" * 32)
    for path in ("/" + "p" * 256, "", "v1/status", "/v1 status", "/v1/st\x7fatus", "/v1/stätus", "/v1/\nstatus"):
        with pytest.raises(ResponseAuthError):
            Binding("12" * 16, MAC, "GET", path, EMPTY, "34" * 16, "7", "56" * 32)


def test_binding_fields_must_be_str():
    for change in (dict(count=7), dict(challenge=b"12" * 16), dict(node=None)):
        with pytest.raises(ResponseAuthError):
            Binding(**dict(challenge="12" * 16, node=MAC, method="GET", path="/v1/status", request_hash=EMPTY, nonce="34" * 16, count="7", request_signature="56" * 32) | change)


def test_pending_verifies_exactly_once_within_its_deadline():
    body = b'{"ok":true}'
    signature = ra.sign(STATUS, 200, hashlib.sha256(body).hexdigest(), KEY)
    pending = Pending(STATUS, max_age=5, started=100.0)
    assert pending.request_headers() == {"X-Flock-Response-Version": "1", "X-Flock-Response-Challenge": "12" * 16}
    pending.verify("1", signature, 200, body, KEY, now=105.0)
    with pytest.raises(ResponseAuthError, match="already attempted"):
        pending.verify("1", signature, 200, body, KEY, now=105.0)
    with pytest.raises(ResponseAuthError, match="deadline"):
        Pending(STATUS, 5, started=100.0).verify("1", signature, 200, body, KEY, now=105.001)
    with pytest.raises(ResponseAuthError, match="deadline"):
        Pending(STATUS, 5, started=100.0).verify("1", signature, 200, body, KEY, now=99.9)
    failed = Pending(STATUS, 5, started=100.0)
    with pytest.raises(ResponseAuthError):
        failed.verify("1", signature, 401, body, KEY, now=101.0)
    with pytest.raises(ResponseAuthError, match="already attempted"):
        failed.verify("1", signature, 200, body, KEY, now=101.0)  # A failure also consumes the attempt.
    for bad_age in (0, -1, 3601, "5", None):
        with pytest.raises(ResponseAuthError):
            Pending(STATUS, bad_age)
    with pytest.raises(ResponseAuthError):
        Pending(dict(STATUS.__dict__), 5)


@pytest.mark.parametrize("version, signature, status, body, key", [
    ("2", None, 200, b"", KEY), ("", None, 200, b"", KEY), (1, None, 200, b"", KEY), (None, None, 200, b"", KEY),
    ("1", "X" * 64, 200, b"", KEY), ("1", "a" * 63, 200, b"", KEY), ("1", "a" * 65, 200, b"", KEY), ("1", b"a" * 64, 200, b"", KEY),
    ("1", None, 200, bytes(ra.BODY_LIMIT + 1), KEY), ("1", None, 200, "text", KEY), ("1", None, 200, b"", bytes.fromhex("0c" * 32)),
    ("1", None, 201, b"", KEY), ("1", None, 200, b" ", KEY),
])
def test_pending_rejects_wrong_version_signature_body_status_or_key(version, signature, status, body, key):
    good = ra.sign(STATUS, 200, EMPTY, KEY)
    with pytest.raises(ResponseAuthError):
        Pending(STATUS, 5, started=0.0).verify(version, good if signature is None else signature, status, body, key, now=1.0)


def test_extract_requires_exactly_one_of_each_header():
    with pytest.raises(LegacyResponseError, match="update the node firmware"):
        ra.extract(headers("Content-Type: application/json\n\n"))
    assert ra.extract(headers("x-flock-response-version: 1 \nX-FLOCK-RESPONSE-SIGNATURE: \t" + "a" * 64 + "\n\n")) == ("1", "a" * 64)
    for text in ("X-Flock-Response-Version: 1\n\n", "X-Flock-Response-Signature: " + "a" * 64 + "\n\n",
                 "X-Flock-Response-Version: 1\nX-Flock-Response-Version: 1\nX-Flock-Response-Signature: " + "a" * 64 + "\n\n",
                 "X-Flock-Response-Version: 1\nX-Flock-Response-Signature: " + "a" * 64 + "\nX-Flock-Response-Signature: " + "a" * 64 + "\n\n"):
        with pytest.raises(ResponseAuthError, match="duplicate or missing") as caught:
            ra.extract(headers(text))
        assert not isinstance(caught.value, LegacyResponseError)
    assert ra.extract(headers("X-Flock-Response-Version: 1\nX-Flock-Response-Challenge: " + "b" * 32 + "\nX-Flock-Response-Signature: " + "a" * 64 + "\n\n")) == ("1", "a" * 64)


def test_golden_vectors_valid_cases():
    assert len(VECTORS["cases"]) >= 16 and VECTORS["source"].endswith("response_auth.h")
    for case in VECTORS["cases"]:
        key, body = bytes.fromhex(case["key_hex"]), bytes.fromhex(case["body_hex"])
        binding = Binding(**case["binding"])
        assert hashlib.sha256(body).hexdigest() == case["body_sha256"], case["name"]
        assert ra.canonical(binding, case["status"], case["body_sha256"]) == case["canonical"].encode("ascii"), case["name"]
        assert ra.sign(binding, case["status"], case["body_sha256"], key) == case["signature"], case["name"]
        Pending(binding, 5, started=0.0).verify("1", case["signature"], case["status"], body, key, now=1.0)
        tampered = [(case["status"] + (1 if case["status"] < 599 else -1), body), (case["status"], body + b"\0")] + ([(case["status"], body[:-1])] if body else [])
        for status, altered in tampered:
            with pytest.raises(ResponseAuthError):
                Pending(binding, 5, started=0.0).verify("1", case["signature"], status, altered, key, now=1.0)
        with pytest.raises(ResponseAuthError):
            Pending(binding, 5, started=0.0).verify("1", case["signature"], case["status"], body, bytes(32), now=1.0)
        other = Binding(**dict(case["binding"], challenge="0" * 32 if case["binding"]["challenge"] != "0" * 32 else "1" * 32))
        with pytest.raises(ResponseAuthError):
            Pending(other, 5, started=0.0).verify("1", case["signature"], case["status"], body, key, now=1.0)
    assert len({c["signature"] for c in VECTORS["cases"]}) == len(VECTORS["cases"])


def test_golden_vectors_invalid_bindings():
    assert len(VECTORS["invalid_bindings"]) >= 30
    for entry in VECTORS["invalid_bindings"]:
        with pytest.raises(ResponseAuthError):
            Binding(**entry["binding"])


def test_firmware_test_protocol_fixture_reproduced():
    """The fixture in firmware/shared/management/tests/test_protocol.cpp, derived there independently."""
    key = bytes(range(32))
    node, nonce, challenge = "02:11:22:33:44:55", "fedcba98765432100123456789abcdef", "00112233445566778899aabbccddeeff"
    request_hash = hashlib.sha256(b'{"op":"tone"}').hexdigest()
    assert request_hash == "cb9872ce4fcf983a6238ca63a5f437cdb7f974a4d9bab08eaa1b0977625a702e"
    request_signature = hmac.new(key, "\n".join(["v1", nonce, "42", node, "POST", "/v1/control", request_hash]).encode(), hashlib.sha256).hexdigest()
    assert request_signature == "f7a8fb1f246f373a37315540b98f9f1bd0fa275910e7460de030bd0401cc6b94"
    body = b'{"ok":true}\n'
    assert hashlib.sha256(body).hexdigest() == "e5f1eb4d806641698a35efe20e098efd20d7d57a9b90ee69079d5bb650920726"
    binding = Binding(challenge, node, "POST", "/v1/control", request_hash, nonce, "42", request_signature)
    assert len(ra.canonical(binding, 200, hashlib.sha256(body).hexdigest())) == 331
    assert ra.sign(binding, 200, hashlib.sha256(body).hexdigest(), key) == "8f3b8f032da4bb37dbc655d208f434cb2ba12c5ecc3eae5d0ee3c50119ed3297"
    Pending(binding, 10, started=1.0).verify("1", "8f3b8f032da4bb37dbc655d208f434cb2ba12c5ecc3eae5d0ee3c50119ed3297", 200, body, key, now=1.1)
    with pytest.raises(ResponseAuthError):  # The request MAC can never be reflected as the response MAC.
        Pending(binding, 10, started=1.0).verify("1", request_signature, 200, body, key, now=1.1)
