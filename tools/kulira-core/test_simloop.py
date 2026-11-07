from kulira_core.simloop import run_loop


def test_loop_finds_survivor_deterministically():
    a = run_loop(42, ticks=300)
    b = run_loop(42, ticks=300)
    assert a["found_tick"] is not None and a["found_tick"] < 300
    assert a["journal"] == b["journal"] and a["frames"] == b["frames"] == a["ticks_run"] * 4


def test_loop_journal_schema():
    out = run_loop(1, ticks=10)
    assert out["journal"][0].keys() == {"tick", "seed", "input_hash", "decision", "latency_us"}


def test_missing_input_ticks_journal_wait_and_still_deterministic():
    from kulira_core.twin import WAIT, missing_hash
    drops = frozenset({5, 6, 7, 20})
    a = run_loop(42, ticks=300, drop_ticks=drops)
    b = run_loop(42, ticks=300, drop_ticks=drops)
    assert a["journal"] == b["journal"]
    for t in drops:
        row = a["journal"][t]
        assert row["decision"] == WAIT and row["input_hash"] == missing_hash(t, 42)
    assert a["found_tick"] is not None  # brief loss degrades, not fatal


def test_heavy_loss_prevents_find_within_budget():
    drops = frozenset(range(0, 300, 2))  # every second tick missing
    out = run_loop(42, ticks=120, drop_ticks=drops)
    assert out["ticks_run"] == 120
