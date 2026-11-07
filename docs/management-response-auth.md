# Authenticated management responses

The node management server, Korvo fleet client and host commissioner use
**response authentication version 1**. A successful signed request alone does
not authenticate its HTTP reply. Updated clients verify the challenge exchange and the operation reply
before parsing status or treating a command/readback as successful. An unsigned,
expired, altered, mismatched, incomplete, or non-200 reply fails closed.

This is a source-level protocol change with native synthetic tests and
[compile-only target builds](results/meta-build-operations-20261107/README.md). It is not a
record of deployment, current hardware acceptance, or new scientific results.
Existing scientific artifacts and experiment semantics are unchanged.

## Wire contract

The existing request signature remains exactly:

```text
v1\n<server nonce>\n<counter>\n<target MAC>\n<method>\n<URI>\n<SHA256(request body)>
```

The node still accepts legacy clients using that signature. Clients opting into
authenticated responses add these headers to **each** request, including
`GET /v1/challenge`:

```text
X-Flock-Response-Version: 1
X-Flock-Response-Challenge: <32 lowercase hex characters from 16 fresh random bytes>
```

The client generates a new unpredictable challenge for the bootstrap exchange,
the protected operation, and every retry. The server returns:

```text
X-Flock-Response-Version: 1
X-Flock-Response-Signature: <64 lowercase hex HMAC-SHA256 characters>
```

The response HMAC uses the node's existing 32-byte management key. Its input is
the following eleven ASCII fields joined by one LF byte, with **no final LF**:

| Order | Field |
| --- | --- |
| 1 | Literal `flock-management-response-v1` |
| 2 | The client's fresh response challenge |
| 3 | The node MAC, exactly as pinned by the client and configured on the node |
| 4 | Exact request method: `GET` or `POST` |
| 5 | Exact request URI, including any query string; no decoding or normalization |
| 6 | Lowercase SHA-256 hex of the exact request body bytes |
| 7 | Request `X-Flock-Nonce` |
| 8 | Request `X-Flock-Counter`, canonical unsigned decimal |
| 9 | Request `X-Flock-Signature`, lowercase hex |
| 10 | Actual numeric HTTP status, canonical decimal, such as `200` or `401` |
| 11 | Lowercase SHA-256 hex of the exact response entity body bytes |

For `GET /v1/challenge`, field 6 is the empty-body SHA-256,
field 7 is the literal `-`, field 8 is `0`, and field 9 is `-`.
This bootstraps authentication without trusting a server-provided nonce or clock.
The body still reports request protocol `"v":1`; that JSON field is independent
of the response protocol header.

The canonicalization implementation is
[`response_auth.h`](../firmware/shared/management/response_auth.h).
An independent Python-stdlib-derived canonical byte string and HMAC fixture are
in [`test_protocol.cpp`](../firmware/shared/management/tests/test_protocol.cpp).
The fixture key is the synthetic byte sequence 0 through 31.

## Verification and bounds

The Korvo captures the expected binding before issuing the request. It requires
exactly one supported version header and one well-formed signature header,
rejecting duplicates even when their names use different case. It hashes the
received body bytes before JSON parsing. HTTP chunk framing is not part of the
entity body; whitespace, newlines and embedded NUL bytes in the body are part of
the hash. No JSON serialization or reformatting occurs during verification.

Verification consumes a pending exchange once, including failed attempts, and
requires completion within **10,000 ms** of the client's monotonic start time.
No server timestamp is trusted. Replaying an old server challenge and its old
operation reply cannot match the new client challenge. Separate request-local
contexts prevent crossed concurrent replies from authenticating one another.
The existing node-wide request counter can still cause concurrent clients to
race and receive an authenticated error; this change does not relax that
counter or introduce automatic command retries.

The verifier limits response bodies to **131,072 bytes**. The shared binding
limits the URI to 256 printable non-space ASCII bytes, method to GET/POST,
challenge and nonce to 32 lowercase hex characters, digests/signatures to 64,
and protected request counters to 1 through 4,294,967,295 without leading zeros.
The MAC identity must be a 17-character colon-separated MAC string and is
case-sensitive in the authenticated binding. Invalid or unterminated fields
fail before the bounded 768-byte canonical buffer is used.

Transport errors, missing completion, overflow, malformed/duplicate proof
headers, crypto errors, and proof mismatches all clear the returned body. A
latched receive error is checked even if the HTTP library ignores a callback's
error return. An authenticated non-200 reply still fails the operation, and
`status()` records the panel as not live. Authenticated malformed status JSON
also cannot mark a panel live. HTTP freshness proves a fresh response exchange,
not the sampling time of every field in the node's published status snapshot.

The node signs normal replies and application errors through one response
adapter that sets the HTTP status used by the MAC. A malformed response-auth
request, unavailable key, allocation failure during signing, crypto failure,
or transport failure may close the exchange without a proof; clients must treat
that as unverified. HTTP-server-level errors outside a registered handler are
also unverified. No unsigned error can be promoted to success.

Journal readback now reads at most 128 KiB into one PSRAM snapshot under the
existing storage lease, checks the complete file length, then hashes and sends
those same bytes. This changes the read response from chunked transmission to a
bounded entity body without changing its contents or journal identity. It needs
up to 128 KiB additional PSRAM during readback; allocation/read failures return
an authenticated 503 where possible. The existing end-to-end journal digest
and byte comparisons remain necessary.

## Compatibility and rollout

| Node | Client | Result |
| --- | --- | --- |
| Updated | Updated verifier | Response-v1 required; successful replies authenticated |
| Updated | Legacy request-only client | Existing signed requests work; replies remain **unverified** by that client |
| Legacy | Updated verifier | **Incompatible/unverified**; unsigned replies rejected, panel not marked live |
| Legacy | Legacy request-only client | Request authentication only; HTTP replies remain **unverified** |

The Korvo's existing not-live display also covers missing response authentication;
it does not distinguish old firmware from an offline, misconfigured or attacked
node. A source version, HTTP 200, familiar JSON label, or reachable IP is not
proof that a device runs response-v1. Do not add a silent unsigned fallback.
The host commissioner implements the same response-v1 binding in
[`response_auth.py`](../tools/node-commissioner/node_commissioner/response_auth.py)
and enforces it in its network transport. Keep node, Korvo and host release
provenance together.

### Host transport and timing

The host checks proofs before JSON parsing, command success, error-body use or
journal digest validation. It connects directly to a pinned IPv4 address without
environment proxies or redirects. Missing proofs fail explicitly, including
against legacy firmware; there is no unsigned fallback. HTTP error codes are
trusted only after their status/body proof verifies; reason phrases and other
unsigned HTTP metadata are not device assertions.

The host's proof age limit is also 10 seconds, measured from when the complete
request has been handed to the local socket. This accommodates a large OTA
upload without treating its upload duration as response age. It differs from
the Korvo's clock, which starts before the exchange. A separate caller-selected
total transport deadline includes connect, upload, headers and body; a socket
watchdog interrupts slow replies. Neither timeout cancels a command that may
already have executed. Reconcile authenticated state before retrying writes.

An early signed rejection can arrive before the node reads the full upload. The
host can verify that rejection even if sending the upload was interrupted; its
post-send age can understate the age of that early error, although the total
transport budget still applies. This does not turn a rejection into success.
On platforms providing `CLOCK_BOOTTIME` (including Linux), the host age and
deadline clock includes time spent suspended. Other platforms use Python's
monotonic clock, whose suspend behavior is platform dependent; keep the host
awake during commissioning and reconcile state after a sleep/resume interruption.

Host tests use real HMACs and a loopback HTTP server. Golden vectors compare the
Python implementation with the actual C++ header using OpenSSL, including the
firmware's Mbed TLS fixture. CI installs the compiler/OpenSSL prerequisites and
runs the commissioner suite with `FLOCK_REQUIRE_CXX=1` so missing prerequisites
fail the check; standalone environments without them explicitly
skip the cross-language tests. None of these checks establish deployed firmware
or physical acceptance.

For a separately authorized rollout:

1. Build and review the updated node (`waveshare-s3`, plus `journal-trial` where
   journal endpoints are needed), Korvo and host verifier releases. Retain exact
   commit/build identities and native-test logs. Existing provisioning keys and
   request signatures do not need rotation for this protocol change.
2. Upgrade nodes first using an independently trusted maintenance procedure.
   A legacy transport's unsigned success reply alone cannot verify that upgrade.
3. Upgrade the Korvo and any host pollers/commissioners to require response-v1.
   Keep legacy-client observations explicitly unverified during the transition.
4. Under a separate hardware acceptance plan, check valid status/control/journal
   exchanges, mismatched identities and keys, mixed-version rejection, memory
   use and timing on the actual targets. Native checks do not replace those
   measurements. No deployment or hardware acceptance was performed here.

HMAC provides authentication to parties holding the management key, not
confidentiality or a public device attestation. Another holder of that symmetric
key can produce a valid proof. This change does not add TLS, protect against
traffic suppression or denial of service, prove sensor truth, or alter the
existing command authorization and execution semantics. A timed-out write can
still have executed; reconcile authenticated state before retrying an operation.

## Native verification

Use an already-installed upstream Mbed TLS source tree (for example the one
inside ESP-IDF), a native C/C++ compiler, CMake and `uv`. No network, hardware,
real keys, package download or firmware flashing is involved:

```sh
uv run --no-project python firmware/shared/management/tests/run_native.py \
  --mbedtls-source /path/to/esp-idf/components/mbedtls/mbedtls \
  --build-dir /tmp/flock-response-native

uv run --no-project python firmware/shared/management/tests/run_native.py \
  --mbedtls-source /path/to/esp-idf/components/mbedtls/mbedtls \
  --build-dir /tmp/flock-response-sanitize --sanitize
```

The runner extracts the current production function bodies from `fleet.cpp`
and `maintenance.cpp` without modifying them and compiles those with the actual
node response adapter. The host transport, monotonic clock and RNG are
deterministic test substitutes. The monitor's PSA API boundary delegates to real
portable Mbed TLS SHA-256/HMAC; the node also uses real Mbed TLS. This tests the
production protocol paths, not an independent Python protocol reimplementation.

The suites cover legitimate acceptance, unsigned replies, every bound field,
status/body/challenge alteration, replay with a replayed server challenge,
crossed pending requests, legacy signed requests, error/live-state handling,
duplicate/oversized headers, incomplete transport, bounded binary bodies,
deadline expiry and crypto failures. Strict compiler warnings and ASan/UBSan
are enabled by the commands above. Complete firmware compilation and physical
timing/memory/OTA acceptance remain separate checks.
