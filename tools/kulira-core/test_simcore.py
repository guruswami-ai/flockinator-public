from kulira_core.simcore import HIDDEN, World
from kulira_core.simwire import Reassembler, snapshot_frames, unpack_frame

KEY = b"k" * 32
RUN = bytes(range(16))


def test_snapshot_size_and_hidden_survivor():
    w = World(42)
    snap = w.snapshot()
    assert len(snap) == 392
    d = World.decode(snap)
    assert d["survivor"] == (HIDDEN, HIDDEN)
    assert World.decode(w.snapshot(reveal_survivor=True))["survivor"] == (2400, 2400)


def test_deterministic_steps():
    a, b = World(1), World(1)
    for _ in range(50):
        a.step({0: (100, 0), 5: (0, -50)})
        b.step({0: (100, 0), 5: (0, -50)})
    assert a.snapshot() == b.snapshot()
    assert a.robots[0]["x"] > 200 and a.robots[5]["y"] < 600


def test_hold_default_and_clamp():
    w = World(1)
    w.step({})
    assert all(r["speed"] == 0 for r in w.robots)
    w.step({0: (99999, 0)})
    assert w.robots[0]["x"] - 200 <= 30  # clamped speed 300cm/s -> 30dm/tick


def test_snapshot_flows_through_simwire():
    w = World(9)
    w.step({1: (50, 50)})
    frames = snapshot_frames(KEY, w.tick, RUN, 9, 1, w.snapshot(), 0)
    r, world = Reassembler(), None
    for f in frames:
        hdr, pay = unpack_frame(KEY, f)
        world = r.feed(hdr, pay) or world
    assert World.decode(world)["tick"] == w.tick
