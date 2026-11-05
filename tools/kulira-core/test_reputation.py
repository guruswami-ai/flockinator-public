from kulira_core.reputation import generate_sequence, run_reputation, score_sequence

def test_deterministic():
    assert score_sequence(generate_sequence(2), "REP") == score_sequence(generate_sequence(2), "REP")

def test_reputation_separates_colluders():
    out = run_reputation(range(20))
    assert out["REP"]["rep_colluders"] < out["REP"]["rep_honest"]

def test_second_half_dangerous_reduced():
    out = run_reputation(range(20))
    assert out["REP"]["dangerous_second"] < out["E"]["dangerous_second"]
