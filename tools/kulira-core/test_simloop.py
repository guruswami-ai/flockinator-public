from kulira_core.simloop import run_loop


def test_loop_finds_survivor_deterministically():
    a = run_loop(42, ticks=300)
    b = run_loop(42, ticks=300)
    assert a["found_tick"] is not None and a["found_tick"] < 300
    assert a["journal"] == b["journal"] and a["frames"] == b["frames"] == a["ticks_run"] * 4


def test_loop_journal_schema():
    out = run_loop(1, ticks=10)
    assert out["journal"][0].keys() == {"tick", "seed", "input_hash", "decision", "latency_us"}
