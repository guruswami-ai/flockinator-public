"""Loopback fake node for NetworkClient integration tests.

The fake node mirrors the firmware handlers in firmware/node-platform (request MAC v1,
counter consumption, status codes, text/html error bodies) and signs responses exactly as
firmware/shared/management/response_auth.h describes. It deliberately builds the canonical
string itself instead of importing node_commissioner.response_auth, so a shared mistake in
the host module cannot confirm itself. Synthetic key and identity only; no devices.
"""
import hashlib
import hmac
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest

MAC = "00:11:22:33:44:55"
KEY = bytes.fromhex("0b" * 32)
EMPTY = hashlib.sha256(b"").hexdigest()
CLOSE = object()  # Handler closes the socket without any response (firmware ESP_FAIL path).


def base_status(mac=MAC):
    return dict(type="status", v=1, base_mac=mac, label="A1", boot_count=5, running_partition="ota_0",
                app_sha256="a" * 64, ota_state=2, firmware="0.9.0", uptime_ms=1234, free_internal=100000,
                commissioning_link=dict(receiver_version=1),
                sd=dict(maintenance_supported=True, presence="RESPONDING", sector_bytes=512, card_id="c" * 80,
                        format_token="f" * 32, test=dict(job=8, phase="READY")))


class FakeNode:
    def __init__(self, key=KEY, mac=MAC):
        self.key, self.mac = key, mac
        self.sign_key = key
        self.nonce, self.counter = secrets.token_hex(16), 0
        self.status = base_status(mac)
        self.journals = {}
        self.requests = []
        self.answer_unsigned = False      # Legacy firmware: never emits response authentication.
        self.busy = False                 # /v1/update answers 503 busy_or_timeout.
        self.delay = {}                   # path -> seconds to sleep before answering.
        self.drip = {}                    # path -> seconds between body bytes (slow-loris style answer).
        self.drip_headers = {}            # path -> seconds between status-line/header bytes.
        self.protocol = "HTTP/1.1"        # or "HTTP/1.0": http.client then detaches the socket after the headers.
        self.tamper = None                # callable(request, status, headers, body) -> replacement triple or CLOSE
        self.port = None

    # --- response authentication, written independently of the host module ---
    def requested(self, request):
        h = request["headers"]
        return bool(h.get_all("X-Flock-Response-Version") or h.get_all("X-Flock-Response-Challenge"))

    def binding(self, request, challenge=None, node=None, method=None, path=None, request_hash=None,
                nonce=None, count=None, request_signature=None):
        h = request["headers"]
        is_challenge = request["path"] == "/v1/challenge"
        return dict(
            challenge=challenge or h["X-Flock-Response-Challenge"],
            node=node or self.mac,
            method=method or request["method"],
            path=path or request["path"],
            request_hash=request_hash or (EMPTY if is_challenge else h["X-Flock-SHA256"]),
            nonce=nonce or ("-" if is_challenge else h["X-Flock-Nonce"]),
            count=count or ("0" if is_challenge else h["X-Flock-Counter"]),
            request_signature=request_signature or ("-" if is_challenge else h["X-Flock-Signature"]))

    def signature(self, binding, status, body, key=None):
        text = "flock-management-response-v1\n" + "\n".join(binding[k] for k in (
            "challenge", "node", "method", "path", "request_hash", "nonce", "count", "request_signature"))
        text += f"\n{status}\n{hashlib.sha256(body).hexdigest()}"
        return hmac.new(key or self.sign_key, text.encode("ascii"), hashlib.sha256).hexdigest()

    def send(self, request, body, status=200, ctype="application/json", binding=None):
        headers = []
        if self.requested(request) and not self.answer_unsigned:
            headers += [("X-Flock-Response-Version", "1"),
                        ("X-Flock-Response-Signature", self.signature(binding or self.binding(request), status, body))]
        headers.append(("Content-Type", ctype))
        return status, headers, body

    def answer(self, request, text, status=200):
        return self.send(request, text.encode(), status)

    def error(self, request, status, text):
        return self.send(request, text.encode(), status, "text/html")

    def unavailable(self, request):
        return self.answer(request, '{"error":"busy_or_timeout"}', 503)

    # --- firmware request handling ---
    def authenticate(self, request):
        h = request["headers"]
        try:
            signature, nonce, target, count, digest = (h["X-Flock-Signature"], h["X-Flock-Nonce"], h["X-Flock-Target"],
                                                       h["X-Flock-Counter"], h["X-Flock-SHA256"])
        except KeyError:
            return None
        if target != self.mac or nonce != self.nonce or not count.isdigit() or str(int(count)) != count:
            return None
        n = int(count)
        if n != self.counter + 1 or n > 0xFFFFFFFF:
            return None
        message = f"v1\n{self.nonce}\n{count}\n{self.mac}\n{request['method']}\n{request['path']}\n{digest}".encode()
        expected = hmac.new(self.key, message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        self.counter = n  # Consumed before execution, including failed requests.
        return digest

    def handle(self, request):
        method, path, body = request["method"], request["path"], request["body"]
        if self.requested(request):
            h = request["headers"]
            version, challenge = h.get_all("X-Flock-Response-Version") or [""], h.get_all("X-Flock-Response-Challenge") or [""]
            ok = version == ["1"] and len(challenge) == 1 and len(challenge[0]) == 32 and all(c in "0123456789abcdef" for c in challenge[0])
            if path == "/v1/challenge":
                ok = ok and not body and method == "GET"
            else:
                ok = ok and all(h.get(k) for k in ("X-Flock-SHA256", "X-Flock-Nonce", "X-Flock-Counter", "X-Flock-Signature"))
            if not ok:
                return CLOSE
        if path == "/v1/challenge" and method == "GET":
            return self.answer(request, json.dumps(dict(v=1, base_mac=self.mac, nonce=self.nonce, next_counter=self.counter + 1,
                                                        key_id=hashlib.sha256(self.key).hexdigest()[:16], configured=True)))
        if (method, path) not in (("GET", "/v1/status"), ("POST", "/v1/control"), ("POST", "/v1/update"),
                                  ("POST", "/v1/journal"), ("POST", "/v1/journal/read")):
            return 404, [("Content-Type", "text/html")], b"Nothing matches the given URI"  # esp_http_server, unsigned
        digest = self.authenticate(request)
        if digest is None:
            return self.error(request, 401, "Authentication failed")
        if path == "/v1/status":
            if digest != EMPTY or body:
                return self.error(request, 401, "Authentication failed")
            return self.answer(request, json.dumps(self.status))
        if hashlib.sha256(body).hexdigest() != digest:
            return self.error(request, 400, "Invalid digest")
        if path == "/v1/control":
            if body[:1] == b"{":
                command = json.loads(body)
                op = command.get("op", "")
                if op.startswith("display_") or op.startswith("mission_"):
                    return self.answer(request, '{"ok":true}')
                if op in ("sd_prepare", "sd_format_quick", "sd_format_full"):
                    return self.answer(request, '{"ok":true,"job":8}')
                return self.answer(request, '{"ok":false,"error":"invalid_sd_operation"}', 409)
            if body in (b"tone", b"next_page"):
                return self.answer(request, '{"ok":true}')
            return self.error(request, 400, "Invalid command or digest")
        if path == "/v1/update":
            if len(body) < 288:
                return self.error(request, 400, "Image does not fit")
            if self.busy:
                return self.unavailable(request)
            return self.answer(request, '{"ok":true,"rebooting":true}')
        if path == "/v1/journal/read":
            key = body.decode("ascii", "replace")
            if len(body) != 64:
                return self.error(request, 400, "Invalid journal length")
            if key not in self.journals:
                return self.error(request, 404, "Unknown journal")
            return self.send(request, self.journals[key], 200, "application/x-ndjson")
        self.journals[digest] = body
        return self.answer(request, json.dumps(dict(ok=True, sha256=digest, bytes=len(body))))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # Like esp_http_server; every response still closes the connection.

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.serve("GET")

    def do_POST(self):
        self.serve("POST")

    def end_headers(self):
        node = self.server.node
        if node.drip_headers.get(self.path):
            raw = b"".join(self._headers_buffer) + b"\r\n"
            self._headers_buffer = []
            for i in range(len(raw)):
                self.wfile.write(raw[i:i + 1])
                self.wfile.flush()
                time.sleep(node.drip_headers[self.path])
            return
        super().end_headers()

    def serve(self, method):
        node = self.server.node
        self.protocol_version = node.protocol
        length = int(self.headers.get("Content-Length") or 0)
        request = dict(method=method, path=self.path, headers=self.headers, body=self.rfile.read(length) if length else b"")
        node.requests.append(request)
        if node.delay.get(self.path):
            time.sleep(node.delay[self.path])
        result = node.handle(request)
        if node.tamper is not None and result is not CLOSE:
            result = node.tamper(request, *result)
        self.close_connection = True
        if result is CLOSE:
            return
        status, headers, body = result
        self.send_response_only(status)
        for name, value in headers:
            self.send_header(name, value)
        if not any(name.lower() in ("transfer-encoding", "content-length") for name, _ in headers):
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if node.drip.get(self.path):
            for i in range(len(body)):
                self.wfile.write(body[i:i + 1])
                self.wfile.flush()
                time.sleep(node.drip[self.path])
            return
        self.wfile.write(body)
        self.wfile.flush()


class QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass  # Clients abort oversized or slow answers on purpose; a broken pipe is expected.


@pytest.fixture
def node():
    server = QuietServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server.node = FakeNode()
    server.node.port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.node
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def client(node):
    from node_commissioner.network import NetworkClient
    return NetworkClient("127.0.0.1", MAC, KEY, port=node.port)
