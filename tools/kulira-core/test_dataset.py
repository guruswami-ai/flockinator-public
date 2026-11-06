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
    assert verify_dataset(tmp_path / "ds")["verified"]


def test_build_rejects_unredacted_telemetry(tmp_path):
    s = WallSession(tmp_path / "sess", "m1", JpegAdb())
    s.capture_still("beginning", burst=1, burst_gap_s=0)
    s.close()
    tel = tmp_path / "runs"; tel.mkdir()
    (tel / "bad.json").write_text('{"host": "10.61.106.205"}')
    with pytest.raises(DatasetError, match="redaction scan failed"):
        build_dataset(tmp_path / "sess", tel, tmp_path / "ds", "m1")
