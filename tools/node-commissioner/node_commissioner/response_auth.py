"""Management response authentication v1 (host side).

Mirrors ``firmware/shared/management/response_auth.h`` field for field. The unchanged
v1 request MAC proves the host to the node; this layer proves each HTTP response to
the host. Every exchange carries a fresh 16-byte client challenge, and the node signs
``flock-management-response-v1`` + challenge + node + method + path + request hash +
request nonce + request counter + request signature + HTTP status + body hash with the
pinned per-node key. Nothing in a response is used before the signature verifies.
"""
import hashlib
import hmac
import re
import secrets
import time
from dataclasses import dataclass

VERSION = "1"
VERSION_HEADER = "X-Flock-Response-Version"
CHALLENGE_HEADER = "X-Flock-Response-Challenge"
SIGNATURE_HEADER = "X-Flock-Response-Signature"
PREFIX = "flock-management-response-v1"
EMPTY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
BODY_LIMIT = 128 * 1024
PATH_LIMIT = 256
CANONICAL_LIMIT = 768  # Firmware canonical buffer; the encoded binding must be shorter.
MAX_AGE_MS = 10000  # Firmware monitor window. The host binds each exchange to its own deadline.
KEY_BYTES = 32

_HEX32 = re.compile(r"[0-9a-f]{32}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_MAC = re.compile(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}")
_COUNTER = re.compile(r"[1-9][0-9]{0,9}")
_PATH = re.compile(r"/[!-~]{0,%d}" % (PATH_LIMIT - 1))


class ResponseAuthError(ValueError):
    """The response did not authenticate; no part of it may be used."""


class LegacyResponseError(ResponseAuthError):
    """The responder sent no response authentication at all (legacy firmware or a non-node)."""


def new_challenge() -> str:
    """Fresh 16-byte challenge as 32 lowercase hex characters; one per HTTP exchange."""
    return secrets.token_bytes(16).hex()


def body_hash(body: bytes) -> str:
    if type(body) is not bytes:
        raise ResponseAuthError("Response body must be bytes")
    return hashlib.sha256(body).hexdigest()


@dataclass(frozen=True)
class Binding:
    """Everything one response is bound to; the challenge-only form is for GET /v1/challenge."""
    challenge: str
    node: str
    method: str
    path: str
    request_hash: str
    nonce: str = "-"
    count: str = "0"
    request_signature: str = "-"

    def __post_init__(self):
        if not valid_binding(self):
            raise ResponseAuthError("Invalid response binding")


def valid_binding(b) -> bool:
    """Exactly the firmware ``valid()`` rules, including the /v1/challenge special case."""
    fields = (b.challenge, b.node, b.method, b.path, b.request_hash, b.nonce, b.count, b.request_signature)
    if not all(type(f) is str for f in fields):
        return False
    if not (_HEX32.fullmatch(b.challenge) and _MAC.fullmatch(b.node) and b.method in ("GET", "POST")
            and _HEX64.fullmatch(b.request_hash) and _PATH.fullmatch(b.path)):
        return False
    if b.path == "/v1/challenge":
        return (b.method == "GET" and b.request_hash == EMPTY_HASH and b.nonce == "-"
                and b.count == "0" and b.request_signature == "-")
    return bool(_HEX32.fullmatch(b.nonce) and _COUNTER.fullmatch(b.count) and int(b.count) <= 0xFFFFFFFF
                and _HEX64.fullmatch(b.request_signature))


def canonical(binding: Binding, status: int, digest: str) -> bytes:
    """LF-separated fixed-order fields without a trailing LF, as the firmware signs them."""
    if not valid_binding(binding) or type(status) is not int or not 100 <= status <= 599 or type(digest) is not str or not _HEX64.fullmatch(digest):
        raise ResponseAuthError("Invalid response binding")
    text = "\n".join((PREFIX, binding.challenge, binding.node, binding.method, binding.path, binding.request_hash,
                      binding.nonce, binding.count, binding.request_signature, str(status), digest))
    data = text.encode("ascii")
    if len(data) >= CANONICAL_LIMIT:
        raise ResponseAuthError("Invalid response binding")
    return data


def sign(binding: Binding, status: int, digest: str, key: bytes) -> str:
    if type(key) is not bytes or len(key) != KEY_BYTES:
        raise ResponseAuthError("Node key must be exactly 32 bytes")
    return hmac.new(key, canonical(binding, status, digest), hashlib.sha256).hexdigest()


def extract(headers) -> tuple[str, str]:
    """Return (version, signature) from parsed response headers; exactly one of each is required.

    ``headers`` is any mapping with ``get_all(name)`` (``http.client.HTTPMessage``). Header
    names are case-insensitive; optional whitespace around values is removed; nothing else is.
    """
    versions = headers.get_all(VERSION_HEADER) or []
    signatures = headers.get_all(SIGNATURE_HEADER) or []
    if not versions and not signatures:
        raise LegacyResponseError(
            "Unsigned response: no X-Flock-Response-* headers. The responder is legacy node firmware "
            "(before management response authentication v1) or not a node. Unsigned responses are "
            "never accepted; update the node firmware, then retry.")
    if len(versions) != 1 or len(signatures) != 1:
        raise ResponseAuthError("Malformed response authentication: duplicate or missing header")
    return versions[0].strip(" \t"), signatures[0].strip(" \t")


def request_headers(binding: Binding) -> dict:
    """The two request headers that ask the node to sign its reply for this binding's challenge."""
    if not isinstance(binding, Binding) or not valid_binding(binding):
        raise ResponseAuthError("Invalid response binding")
    return {VERSION_HEADER: VERSION, CHALLENGE_HEADER: binding.challenge}


class Pending:
    """One verification opportunity for one HTTP exchange; a second attempt always fails."""

    def __init__(self, binding: Binding, max_age: float, started: float | None = None):
        if not isinstance(binding, Binding) or not valid_binding(binding):
            raise ResponseAuthError("Invalid response binding")
        if type(max_age) not in (int, float) or not 0 < max_age <= 3600:
            raise ResponseAuthError("Exchange deadline must be 0 < seconds <= 3600")
        self.binding, self.max_age = binding, float(max_age)
        self.started = time.monotonic() if started is None else float(started)
        self.waiting = True

    def request_headers(self) -> dict:
        return request_headers(self.binding)

    def verify(self, version: str, signature: str, status: int, body: bytes, key: bytes, now: float | None = None) -> None:
        """Raise ResponseAuthError unless the response is exactly the one the node signed for us."""
        waiting, self.waiting = self.waiting, False  # Exactly one attempt, including failures.
        now = time.monotonic() if now is None else float(now)
        if not waiting:
            raise ResponseAuthError("Response verification already attempted for this exchange")
        if now < self.started or now - self.started > self.max_age:
            raise ResponseAuthError("Response arrived outside the exchange deadline")
        if type(version) is not str or version != VERSION:
            raise ResponseAuthError("Unsupported response authentication version")
        if type(signature) is not str or not _HEX64.fullmatch(signature):
            raise ResponseAuthError("Malformed response signature")
        if type(body) is not bytes or len(body) > BODY_LIMIT:
            raise ResponseAuthError("Response body exceeds the signed body limit")
        expected = sign(self.binding, status, body_hash(body), key)
        if not hmac.compare_digest(expected.encode("ascii"), signature.encode("ascii")):
            raise ResponseAuthError("Response signature mismatch: not signed by this node for this exchange")
