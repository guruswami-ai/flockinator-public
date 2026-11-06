from kulira_core.twin import (DOUBLE_CHECK, SEARCH, WAIT, decide,
                              distribution_sweep, expected_distribution,
                              input_hash, parity,
                              run_twin, to_csv)


def test_decide_priority_order():
    assert decide(900, obstacle=False, pkt_loss=True) == WAIT
    assert decide(900, obstacle=True, pkt_loss=False) == WAIT
    assert decide(900, obstacle=False, pkt_loss=False) == DOUBLE_CHECK
    assert decide(699, obstacle=False, pkt_loss=False) == SEARCH
    assert decide(700, obstacle=False, pkt_loss=False) == DOUBLE_CHECK


def test_determinism_byte_identical():
    assert to_csv(run_twin(42, 200)) == to_csv(run_twin(42, 200))
    assert to_csv(run_twin(42, 200)) != to_csv(run_twin(43, 200))


def test_input_hash_stable_and_sensitive():
    h = input_hash(0, 42, 500, False, False)
    assert h == input_hash(0, 42, 500, False, False) and len(h) == 8
    assert h != input_hash(0, 42, 501, False, False)
    assert h != input_hash(0, 42, 500, True, False)


def test_perfect_link_parity_is_one():
    rows = run_twin(7, 100, p_loss=0.0)
    assert parity(rows, [dict(r) for r in rows])["parity"] == 1.0


def test_loss_forces_wait():
    rows = run_twin(7, 100, p_loss=1.0)
    assert all(r["decision"] == WAIT for r in rows)


def test_schema_header():
    assert to_csv(run_twin(1, 2)).splitlines()[0] == \
        "tick,seed,input_hash,decision,latency_us"


def test_parity_length_mismatch_is_failure_not_one():
    rows = run_twin(7, 100, p_loss=0.0)
    out = parity(rows, rows[:90])
    assert out["length_mismatch"] and out["parity"] is None


def test_expected_distribution_sums_to_one():
    for p in (0.0, 0.05, 0.10, 0.20):
        d = expected_distribution(p)
        assert abs(sum(d.values()) - 1.0) < 0.001
    assert expected_distribution(0.0)["WAIT"] == 0.10


def test_distribution_sweep_tracks_analytic():
    out = distribution_sweep(3, ticks=2000)
    for level, d in out.items():
        for name in ("SEARCH", "DOUBLE_CHECK", "WAIT"):
            assert abs(d["empirical"][name] - d["expected"][name]) < 0.05
