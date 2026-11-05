from kulira_core.priority_split import run_split, score_trial_split
from kulira_core.relay_attack import generate_trial

def test_deterministic():
    t = generate_trial(1)
    assert score_trial_split(t, 1) == score_trial_split(t, 1)

def test_high_priority_safety_identical_to_e():
    out = run_split(range(20))
    assert out["F"]["dangerous_high"] == out["E"]["dangerous_high"]  # H-J1

def test_split_recall_between_and_dangerous_below_full_recheck():
    out = run_split(range(20))
    mid = (out["E"]["recall"] + out["E+R"]["recall"]) / 2
    assert out["F"]["recall"] >= mid - 1e-9  # H-J2
    assert out["F"]["dangerous"] < out["E+R"]["dangerous"]  # H-J3
