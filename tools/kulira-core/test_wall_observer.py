"""Wall observer: manifest chain, clock offset, tamper detection."""
import time

import pytest

from kulira_core.wall_observer import (
    Adb, AdbError, WallSession, device_tag, utc_iso, verify_session,
)


class FakeAdb(Adb):
    def __init__(self):
        super().__init__(serial="FAKESERIAL123")
        self.dcim = set()
        self.n = 0

    def phone_epoch(self):
        return time.time() + 2.0  # phone 2s ahead of host

    def model(self):
        return "Pixel 9a"

    def dcim_listing(self):
        return set(self.dcim)

    def shell(self, *args):
        if args[:2] == ("input", "keyevent"):
            self.n += 1
            self.dcim.add(f"IMG_20261106_1200{self.n:02d}.jpg")
        return ""

    def pull(self, remote, local):
        name = remote.rsplit("/", 1)[-1]
        with open(local, "wb") as f:
            f.write(b"JPEGDATA-" + name.encode())


def test_utc_iso_format():
    assert utc_iso(0) == "1970-01-01T00:00:00.000Z"


def test_device_tag_hides_serial():
    tag = device_tag("FAKESERIAL123")
    assert "FAKESERIAL123" not in tag and tag.startswith("sha256:")


def test_session_manifest_and_verify(tmp_path):
    adb = FakeAdb()
    s = WallSession(tmp_path / "s1", "mission-1", adb)
    assert s.start["payload"]["phone_minus_host_clock_s"] == pytest.approx(2.0, abs=0.6)
    assert "FAKESERIAL123" not in str(s.start)
    s.mark("beginning")
    entries = s.capture_still("beginning", burst=2, burst_gap_s=0)
    assert [e["payload"]["seq"] for e in entries] == [1, 2]
    s.mark("end")
    s.close()
    result = verify_session(tmp_path / "s1")
    assert result["log_verified"] and result["frames"] == 2


def test_verify_detects_tampered_frame(tmp_path):
    s = WallSession(tmp_path / "s2", "m", FakeAdb())
    s.capture_still("beginning", burst=1, burst_gap_s=0)
    s.close()
    frame = next((tmp_path / "s2" / "frames").glob("*.jpg"))
    frame.write_bytes(b"tampered")
    with pytest.raises(AdbError, match="sha256 mismatch"):
        verify_session(tmp_path / "s2")


def test_night_mode_forbidden(tmp_path):
    s = WallSession(tmp_path / "s3", "m", FakeAdb())
    with pytest.raises(AdbError, match="forbidden"):
        s.open_camera("NIGHT")
