"""Mission slate: checksum derivation, QR payload, rendering."""
import hashlib

from kulira_core.slate import mission_checksum, qr_payload, render_slate_png, validate_qr_payload


def test_checksum_is_derived_and_stable():
    a = mission_checksum("m1", "2026-11-06T00:00:00Z", "ab" * 32, ["ff" * 32])
    b = mission_checksum("m1", "2026-11-06T00:00:00Z", "ab" * 32, ["ff" * 32])
    assert a == b and a.startswith("FLOCK-") and len(a) == 22
    assert mission_checksum("m2", "2026-11-06T00:00:00Z", "ab" * 32) != a


def test_checksum_frame_order_insensitive():
    a = mission_checksum("m", "t", "", ["aa", "bb"])
    b = mission_checksum("m", "t", "", ["bb", "aa"])
    assert a == b  # sorted before hashing


def test_qr_payload_compact_json():
    import json
    p = qr_payload("m1", "2026-11-06T00:00:00Z", "FLOCK-0123456789ABCDEF", "cd" * 32)
    d = json.loads(p)
    assert d["mission"] == "m1" and d["ck"].startswith("FLOCK-")
    assert len(p) < 200


def test_render_slate_png(tmp_path):
    import pytest
    pytest.importorskip("PIL")
    matrix = [[(x + y) % 2 == 0 for x in range(21)] for y in range(21)]
    out = tmp_path / "slate.png"
    assert render_slate_png(out, "m1", "2026-11-06T00:00:00Z",
                            "FLOCK-0123456789ABCDEF", "{}", matrix=matrix)
    assert out.stat().st_size > 1000


def test_validate_qr_payload_boundary():
    import pytest
    good = qr_payload("m1", "2026-11-06T00:00:00Z", "FLOCK-0123456789ABCDEF")
    assert validate_qr_payload(good)["mission"] == "m1"
    for bad in ("not json", '{"v":2}', '{"v":1,"mission":"m"}',
                '{"v":1,"mission":"m","utc":"t","ck":"nope"}'):
        with pytest.raises(ValueError):
            validate_qr_payload(bad)
