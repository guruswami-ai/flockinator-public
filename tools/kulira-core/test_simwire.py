import struct

from kulira_core.simwire import (FRAG_N, EventTracker, IntentGate,
                                 Reassembler, fnv1a, snapshot_frames,
                                 unpack_frame, pack_frame, INTENT,
                                 RESYNC_REPLY)

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


# --- apply-once watermark / run-context regressions -------------------------
WORLD_B = bytes((i * 11 + 3) % 256 for i in range(392))
WORLD_C = bytes((i * 13 + 5) % 256 for i in range(392))
RUN_B = bytes(range(16, 32))


def _deliver(r, frames, order=None):
    """Feed frames (optionally by index order); return the delivered world, if any."""
    got = None
    for i in (range(len(frames)) if order is None else order):
        hdr, pay = unpack_frame(KEY, frames[i])
        got = r.feed(hdr, pay) or got
    return got


def _resync_frames(tick, world, prev_hash, run=RUN, seed=42, cycle=1):
    """RESYNC_REPLY: SNAP_FRAG layout with KIND=5 and TICK=want_tick (spec 2.5)."""
    out = []
    for f in snapshot_frames(KEY, tick, run, seed, cycle, world, prev_hash):
        hdr, pay = unpack_frame(KEY, f)
        out.append(pack_frame(KEY, RESYNC_REPLY, hdr["sender"], tick, run, seed, cycle, pay))
    return out


def test_reassembler_full_replay_of_delivered_snapshot_not_reemitted():
    r = Reassembler()
    f5 = snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)
    assert _deliver(r, f5) == WORLD
    assert _deliver(r, f5) is None                       # all four frags again
    assert _deliver(r, f5, order=(3, 1, 0, 2)) is None   # shuffled replay
    assert r.last_tick == 5 and r.mask == 0
    f6 = snapshot_frames(KEY, 6, RUN, 42, 1, WORLD_B, fnv1a(WORLD))
    assert _deliver(r, f6, order=(2, 3, 0, 1)) == WORLD_B  # next tick, out of order
    assert r.last_tick == 6


def test_reassembler_older_completed_snapshot_not_delivered():
    r = Reassembler()
    assert _deliver(r, snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)) == WORLD
    assert _deliver(r, snapshot_frames(KEY, 3, RUN, 42, 1, WORLD_B, 100)) is None  # no rollback
    assert r.last_tick == 5 and r.tick is None and r.mask == 0
    assert _deliver(r, snapshot_frames(KEY, 7, RUN, 42, 1, WORLD_C, 0)) == WORLD_C


def test_reassembler_partial_newer_tick_never_reopens_delivered_ticks():
    r = Reassembler()
    f5 = snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)
    f6 = snapshot_frames(KEY, 6, RUN, 42, 1, WORLD_B, 600)
    f7 = snapshot_frames(KEY, 7, RUN, 42, 1, WORLD_C, 700)
    assert _deliver(r, f5) == WORLD
    assert _deliver(r, f7, order=(0, 2)) is None        # tick 7 half assembled, live
    assert _deliver(r, f5) is None                      # replayed delivered tick
    assert _deliver(r, f6) is None                      # complete, but older than the slot
    assert r.tick == 7 and r.mask == 0b0101             # slot untouched by either
    assert _deliver(r, f7, order=(3, 1)) == WORLD_C     # finishing tick 7 delivers once
    assert _deliver(r, f6) is None                      # still dropped once the slot cleared
    assert _deliver(r, f7) is None
    assert r.last_tick == 7


def test_reassembler_drop_partial_then_late_fragments_stay_dropped():
    r = Reassembler()
    assert _deliver(r, snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)) == WORLD
    f6 = snapshot_frames(KEY, 6, RUN, 42, 1, WORLD_B, 600)
    assert _deliver(r, f6, order=(1,)) is None          # 1 of 4 for tick 6
    f7 = snapshot_frames(KEY, 7, RUN, 42, 1, WORLD_C, 700)
    assert _deliver(r, f7, order=(2, 0, 3, 1)) == WORLD_C  # newer tick: 6 dropped partial
    assert r.gaps == 1
    assert _deliver(r, f6) is None                      # late tick-6 frags cannot revive it
    assert r.tick is None and r.mask == 0 and r.last_tick == 7


def test_reassembler_resync_reply_catches_up_but_never_rolls_back():
    r = Reassembler()
    assert _deliver(r, snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)) == WORLD
    assert _deliver(r, _resync_frames(9, WORLD_B, 800), order=(1, 0, 3, 2)) == WORLD_B
    assert _deliver(r, _resync_frames(9, WORLD_B, 800)) is None   # replayed reply
    assert _deliver(r, _resync_frames(5, WORLD, 123)) is None     # older checkpoint
    assert _deliver(r, snapshot_frames(KEY, 10, RUN, 42, 1, WORLD_C, fnv1a(WORLD_B))) == WORLD_C


def test_reassembler_begin_is_the_only_run_reset():
    r = Reassembler()
    assert _deliver(r, snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)) == WORLD
    new_run = snapshot_frames(KEY, 0, RUN_B, 7, 2, WORLD_B, 0)   # new run_id, cycle++
    assert _deliver(r, new_run) is None                          # data plane cannot switch runs
    assert r.run_id == (RUN, 42, 1) and r.last_tick == 5
    r.begin(RUN_B, 7, 2)                                         # caller-authorised restart
    assert r.last_tick is None and r.gaps == 0
    assert _deliver(r, new_run, order=(3, 0, 2, 1)) == WORLD_B   # ticks restart at 0
    assert _deliver(r, new_run) is None                          # replay inside the new run
    assert _deliver(r, snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)) is None  # old run
    assert _deliver(r, snapshot_frames(KEY, 1, RUN_B, 7, 2, WORLD_C, fnv1a(WORLD_B))) == WORLD_C


def test_reassembler_begin_before_first_frame_pins_context():
    import pytest
    r = Reassembler()
    r.begin(RUN, 42, 1)
    assert _deliver(r, snapshot_frames(KEY, 0, RUN_B, 42, 1, WORLD, 0)) is None  # foreign run
    assert _deliver(r, snapshot_frames(KEY, 0, RUN, 42, 1, WORLD, 0)) == WORLD
    with pytest.raises(ValueError):
        r.begin(b"short", 42, 1)


def test_reassembler_same_run_seed_or_cycle_change_rejected_when_idle():
    r = Reassembler()
    assert _deliver(r, snapshot_frames(KEY, 5, RUN, 42, 1, WORLD, 123)) == WORLD
    assert _deliver(r, snapshot_frames(KEY, 6, RUN, 42, 2, WORLD_B, 0)) is None  # cycle++, same run
    assert _deliver(r, snapshot_frames(KEY, 6, RUN, 43, 1, WORLD_B, 0)) is None  # seed change
    assert r.run_id == (RUN, 42, 1) and r.last_tick == 5 and r.mask == 0
    assert _deliver(r, snapshot_frames(KEY, 6, RUN, 42, 1, WORLD_B, fnv1a(WORLD))) == WORLD_B
