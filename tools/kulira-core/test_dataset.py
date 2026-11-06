"""Dataset packager: metadata strip, redaction gate, silent-only rule."""
import json

import pytest

from kulira_core.dataset import (
    DatasetError, build_dataset, scan_text, strip_jpeg_metadata,
    verify_dataset,
)
from kulira_core.wall_observer import WallSession
from test_wall_observer import FakeAdb


def _jpeg(with_exif=True):
    app1 = b"\xff\xe1" + (17).to_bytes(2, "big") + b"Exif\x00\x00GPSDATA!!" if with_exif else b""
    dqt = b"\xff\xdb" + (4).to_bytes(2, "big") + b"\x00\x10"
    sos = b"\xff\xda" + (4).to_bytes(2, "big") + b"\x01\x00" + b"\x11\x22\xff\xd9"
    return b"\xff\xd8" + app1 + dqt + sos


def test_strip_jpeg_metadata():
    out = strip_jpeg_metadata(_jpeg())
    assert b"Exif" not in out and b"GPSDATA" not in out
    assert out.endswith(b"\x11\x22\xff\xd9")  # entropy data preserved
    with pytest.raises(DatasetError):
        strip_jpeg_metadata(b"notajpeg")


def test_scan_text_finds_secrets():
    assert scan_text('{"ip": "10.0.0.5"}')
    assert scan_text("aa:bb:cc:dd:ee:ff")
    assert scan_text("/Users/someone/file")
    assert scan_text('{"seed": 3, "recall": 0.5}') == []


class JpegAdb(FakeAdb):
    def pull(self, remote, local):
        with open(local, "wb") as f:
            f.write(_jpeg())


def test_build_and_verify_dataset(tmp_path):
    s = WallSession(tmp_path / "sess", "m1", JpegAdb())
    s.capture_still("beginning", burst=1, burst_gap_s=0)
    s.close()
    tel = tmp_path / "runs"; tel.mkdir()
    (tel / "score.json").write_text('{"seed": 0, "recall": 0.5}')
    manifest = build_dataset(tmp_path / "sess", tel, tmp_path / "ds", "m1")
    assert manifest["files"][0]["metadata_stripped"] is True
    # derivative attempted (None when ffmpeg cannot read the fixture)
    assert "web_derivative" in manifest["files"][0]
    assert verify_dataset(tmp_path / "ds")["verified"]


def test_build_rejects_unredacted_telemetry(tmp_path):
    s = WallSession(tmp_path / "sess", "m1", JpegAdb())
    s.capture_still("beginning", burst=1, burst_gap_s=0)
    s.close()
    tel = tmp_path / "runs"; tel.mkdir()
    (tel / "bad.json").write_text('{"host": "10.61.106.205"}')
    with pytest.raises(DatasetError, match="redaction scan failed"):
        build_dataset(tmp_path / "sess", tel, tmp_path / "ds", "m1")


def test_scan_text_variants_and_no_timestamp_false_positive():
    from kulira_core.dataset import scan_text as st
    assert st("AA-BB-CC-DD-EE-FF")          # dash MAC (fleet finding)
    assert st("AABB.CCDD.EEFF")             # dotted MAC
    assert st("fe80::1")                    # compressed IPv6
    assert st("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
    assert st("/Users/alice")               # no trailing slash
    assert st("/home/alice/x.json")
    assert st(r"C:\Users\Alice\x.json")
    assert st("mbp-alice.local")
    # ordinary telemetry must stay clean: ISO timestamps are not IPv6
    assert st('{"ts": "2026-11-06T12:34:56Z", "seed": 3}') == []


def test_strip_png_metadata():
    import struct, zlib
    from kulira_core.dataset import strip_png_metadata
    def chunk(typ, body):
        c = struct.pack(">I", len(body)) + typ + body
        return c + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", b"\x00" * 13)
           + chunk(b"tEXt", b"GPS\x00somewhere") + chunk(b"IDAT", b"\x01\x02")
           + chunk(b"IEND", b""))
    out = strip_png_metadata(png)
    assert b"GPS" not in out and b"somewhere" not in out
    assert b"IDAT" in out and out.endswith(chunk(b"IEND", b""))


def test_strip_jpeg_padding_and_standalone_markers():
    # FF fill byte + TEM standalone marker before APP1/DQT
    data = (b"\xff\xd8" + b"\xff\xff\xe1" + (6).to_bytes(2, "big") + b"Exif"
            + b"\xff\x01" + b"\xff\xdb" + (4).to_bytes(2, "big") + b"\x00\x10"
            + b"\xff\xda" + (4).to_bytes(2, "big") + b"\x01\x00" + b"\x11\x22")
    out = strip_jpeg_metadata(data)
    assert b"Exif" not in out and out.endswith(b"\x11\x22")
