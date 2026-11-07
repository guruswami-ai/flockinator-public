import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("record_call", Path(__file__).with_name("record_call.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SYNTHETIC_KEY = "synthetic-test-credential-never-a-live-key"


class Reply:
    def __init__(self, status, body):
        self.status, self.body = status, body

    def getheader(self, name):
        return "synthetic-request-id" if name == "x-request-id" else None

    def read(self, size):
        return self.body[:size]


class Connection:
    def __init__(self, status=200, body=None):
        self.calls = []
        self.reply = Reply(status, body or b'{"status":"completed","model":"muse-spark-1.3-contributor","id":"synthetic-response-id","usage":{"input_tokens":3,"output_tokens":4}}')

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))

    def getresponse(self):
        return self.reply

    def close(self):
        pass


class CallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.request = self.root / "input.json"
        self.request.write_text(json.dumps({"model":"muse-spark-1.3-contributor", "input":"Public build task", "store":False, "max_output_tokens":100}))
        self.env = patch.dict(os.environ, {"MODEL_API_KEY":SYNTHETIC_KEY})
        self.env.start()
        self.addCleanup(self.env.stop)

    def call(self, conn):
        return module.record(self.request, self.root / "result", connection_factory=lambda *a, **kw:conn)

    def test_exact_request_and_receipt_without_credential(self):
        conn = Connection()
        self.assertTrue(self.call(conn))
        self.assertEqual(len(conn.calls), 1)
        self.assertEqual(conn.calls[0][1]["body"], self.request.read_bytes())
        receipt = json.loads((self.root / "result/receipt.json").read_text())
        self.assertEqual(receipt["request_sha256"], module.digest(self.request.read_bytes()))
        self.assertEqual(receipt["provider_request_id"], "synthetic-request-id")
        self.assertTrue(all(SYNTHETIC_KEY.encode() not in p.read_bytes() for p in (self.root / "result").iterdir()))

    def test_no_redirect_or_retry_and_preserves_failure(self):
        conn = Connection(307, b'{"error":"redirect"}')
        self.assertFalse(self.call(conn))
        self.assertEqual(len(conn.calls), 1)
        self.assertEqual(json.loads((self.root / "result/receipt.json").read_text())["http_status"], 307)

    def test_reflected_credential_redacted_and_not_success(self):
        conn = Connection(body=json.dumps({"status":"completed", "echo":SYNTHETIC_KEY}).encode())
        self.assertFalse(self.call(conn))
        self.assertTrue(all(SYNTHETIC_KEY.encode() not in p.read_bytes() for p in (self.root / "result").iterdir()))

    def test_escaped_credential_request_rejected_before_write_or_network(self):
        escaped = "".join("\\u%04x" % ord(char) for char in SYNTHETIC_KEY)
        for value in (SYNTHETIC_KEY, {SYNTHETIC_KEY: ["nested"]}):
            with self.subTest(value=value):
                request = {"model": "muse-spark-1.3-contributor", "store": False,
                           "max_output_tokens": 100, "input": value}
                self.request.write_text(json.dumps(request).replace(SYNTHETIC_KEY, escaped))
                conn = Connection()
                with self.assertRaises(ValueError):
                    self.call(conn)
                self.assertEqual(conn.calls, [])
                self.assertFalse((self.root / "result").exists())

    def test_escaped_response_strings_and_keys_cannot_leak_into_receipt(self):
        escaped = "".join("\\u%04x" % ord(char) for char in SYNTHETIC_KEY)
        payload = {"status": "completed", "model": SYNTHETIC_KEY,
                   "id": "prefix-" + SYNTHETIC_KEY,
                   "usage": {SYNTHETIC_KEY: [{"nested": SYNTHETIC_KEY}]}}
        conn = Connection(body=json.dumps(payload).replace(SYNTHETIC_KEY, escaped).encode())
        self.assertFalse(self.call(conn))
        for path in (self.root / "result").iterdir():
            decoded = json.loads(path.read_bytes())
            self.assertNotIn(SYNTHETIC_KEY, json.dumps(decoded, ensure_ascii=False))
        receipt = json.loads((self.root / "result/receipt.json").read_bytes())
        self.assertTrue(receipt["credential_redacted"])
        self.assertEqual(receipt["outcome"], "provider_failure")
        self.assertEqual(receipt["response_sha256"], module.digest((self.root / "result/response.json").read_bytes()))

    def test_safe_response_wire_bytes_preserved(self):
        body = b'{ "status" : "completed", "model": "muse-spark-1.3-contributor", "text":"\\u0041" }\n'
        self.assertTrue(self.call(Connection(body=body)))
        self.assertEqual((self.root / "result/response.json").read_bytes(), body)

    def test_malformed_or_duplicate_response_not_persisted(self):
        escaped = "".join("\\u%04x" % ord(char) for char in SYNTHETIC_KEY)
        for index, body in enumerate((b'{"text":"' + escaped.encode(),
                                      b'{"x":"' + escaped.encode() + b'","x":0}')):
            with self.subTest(index=index):
                target = self.root / str(index)
                self.assertFalse(module.record(self.request, target,
                    connection_factory=lambda *a, **kw: Connection(body=body)))
                self.assertFalse((target / "response.json").exists())
                self.assertEqual(json.loads((target / "receipt.json").read_bytes())["outcome"], "invalid_response")

    def test_duplicate_request_and_reuse_reject_before_network(self):
        conn = Connection()
        self.assertTrue(self.call(conn))
        with self.assertRaises(FileExistsError):
            self.call(conn)
        self.assertEqual(len(conn.calls), 1)
        self.request.write_text('{"model":"a","model":"b"}')
        with self.assertRaises(ValueError):
            module.record(self.request, self.root / "other", connection_factory=lambda *a, **kw:conn)
        self.assertEqual(len(conn.calls), 1)

    def test_transport_error_retains_receipt(self):
        conn = Connection()
        conn.getresponse = lambda: (_ for _ in ()).throw(TimeoutError("provider detail"))
        self.assertFalse(self.call(conn))
        receipt = json.loads((self.root / "result/receipt.json").read_text())
        self.assertEqual(receipt["exception_type"], "TimeoutError")
        self.assertNotIn("provider detail", json.dumps(receipt))

    def test_connection_setup_failure_retains_receipt(self):
        def fail(*args, **kwargs):
            raise OSError("provider detail")
        self.assertFalse(module.record(self.request, self.root / "result", connection_factory=fail))
        receipt = json.loads((self.root / "result/receipt.json").read_text())
        self.assertEqual(receipt["exception_type"], "OSError")

    def test_close_failure_does_not_lose_result(self):
        conn = Connection()
        conn.close = lambda: (_ for _ in ()).throw(OSError("provider detail"))
        self.assertTrue(self.call(conn))
        receipt = json.loads((self.root / "result/receipt.json").read_text())
        self.assertTrue(receipt["close_failed"])


if __name__ == "__main__":
    unittest.main()
