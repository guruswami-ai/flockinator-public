from kulira_core.colluding import generate_trial_colluding, run_colluding, score_colluding

def test_colluders_lie_only_on_hazards():
    t = generate_trial_colluding(0, k=3)
    for c in t:
        for r in c["reports"]:
            if r[5] and c["truth"] == "hazard":
                assert r[3] == "survivor"

def test_k0_matches_honest_baseline_no_colluder_commits():
    out = run_colluding(range(20), ks=(0,))
    assert out["E"]["0"]["colluder_dangerous"] == 0

def test_tolerance_curve_monotonic_in_k():
    out = run_colluding(range(20))
    e = [out["E"][str(k)]["colluder_dangerous"] for k in range(4)]
    assert e[0] == 0 and e[-1] > e[0]  # tolerance degrades with collusion size
    assert set(out["E"].keys()) == {"0", "1", "2", "3"}
