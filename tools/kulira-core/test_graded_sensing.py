from kulira_core.graded_sensing import run_graded, score_trial_graded
from kulira_core.relay_attack import generate_trial

def test_deterministic():
    t = generate_trial(2)
    assert score_trial_graded(t, 2) == score_trial_graded(t, 2)

def test_recheck_recovers_recall_without_more_dangerous():
    out = run_graded(range(20))
    assert out["E+R"]["recall"] > out["E"]["recall"]
    assert out["E+R"]["rechecks_per_contact"] <= 0.5
