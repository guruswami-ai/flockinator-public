from kulira_core.composite import generate_world, run_composite, score_world

def test_deterministic():
    assert score_world(generate_world(3), "COMP") == score_world(generate_world(3), "COMP")

def test_forged_origin_stays_zero_under_both():
    out = run_composite(range(20))
    assert out["E"]["forged_dangerous"] == 0 and out["COMP"]["forged_dangerous"] == 0

def test_composite_reduces_post_betrayal_dangerous():
    out = run_composite(range(20))
    assert out["COMP"]["dangerous_post"] < out["E"]["dangerous_post"]
