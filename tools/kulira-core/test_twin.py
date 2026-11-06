from kulira_core.twin import (DOUBLE_CHECK, SEARCH, WAIT, decide,
                              input_hash, parity, run_twin, to_csv)


def test_decide_priority_order():
    assert decide(0.9, obstacle=False, pkt_loss=True) == WAIT
    assert decide(0.9, obstacle=True, pkt_loss=False) == WAIT
    assert decide(0.9, obstacle=False, pkt_loss=False) == DOUBLE_CHECK
    assert decide(0.2, obstacle=False, pkt_loss=False) == SEARCH


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
