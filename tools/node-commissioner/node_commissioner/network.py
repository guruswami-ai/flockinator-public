"""Authenticated local IPv4 maintenance transport: signed requests, verified responses.

The v1 request MAC is unchanged byte for byte. Every HTTP response, including HTTP errors
and the initial /v1/challenge answer, is authenticated with the pinned node key over a
fresh per-exchange challenge before it is parsed, used for status validation or update
progress, or treated as SD data. No environment proxy, no redirects, no unsigned fallback.
"""
import hashlib
import hmac
import http.client
import io
import ipaddress
import json
import re
import socket
import threading
import time
import urllib.error
from collections import namedtuple
from . import response_auth
from .protocol import valid_mac, validate_status
from .response_auth import BODY_LIMIT, EMPTY_HASH, MAX_AGE_MS, Binding, Pending, ResponseAuthError

VerifiedResponse = namedtuple("VerifiedResponse", "status reason headers body")
OPERATIONS = frozenset({("GET", "/v1/status"), ("POST", "/v1/control"), ("POST", "/v1/update"),
                        ("POST", "/v1/journal"), ("POST", "/v1/journal/read")})


def _check_timeout(timeout) -> None:
    if type(timeout) not in (int, float) or not 0 < timeout <= 3600:
        raise ValueError("Exchange timeout must be 0 < seconds <= 3600")


def auth_headers(key: bytes, challenge: dict, mac: str, method: str, path: str, body: bytes) -> dict:
    if len(key) != 32 or not valid_mac(mac) or challenge.get("v") != 1 or challenge.get("base_mac") != mac or challenge.get("configured") is not True:
        raise ValueError("Unconfigured or wrong maintenance target")
    nonce, counter = challenge.get("nonce", ""), challenge.get("next_counter")
    if not re.fullmatch(r"[0-9a-f]{32}", nonce) or type(counter) is not int or not 1 <= counter <= 0xFFFFFFFF:
        raise ValueError("Invalid challenge")
    if method not in ("GET", "POST") or path not in ("/v1/status", "/v1/control", "/v1/update", "/v1/journal", "/v1/journal/read"):
        raise ValueError("Unsupported maintenance operation")
    digest = hashlib.sha256(body).hexdigest()
    message = f"v1\n{nonce}\n{counter}\n{mac}\n{method}\n{path}\n{digest}".encode()
    signature = hmac.new(key, message, hashlib.sha256).hexdigest()
    return {"X-Flock-Nonce": nonce, "X-Flock-Counter": str(counter), "X-Flock-Target": mac, "X-Flock-SHA256": digest, "X-Flock-Signature": signature, "Content-Type": "application/octet-stream"}


class TransportError(OSError):
    """The HTTP exchange failed before any authenticated response existed."""


def _printable(value, limit: int) -> str:
    text = value.decode("ascii", "replace") if isinstance(value, bytes) else str(value)
    return "".join(c if " " <= c <= "~" else "?" for c in text[:limit])


class NodeHTTPError(urllib.error.HTTPError):
    """An authenticated non-200 answer from the node; ``code`` and ``read()`` are trustworthy.

    The status code and body are signed. The reason phrase and other headers are not, so
    they are only ever echoed as sanitised text, never acted upon.
    """

    def __init__(self, url: str, answer: VerifiedResponse):
        message = f"{_printable(answer.reason, 64)}; node said: {_printable(answer.body, 200)}"
        super().__init__(url, answer.status, message, answer.headers, io.BytesIO(answer.body))
        self.body = answer.body


def validate_challenge(value: dict, mac: str) -> dict:
    """Strict shape of an authenticated /v1/challenge body (bool is never an int here)."""
    if (not isinstance(value, dict) or type(value.get("v")) is not int or value["v"] != 1
            or value.get("base_mac") != mac or value.get("configured") is not True
            or type(value.get("nonce")) is not str or not re.fullmatch(r"[0-9a-f]{32}", value["nonce"])
            or type(value.get("next_counter")) is not int or not 1 <= value["next_counter"] <= 0xFFFFFFFF):
        raise ValueError("Unconfigured or wrong maintenance target, or invalid challenge")
    return value


class NetworkClient:
    CHALLENGE_TIMEOUT = 5
    JOURNAL_TIMEOUT = 10
    # Contract freshness bound (response_auth.h MaxAgeMs): the reply must verify within this
    # many seconds of the moment the request was fully handed to the kernel. The node cannot
    # have signed earlier than that, so the measured age is never shorter than the true one.
    # The transport timeout bounds the whole exchange separately and may be longer (updates).
    MAX_AGE = MAX_AGE_MS / 1000

    def __init__(self, address: str, mac: str, key: bytes, port: int = 80):
        self.address = str(ipaddress.IPv4Address(address))
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Invalid maintenance port")
        if not valid_mac(mac):
            raise ValueError("Expected an exact uppercase factory MAC")
        if type(key) is not bytes or len(key) != 32:
            raise ValueError("Management key must be exactly 32 bytes")
        self.mac, self.key, self.port = mac, key, port
        self.base = f"http://{self.address}" + ("" if port == 80 else f":{port}")

    def _exchange(self, method: str, path: str, body: bytes | None, headers: dict, timeout: float, binding: Binding) -> VerifiedResponse:
        """One connection, one request, one bounded response, verified before it is returned."""
        _check_timeout(timeout)
        max_age = self.MAX_AGE
        if type(max_age) not in (int, float) or not 0 < max_age <= MAX_AGE_MS / 1000:
            raise ValueError("Proof freshness bound must be 0 < seconds <= 10")
        deadline = time.monotonic() + timeout

        def remaining() -> float:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError(f"Maintenance exchange {method} {path} exceeded {timeout:g}s")
            return left

        sent = dict(headers)
        sent.update(response_auth.request_headers(binding))
        sent["Connection"] = "close"
        connection = http.client.HTTPConnection(self.address, self.port, timeout=remaining())
        expired = threading.Event()
        pinned = []  # The connected socket. getresponse() detaches connection.sock on a
        # Connection: close or HTTP/1.0 reply, while the response keeps reading from it.
        response = None

        def expire():
            # Hard wall-clock cap: a peer that drips bytes within each socket timeout cannot
            # stretch the exchange. Shutting the socket down fails every blocked stage at once.
            expired.set()
            for sock in pinned:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        watchdog = threading.Timer(timeout, expire)
        watchdog.daemon = True
        try:
            try:
                watchdog.start()
                connection.connect()
                sock = connection.sock
                pinned.append(sock)
                sock.settimeout(remaining())
                connection.request(method, path, body=body if method == "POST" else None, headers=sent)
                pending = Pending(binding, max_age=max_age)  # Freshness clock starts once the request is sent.
                sock.settimeout(remaining())
                response = connection.getresponse()
                lengths = response.headers.get_all("Content-Length") or []
                if len(lengths) > 1 or (response.length is not None and response.length > BODY_LIMIT):
                    raise ResponseAuthError("Response body exceeds the 128 KiB limit or has conflicting lengths")
                sock.settimeout(remaining())
                data = response.read(BODY_LIMIT + 1)
                if len(data) > BODY_LIMIT:
                    raise ResponseAuthError("Response body exceeds the 128 KiB limit")
                if response.length:
                    # read(amt) returns short at EOF without IncompleteRead; the framing promised more.
                    raise TransportError(f"Maintenance exchange {method} {path} ended {response.length} bytes before its declared length")
            except http.client.HTTPException as error:
                if expired.is_set():
                    raise TimeoutError(f"Maintenance exchange {method} {path} exceeded {timeout:g}s") from None
                raise TransportError(f"Maintenance exchange {method} {path} failed before an authenticated response: {type(error).__name__}") from error
            except (OSError, ValueError):
                if expired.is_set():
                    raise TimeoutError(f"Maintenance exchange {method} {path} exceeded {timeout:g}s") from None
                raise
        finally:
            watchdog.cancel()
            if response is not None:
                response.close()  # Releases the detached socket's file; the fd closes here, not at GC.
            for sock in pinned:
                sock.close()
            connection.close()
        if expired.is_set():
            raise TimeoutError(f"Maintenance exchange {method} {path} exceeded {timeout:g}s")
        if time.monotonic() - pending.started > max_age:
            raise ResponseAuthError(f"Response to {method} {path} arrived later than the {max_age:g}s freshness bound")
        version, signature = response_auth.extract(response.headers)
        pending.verify(version, signature, response.status, data, self.key)
        return VerifiedResponse(response.status, response.reason, response.headers, data)

    def _ok(self, answer: VerifiedResponse, path: str) -> VerifiedResponse:
        if answer.status != 200:
            raise NodeHTTPError(self.base + path, answer)
        return answer

    def _json(self, answer: VerifiedResponse, path: str) -> dict:
        try:
            value = json.loads(self._ok(answer, path).body)
        except (ValueError, UnicodeError):
            raise ValueError(f"Node returned invalid JSON for {path}") from None
        if not isinstance(value, dict):
            raise ValueError(f"Node returned a non-object JSON answer for {path}")
        return value

    def challenge(self) -> dict:
        """Authenticated GET /v1/challenge; the result is only used after its signature verifies."""
        binding = Binding(response_auth.new_challenge(), self.mac, "GET", "/v1/challenge", EMPTY_HASH)
        answer = self._exchange("GET", "/v1/challenge", None, {}, self.CHALLENGE_TIMEOUT, binding)
        return validate_challenge(self._json(answer, "/v1/challenge"), self.mac)

    def _signed(self, method: str, path: str, body: bytes, timeout: float) -> VerifiedResponse:
        if type(body) is not bytes:
            raise ValueError("Request body must be bytes")
        if (method, path) not in OPERATIONS:
            raise ValueError("Unsupported maintenance operation")
        _check_timeout(timeout)
        headers = auth_headers(self.key, self.challenge(), self.mac, method, path, body)
        # The response binds the exact request authentication that was sent, not a recomputation.
        binding = Binding(response_auth.new_challenge(), self.mac, method, path, headers["X-Flock-SHA256"],
                          headers["X-Flock-Nonce"], headers["X-Flock-Counter"], headers["X-Flock-Signature"])
        return self._exchange(method, path, body, headers, timeout, binding)

    def request(self, method: str, path: str, body: bytes = b"", timeout: float = 30) -> dict:
        value = self._json(self._signed(method, path, body, timeout), path)
        if path == "/v1/status":
            validate_status(value, self.mac)
        return value

    def read_journal(self, digest: str) -> bytes:
        if type(digest) is not str or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError("Invalid journal digest")
        path = "/v1/journal/read"
        answer = self._ok(self._signed("POST", path, digest.encode('ascii'), self.JOURNAL_TIMEOUT), path)
        data = answer.body
        if len(data) > BODY_LIMIT or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("SD journal readback mismatch")
        return data
