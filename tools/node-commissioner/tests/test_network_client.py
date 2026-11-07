"""NetworkClient over a loopback fake node: every operation, every rejection path.

Real HMAC-SHA256 end to end; synthetic key and identity; no devices, no hardware, no
external network. The fake node lives in conftest.py and signs independently of the host
module so that the two implementations check each other.
"""
import hashlib
import json
import re
import urllib.error
import pytest
from conftest import CLOSE, EMPTY, KEY, MAC
from node_commissioner.network import NetworkClient, NodeHTTPError, TransportError
from node_commissioner.response_auth import BODY_LIMIT, LegacyResponseError, ResponseAuthError

HEX32 = re.compile(r"[0-9a-f]{32}")


def challenges(node):
    return [r["headers"]["X-Flock-Response-Challenge"] for r in node.requests]


def test_status_round_trip_is_signed_both_ways(node, client):
    status = client.request("GET", "/v1/status")
    assert status == node.status
    assert [(r["method"], r["path"]) for r in node.requests] == [("GET", "/v1/challenge"), ("GET", "/v1/status")]
    for request in node.requests:
        assert request["headers"].get_all("X-Flock-Response-Version") == ["1"]
        assert HEX32.fullmatch(request["headers"]["X-Flock-Response-Challenge"])
    signed = node.requests[1]["headers"]
    assert signed["X-Flock-Target"] == MAC and signed["X-Flock-Counter"] == "1" and signed["X-Flock-SHA256"] == EMPTY
    assert node.counter == 1  # The v1 request MAC still authorises and consumes the counter.
    assert len(set(challenges(node))) == 2


def test_every_exchange_carries_a_fresh_challenge(node, client):
    client.request("GET", "/v1/status")
    client.request("POST", "/v1/control", b"tone")
    client.request("GET", "/v1/status")
    seen = challenges(node)
    assert len(seen) == 6 and len(set(seen)) == 6


def test_control_commands_and_sd_rejection_codes(node, client):
    assert client.request("POST", "/v1/control", b"tone") == dict(ok=True)
    assert client.request("POST", "/v1/control", b'{"op":"sd_prepare"}') == dict(ok=True, job=8)
    assert client.request("POST", "/v1/control", b'{"op":"display_state","activity":"idle"}') == dict(ok=True)
    with pytest.raises(NodeHTTPError) as caught:
        client.request("POST", "/v1/control", b'{"op":"sd_explode"}')
    error = caught.value
    assert isinstance(error, urllib.error.HTTPError) and error.code == 409
    assert json.loads(error.read()) == dict(ok=False, error="invalid_sd_operation")
    assert "409" in str(error) and "invalid_sd_operation" in str(error)


def test_update_binds_image_digest_and_busy_answer_keeps_trustworthy_code(node, client):
    image = bytes(range(256)) * 4
    assert client.request("POST", "/v1/update", image, timeout=50) == dict(ok=True, rebooting=True)
    assert node.requests[-1]["headers"]["X-Flock-SHA256"] == hashlib.sha256(image).hexdigest()
    assert node.requests[-1]["body"] == image
    node.busy = True
    with pytest.raises(urllib.error.HTTPError) as caught:
        client.request("POST", "/v1/update", image, timeout=5)
    assert caught.value.code == 503 and json.loads(caught.value.read()) == dict(error="busy_or_timeout")
    with pytest.raises(NodeHTTPError) as caught:
        client.request("POST", "/v1/update", bytes(100), timeout=5)
    assert caught.value.code == 400 and caught.value.body == b"Image does not fit"


def test_signed_authentication_failure_is_reported_with_its_code(node, client):
    node.key = bytes.fromhex("0c" * 32)  # Node verifies requests with a different key, but still signs with ours.
    with pytest.raises(NodeHTTPError) as caught:
        client.request("GET", "/v1/status")
    assert caught.value.code == 401 and caught.value.body == b"Authentication failed"


def test_legacy_firmware_is_rejected_before_any_state_changing_request(node, client):
    node.answer_unsigned = True
    with pytest.raises(LegacyResponseError, match="update the node firmware"):
        client.request("POST", "/v1/control", b"tone")
    assert [r["path"] for r in node.requests] == ["/v1/challenge"]


def test_unsigned_success_is_never_accepted(node, client):
    node.tamper = lambda request, status, headers, body: (status, [h for h in headers if not h[0].startswith("X-Flock-Response")], body)
    with pytest.raises(LegacyResponseError):
        client.challenge()


@pytest.mark.parametrize("drop", ["X-Flock-Response-Version", "X-Flock-Response-Signature"])
def test_half_authenticated_responses_are_malformed_not_legacy(node, client, drop):
    node.tamper = lambda request, status, headers, body: (status, [h for h in headers if h[0] != drop], body)
    with pytest.raises(ResponseAuthError, match="duplicate or missing") as caught:
        client.challenge()
    assert not isinstance(caught.value, LegacyResponseError)


@pytest.mark.parametrize("name", ["X-Flock-Response-Version", "X-Flock-Response-Signature"])
def test_duplicate_authentication_headers_rejected_even_when_identical(node, client, name):
    node.tamper = lambda request, status, headers, body: (status, headers + [h for h in headers if h[0] == name], body)
    with pytest.raises(ResponseAuthError, match="duplicate or missing"):
        client.challenge()


@pytest.mark.parametrize("version", ["2", "01", "1.0", "", "1\t1"])
def test_wrong_version_values_rejected(node, client, version):
    def tamper(request, status, headers, body):
        return status, [("X-Flock-Response-Version", version) if h[0] == "X-Flock-Response-Version" else h for h in headers], body
    node.tamper = tamper
    with pytest.raises(ResponseAuthError):
        client.challenge()


def test_optional_whitespace_around_header_values_is_tolerated(node, client):
    node.tamper = lambda request, status, headers, body: (status, [(h[0], " " + h[1] + " \t") for h in headers], body)
    assert client.challenge()["configured"] is True


@pytest.mark.parametrize("mutate", [str.upper, lambda s: s[:63], lambda s: s + "0", lambda s: "g" + s[1:], lambda s: s.encode().hex()[:64]])
def test_malformed_or_wrong_signatures_rejected(node, client, mutate):
    def tamper(request, status, headers, body):
        return status, [(h[0], mutate(h[1])) if h[0] == "X-Flock-Response-Signature" else h for h in headers], body
    node.tamper = tamper
    with pytest.raises(ResponseAuthError):
        client.request("GET", "/v1/status")


def test_wrong_node_key_rejected(node, client):
    node.sign_key = bytes.fromhex("0c" * 32)
    with pytest.raises(ResponseAuthError, match="signature mismatch"):
        client.challenge()


def test_replayed_signed_status_rejected(node, client):
    captured = []
    node.tamper = lambda request, status, headers, body: captured.append((status, headers, body)) or (status, headers, body)
    first = client.request("GET", "/v1/status")
    replay = captured[-1]
    node.tamper = lambda request, status, headers, body: replay if request["path"] == "/v1/status" else (status, headers, body)
    with pytest.raises(ResponseAuthError, match="signature mismatch"):
        client.request("GET", "/v1/status")
    assert first == node.status


def test_replayed_challenge_answer_rejected_before_signing_anything(node, client):
    captured = []
    node.tamper = lambda request, status, headers, body: captured.append((status, headers, body)) or (status, headers, body)
    client.challenge()
    replay = captured[0]
    node.tamper = lambda request, status, headers, body: replay
    with pytest.raises(ResponseAuthError, match="signature mismatch"):
        client.request("POST", "/v1/control", b"tone")
    assert [r["path"] for r in node.requests] == ["/v1/challenge", "/v1/challenge"]


def test_server_supplied_challenge_header_cannot_redirect_verification(node, client):
    attacker = "ab" * 16

    def tamper(request, status, headers, body):
        binding = node.binding(request, challenge=attacker)
        headers = [h for h in headers if h[0] != "X-Flock-Response-Signature"]
        return status, headers + [("X-Flock-Response-Signature", node.signature(binding, status, body)), ("X-Flock-Response-Challenge", attacker)], body
    node.tamper = tamper
    with pytest.raises(ResponseAuthError, match="signature mismatch"):
        client.challenge()


def test_echo_of_our_own_challenge_is_ignored_not_fatal(node, client):
    node.tamper = lambda request, status, headers, body: (status, headers + [("X-Flock-Response-Challenge", request["headers"]["X-Flock-Response-Challenge"])], body)
    assert client.request("GET", "/v1/status") == node.status


@pytest.mark.parametrize("field, value", [
    ("path", "/v1/status"), ("method", "GET"), ("nonce", "11" * 16), ("count", "2"),
    ("request_signature", "33" * 32), ("request_hash", EMPTY), ("node", "02:00:00:00:00:02"),
])
def test_signature_over_a_different_request_binding_rejected(node, client, field, value):
    def tamper(request, status, headers, body):
        if request["path"] != "/v1/control":
            return status, headers, body
        binding = node.binding(request, **{field: value})
        return status, [(h[0], node.signature(binding, status, body)) if h[0] == "X-Flock-Response-Signature" else h for h in headers], body
    node.tamper = tamper
    with pytest.raises(ResponseAuthError, match="signature mismatch"):
        client.request("POST", "/v1/control", b"tone")


@pytest.mark.parametrize("change", ["status", "flip", "truncate", "append"])
def test_tampering_after_signing_rejected(node, client, change):
    def tamper(request, status, headers, body):
        if request["path"] != "/v1/status":
            return status, headers, body
        if change == "status":
            return 401, headers, body
        if change == "flip":
            return status, headers, body[:-2] + bytes([body[-2] ^ 1]) + body[-1:]
        if change == "truncate":
            return status, headers, body[:-1]
        return status, headers, body + b" "
    node.tamper = tamper
    with pytest.raises(ResponseAuthError, match="signature mismatch"):
        client.request("GET", "/v1/status")


@pytest.mark.parametrize("signed", [True, False])
def test_redirects_are_never_followed(node, client, signed):
    def tamper(request, status, headers, body):
        if request["path"] != "/v1/status":
            return status, headers, body
        location = [("Location", "http://198.51.100.7/v1/status")]  # Documentation range; never contacted.
        if signed:
            return 302, [(h[0], node.signature(node.binding(request), 302, b"")) if h[0] == "X-Flock-Response-Signature" else h for h in headers] + location, b""
        return 302, [("Content-Type", "text/html")] + location, b""
    node.tamper = tamper
    expected = NodeHTTPError if signed else LegacyResponseError
    with pytest.raises(expected) as caught:
        client.request("GET", "/v1/status")
    if signed:
        assert caught.value.code == 302
    assert [r["path"] for r in node.requests] == ["/v1/challenge", "/v1/status"]


def test_environment_proxy_settings_are_ignored(node, client, monkeypatch):
    for name in ("http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY", "no_proxy", "NO_PROXY"):
        monkeypatch.setenv(name, "http://198.51.100.9:3128" if "no" not in name.lower() else "")
    assert client.request("GET", "/v1/status") == node.status
    assert all(r["path"].startswith("/v1/") for r in node.requests)


def test_declared_oversized_body_rejected_without_being_trusted(node, client):
    node.tamper = lambda request, status, headers, body: (status, headers, bytes(BODY_LIMIT + 1))
    with pytest.raises(ResponseAuthError, match="128 KiB"):
        client.challenge()


def test_chunked_oversized_body_rejected_and_chunked_signed_body_accepted(node, client):
    def chunked(payload):
        return b"".join(b"%x\r\n%s\r\n" % (len(part), part) for part in (payload[i:i + 4096] for i in range(0, len(payload), 4096))) + b"0\r\n\r\n"

    def tamper(request, status, headers, body):
        kept = [h for h in headers if h[0] != "Content-Length"] + [("Transfer-Encoding", "chunked")]
        if request["path"] == "/v1/status":
            return status, kept, chunked(bytes(BODY_LIMIT + 1))
        return status, kept, chunked(body)
    node.tamper = tamper
    with pytest.raises(ResponseAuthError, match="128 KiB"):
        client.request("GET", "/v1/status")


def test_conflicting_content_length_headers_rejected(node, client):
    node.tamper = lambda request, status, headers, body: (status, headers + [("Content-Length", str(len(body)))] * 2, body)
    with pytest.raises(ResponseAuthError, match="conflicting"):
        client.challenge()


def test_journal_read_verifies_signature_then_digest(node, client):
    content = b'{"tick":1}\n{"tick":2}\n'
    digest = hashlib.sha256(content).hexdigest()
    node.journals[digest] = content
    assert client.read_journal(digest) == content
    assert node.requests[-1]["body"] == digest.encode()
    largest = bytes(BODY_LIMIT)
    node.journals[hashlib.sha256(largest).hexdigest()] = largest
    assert client.read_journal(hashlib.sha256(largest).hexdigest()) == largest
    with pytest.raises(NodeHTTPError) as caught:
        client.read_journal("d" * 64)
    assert caught.value.code == 404 and caught.value.body == b"Unknown journal"
    node.journals[digest] = content + b'{"tick":3}\n'  # Signed by the node, but not the journal that was asked for.
    with pytest.raises(ValueError, match="readback mismatch"):
        client.read_journal(digest)
    with pytest.raises(ValueError, match="Invalid journal digest"):
        client.read_journal("D" * 64)
    node.answer_unsigned = True
    with pytest.raises(LegacyResponseError):
        client.read_journal(digest)


def close_header(request, status, headers, body):
    return status, headers + [("Connection", "close")], body


@pytest.mark.parametrize("mode", ["close-header", "http10", "both"])
def test_connection_close_and_http10_replies_are_verified_and_cleaned_up(node, client, mode):
    """Regression: http.client detaches connection.sock after such replies; the client must keep working."""
    import os
    if mode in ("close-header", "both"):
        node.tamper = close_header
    if mode in ("http10", "both"):
        node.protocol = "HTTP/1.0"
    assert client.request("GET", "/v1/status") == node.status
    assert client.request("POST", "/v1/control", b"tone") == dict(ok=True)
    fds = len(os.listdir("/proc/self/fd")) if os.path.isdir("/proc/self/fd") else None
    for _ in range(10):
        assert client.request("GET", "/v1/status") == node.status
    if fds is not None:
        assert len(os.listdir("/proc/self/fd")) <= fds + 1  # Detached sockets are closed in finally, not at GC.


@pytest.mark.parametrize("mode", ["close-header", "http10"])
def test_slow_drip_with_detached_socket_cannot_outlive_the_deadline(node, client, mode):
    import time
    if mode == "close-header":
        node.tamper = close_header
    else:
        node.protocol = "HTTP/1.0"
    node.drip["/v1/status"] = 0.05
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        client.request("GET", "/v1/status", timeout=0.6)
    assert time.monotonic() - started < 3


def test_slow_header_trickle_cannot_outlive_the_deadline(node, client):
    import time
    node.drip_headers["/v1/status"] = 0.05  # ~150 header bytes would take ~7 s.
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        client.request("GET", "/v1/status", timeout=0.6)
    assert time.monotonic() - started < 3


@pytest.mark.parametrize("mode", ["close-header", "keep-alive"])
def test_premature_content_length_eof_is_a_transport_failure_not_an_answer(node, client, mode):
    """A genuine signed body with a larger declared length must not verify as a short body."""
    def tamper(request, status, headers, body):
        headers = headers + [("Content-Length", str(len(body) + 10))]
        return close_header(request, status, headers, body) if mode == "close-header" else (status, headers, body)
    node.tamper = tamper
    with pytest.raises(TransportError, match="before its declared length") as caught:
        client.challenge()
    assert isinstance(caught.value, OSError) and not isinstance(caught.value, (ValueError, urllib.error.HTTPError))


def test_truncated_chunked_body_is_a_transport_failure(node, client):
    def tamper(request, status, headers, body):
        kept = [h for h in headers if h[0] != "Content-Length"] + [("Transfer-Encoding", "chunked")]
        return status, kept, b"%x\r\n%s\r\n" % (len(body), body)  # No terminating zero chunk.
    node.tamper = tamper
    with pytest.raises(TransportError):
        client.challenge()


def test_early_signed_error_reply_is_read_when_the_upload_is_cut_off(node, client):
    """A busy node answers 503 from the headers and closes; the 8 MB upload then fails with a reset."""
    node.early_reply["/v1/update"] = lambda request: node.unavailable(request)
    with pytest.raises(NodeHTTPError) as caught:
        client.request("POST", "/v1/update", bytes(8_000_000), timeout=30)
    assert caught.value.code == 503 and json.loads(caught.value.read()) == dict(error="busy_or_timeout")
    node.early_reply["/v1/update"] = lambda request: (503, [("Content-Type", "application/json")], b'{"error":"busy_or_timeout"}')
    with pytest.raises(LegacyResponseError):
        client.request("POST", "/v1/update", bytes(8_000_000), timeout=30)
    node.early_reply["/v1/update"] = lambda request: CLOSE
    with pytest.raises(TransportError, match="may still have executed"):
        client.request("POST", "/v1/update", bytes(8_000_000), timeout=30)


def test_connection_closed_without_response_is_a_transport_failure(node, client):
    node.tamper = lambda request, status, headers, body: CLOSE
    with pytest.raises(OSError) as caught:
        client.challenge()
    assert not isinstance(caught.value, urllib.error.HTTPError)


def test_exchange_deadline_is_enforced(node, client):
    node.delay["/v1/status"] = 1.5
    with pytest.raises(TimeoutError):
        client.request("GET", "/v1/status", timeout=0.4)
    node.delay["/v1/challenge"] = 1.5
    client.CHALLENGE_TIMEOUT = 0.4
    with pytest.raises(TimeoutError):
        client.challenge()


def test_completed_reply_past_deadline_is_rejected_if_watchdog_is_delayed(node, client, monkeypatch):
    """A valid complete reply cannot win a race with a delayed Timer callback."""
    from types import SimpleNamespace
    from node_commissioner import network
    original_clock = network.clock
    original_read = network.http.client.HTTPResponse.read
    elapsed = [0.0]

    def finish_after_deadline(response, *args, **kwargs):
        body = original_read(response, *args, **kwargs)
        elapsed[0] = 1.0  # Deterministic time jump; proof is still younger than 10 s.
        return body

    monkeypatch.setattr(network, "clock", lambda: original_clock() + elapsed[0])
    monkeypatch.setattr(network.threading, "Timer", lambda *a, **kw:
                        SimpleNamespace(start=lambda: None, cancel=lambda: None))
    monkeypatch.setattr(network.http.client.HTTPResponse, "read", finish_after_deadline)
    client.CHALLENGE_TIMEOUT = 0.5
    with pytest.raises(TimeoutError, match="exceeded"):
        client.challenge()
    assert len(node.requests) == 1


def test_slowly_dripped_response_cannot_outlive_the_deadline(node, client):
    import time
    node.drip["/v1/status"] = 0.05  # Each byte arrives well inside any socket timeout; the whole body would take seconds.
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        client.request("GET", "/v1/status", timeout=0.6)
    assert time.monotonic() - started < 3


def test_late_update_reply_is_rejected_even_inside_the_transport_timeout(node, client):
    client.MAX_AGE = 0.5  # Scaled stand-in for the contract's 10 s; the transport timeout stays long.
    node.delay["/v1/update"] = 1.2
    with pytest.raises(ResponseAuthError, match="freshness"):
        client.request("POST", "/v1/update", bytes(300), timeout=50)
    node.delay.clear()
    assert client.request("POST", "/v1/update", bytes(300), timeout=50) == dict(ok=True, rebooting=True)
    client.MAX_AGE = 11
    with pytest.raises(ValueError, match="freshness"):
        client.challenge()


@pytest.mark.parametrize("change", [dict(v=True), dict(v="1"), dict(v=1.0), dict(next_counter=True), dict(next_counter="1"),
                                    dict(next_counter=0), dict(next_counter=2 ** 32), dict(configured=1), dict(configured="true"),
                                    dict(nonce="A" * 32), dict(nonce=None), dict(base_mac="00:11:22:33:44:55 ")])
def test_challenge_body_types_are_strict(node, client, change):
    def tamper(request, status, headers, body):
        altered = json.dumps(dict(json.loads(body), **change)).encode()
        return status, [(h[0], node.signature(node.binding(request), status, altered)) if h[0] == "X-Flock-Response-Signature" else h for h in headers], altered
    node.tamper = tamper
    with pytest.raises(ValueError, match="challenge|maintenance target"):
        client.challenge()


@pytest.mark.parametrize("timeout", [0, -1, 3601, "30", None])
def test_invalid_timeouts_rejected_before_any_request(node, client, timeout):
    with pytest.raises(ValueError):
        client.request("GET", "/v1/status", timeout=timeout)
    assert node.requests == []


def test_status_identity_checked_only_after_verification(node, client):
    node.status = dict(node.status, base_mac="02:00:00:00:00:02")
    with pytest.raises(ValueError, match="identity"):
        client.request("GET", "/v1/status")


@pytest.mark.parametrize("body", [b"not json", b"[1,2]", b"\xff\xfe", b""])
def test_verified_but_unusable_json_rejected(node, client, body):
    node.tamper = lambda request, status, headers, body_: (status, [(h[0], node.signature(node.binding(request), status, body)) if h[0] == "X-Flock-Response-Signature" else h for h in headers], body)
    with pytest.raises(ValueError, match="JSON"):
        client.challenge()


def test_challenge_contents_validated_only_after_verification(node, client):
    def tamper(request, status, headers, body):
        altered = json.dumps(dict(json.loads(body), base_mac="02:00:00:00:00:02")).encode()
        return status, [(h[0], node.signature(node.binding(request), status, altered)) if h[0] == "X-Flock-Response-Signature" else h for h in headers], altered
    node.tamper = tamper
    with pytest.raises(ValueError, match="maintenance target"):
        client.request("GET", "/v1/status")
    assert [r["path"] for r in node.requests] == ["/v1/challenge"]


def test_key_never_leaves_the_host(node, client):
    client.request("POST", "/v1/control", b"tone")
    for request in node.requests:
        assert KEY.hex() not in str(request["headers"]) and KEY not in request["body"]


def test_constructor_and_body_validation():
    with pytest.raises(ValueError):
        NetworkClient("node.local", MAC, KEY)
    with pytest.raises(ValueError):
        NetworkClient("127.0.0.1", "aa:bb:cc:dd:ee:ff", KEY)
    with pytest.raises(ValueError):
        NetworkClient("127.0.0.1", MAC, KEY[:-1])
    with pytest.raises(ValueError):
        NetworkClient("127.0.0.1", MAC, KEY, port=70000)
    client = NetworkClient("192.0.2.1", MAC, KEY)
    assert client.base == "http://192.0.2.1"
    with pytest.raises(ValueError):
        client.request("POST", "/v1/control", "tone")
    with pytest.raises(ValueError):
        client.request("POST", "/v1/reboot", b"")


def test_transport_error_is_an_oserror():
    assert issubclass(TransportError, OSError)


def test_node_http_error_sanitises_unsigned_reason_and_body_text():
    from node_commissioner.network import VerifiedResponse
    answer = VerifiedResponse(503, "Busy\r\nX-Injected: 1\x1b[31m", {}, b"\x00bad\n\xff" + b"x" * 500)
    error = NodeHTTPError("http://192.0.2.1/v1/update", answer)
    text = str(error)
    assert error.code == 503 and error.read() == answer.body and error.body == answer.body
    assert "\r" not in text and "\n" not in text and "\x1b" not in text and "\x00" not in text
    assert "Busy??X-Injected: 1?[31m" in text and "?bad??" in text and len(text) < 400
