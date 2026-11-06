"""Flip-flop: determinism, alternation, hysteresis invariants."""
from kulira_core.flipflop import run_flipflop, run_seed_flip


def test_deterministic():
    assert run_seed_flip(5, 3, 2) == run_seed_flip(5, 3, 2)


def test_result_shape_and_bounds():
    r = run_seed_flip(5, 1, 1)
    assert set(r) == {"post_flip", "decision_flips", "latch_toggles_ir",
                      "rechecks", "first_latch_contact"}
    assert 0 <= r["decision_flips"] <= 29  # post-onset window only
    assert r["rechecks"] >= 0 and r["latch_toggles_ir"] >= 0
    assert r["post_flip"]["dangerous"] <= r["post_flip"]["hazards"]


def test_run_grid_keys():
    out = run_flipflop(range(3))
    assert list(out) == ["D1-R1", "D2-R2", "D3-R2", "D3-R4", "D5-R5"]
    for v in out.values():
        assert 0 <= v["latched_seeds"] <= 3
