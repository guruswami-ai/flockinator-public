import struct

from kulira_core.simwire import (FRAG_N, EventTracker, IntentGate,
                                 Reassembler, fnv1a, snapshot_frames,
                                 unpack_frame, pack_frame, INTENT)

KEY = b"k" * 32
RUN = bytes(range(16))
WORLD = bytes((i * 7) % 256 for i in range(392))


def test_roundtrip_and_tag_tamper_rejected():
    frames = snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)
    assert len(frames) == FRAG_N and all(len(f) <= 160 for f in frames)
    hdr, _ = unpack_frame(KEY, frames[0])
    assert hdr["tick"] == 5 and hdr["seed"] == 42
    bad = bytearray(frames[0]); bad[40] ^= 1
    assert unpack_frame(KEY, bytes(bad)) is None
    assert unpack_frame(b"wrong-key-32-bytes-padded!!", frames[0]) is None


def test_reassembly_out_of_order_and_drop_partial():
    frames = snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)
    r = Reassembler()
    world = None
    for f in (frames[2], frames[0], frames[3], frames[1]):
        hdr, pay = unpack_frame(KEY, f)
        world = r.feed(hdr, pay) or world
    assert world == WORLD
    # partial next tick then newer tick -> gap counted, no cross-merge
    f6 = snapshot_frames(KEY, 6, RUN, 42, 1, WORLD, 124)
    hdr, pay = unpack_frame(KEY, f6[0]); assert r.feed(hdr, pay) is None
    f7 = snapshot_frames(KEY, 7, RUN, 42, 1, WORLD, 125)
    hdr, pay = unpack_frame(KEY, f7[0]); r.feed(hdr, pay)
    assert r.gaps >= 1


def test_intent_gate_pipeline_and_hold():
    g = IntentGate()
    assert g.offer(3, 0, 10, b"\x01\x02") is True
    assert g.offer(3, 0, 10, b"\x01\x02") is False  # duplicate seq
    assert g.for_tick(3, 11) == b"\x00\x00"          # too fresh: HOLD
    assert g.for_tick(3, 12) == b"\x01\x02"          # usable at T-2
    assert g.for_tick(9, 99) == b"\x00\x00"          # unknown node: HOLD


def test_event_apply_once():
    t = EventTracker()
    assert t.apply(7, 10, 9) is False
    assert t.apply(7, 10, 10) is True
    assert t.apply(7, 10, 11) is False


def test_fnv_matches_twin_definition():
    assert fnv1a(b"") == 0x811C9DC5
    assert fnv1a(b"a") == 0xE40C292C


def test_reassembler_rejects_bad_fragments():
    r = Reassembler()
    frames = snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)
    hdr, pay = unpack_frame(KEY, frames[0])
    assert r.feed(hdr, pay[:50]) is None            # short payload
    bad = struct.pack("<BBI", 4, 9, 123) + pay[6:]  # idx out of range
    assert r.feed(hdr, bad) is None
    fork = struct.pack("<BBI", 4, 1, 999) + pay[6:]  # prev_hash fork
    r.feed(hdr, pay)
    assert r.feed(hdr, fork) is None


def test_reassembler_apply_once():
    frames = snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)
    r = Reassembler()
    got = None
    for f in frames:
        hdr, pay = unpack_frame(KEY, f)
        got = r.feed(hdr, pay) or got
    assert got == WORLD
    hdr, pay = unpack_frame(KEY, frames[0])
    assert r.feed(hdr, pay) is None  # duplicate after complete: no re-emit


def test_intent_single_use_and_expiry():
    g = IntentGate()
    g.offer(3, 0, 10, b"\x01\x02")
    assert g.for_tick(3, 12) == b"\x01\x02"
    assert g.for_tick(3, 13) == b"\x00\x00"  # consumed, not replayed
    g.offer(3, 1, 10, b"\x03\x04")
    assert g.for_tick(3, 100) == b"\x00\x00"  # expired


def test_pack_frame_rejects_oversize():
    import pytest
    with pytest.raises(ValueError):
        pack_frame(KEY, INTENT, 1, 0, RUN, 1, 1, b"x" * 200)


def test_reassembler_rejects_mixed_context_same_tick():
    r = Reassembler()
    f_a = snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)
    f_b = snapshot_frames(KEY, 5, RUN, 43, 1, WORLD, 123)  # different seed
    hdr, pay = unpack_frame(KEY, f_a[0]); assert r.feed(hdr, pay) is None
    hdr, pay = unpack_frame(KEY, f_b[1]); assert r.feed(hdr, pay) is None
    assert r.mask == 0b0001  # only the first context's frag held


def test_completed_snapshot_replay_rejected():
    frames = snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)
    r = Reassembler()
    got = None
    for f in frames:
        hdr, pay = unpack_frame(KEY, f)
        got = r.feed(hdr, pay) or got
    assert got == WORLD
    # full replay of the completed tick: every frag rejected
    for f in frames:
        hdr, pay = unpack_frame(KEY, f)
        assert r.feed(hdr, pay) is None
    # and a stale older tick too
    old = snapshot_frames(KEY, 3, RUN, 42, 1, WORLD, 122)
    hdr, pay = unpack_frame(KEY, old[0])
    assert r.feed(hdr, pay) is None


def test_authorized_reset_lifecycle():
    r = Reassembler()
    frames_a = snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)
    got = None
    for f in frames_a:
        hdr, pay = unpack_frame(KEY, f)
        got = r.feed(hdr, pay) or got
    assert got == WORLD
    run_b = bytes(range(16, 32))
    frames_b = snapshot_frames(KEY, 0, run_b, 42, 2, WORLD, 0)
    hdr, pay = unpack_frame(KEY, frames_b[0])
    assert r.feed(hdr, pay) is None  # new run on wire alone does NOT reset
    r.reset(run_b, 42, 2)            # management-authorized reset
    got = None
    for f in frames_b:
        hdr, pay = unpack_frame(KEY, f)
        got = r.feed(hdr, pay) or got
    assert got == WORLD
    hdr, pay = unpack_frame(KEY, frames_a[0])
    assert r.feed(hdr, pay) is None  # stale run A traffic still rejected
