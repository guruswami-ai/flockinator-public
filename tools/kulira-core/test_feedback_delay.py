from kulira_core.feedback_delay import run_feedback, run_seed_delayed

def test_deterministic():
    assert run_seed_delayed(4, 5, 0.5) == run_seed_delayed(4, 5, 0.5)

def test_delay_slows_discount():
    out = run_feedback(range(20), conditions=((0, 0.0), (15, 0.0)))
    assert out["d15-m0.0"]["median_discount_contacts"] >= out["d0-m0.0"]["median_discount_contacts"] + 5

def test_degraded_learning_still_beats_static_parent():
    # static parent arm: 306 dangerous on dev seeds 0-19
    out = run_feedback(range(20), conditions=((15, 0.5),))
    assert out["d15-m0.5"]["dangerous"] < 306
