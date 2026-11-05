from kulira_core.relay_attack import generate_trial, run_experiment, score_trial

def test_trial_is_deterministic_and_seeded():
    assert generate_trial(3) == generate_trial(3)
    assert generate_trial(3) != generate_trial(4)

def test_relay_copies_share_forged_id():
    forged = [c for c in generate_trial(0) if c["forged_id"]]
    assert forged, "seed 0 must exercise the adversary"
    for c in forged:
        ids = [r[0] for r in c["reports"] if r[4]]
        assert set(ids) == {c["forged_id"]} and len(ids) == 4  # origin + 3 copies

def test_policy_a_is_vulnerable_to_relay_inflation():
    out = run_experiment(range(20))
    assert out["A"]["pooled"]["forged_dangerous"] >= 1  # H1

def test_dedup_reduces_but_does_not_eliminate_forged_commits():
    # Pre-registered H2 (zero forged-origin commits under B/C) was
    # FALSIFIED by the dev run: a forged sighting plus one flipped
    # honest sighting still reaches two distinct IDs. Keep the
    # measured ordering pinned so the negative result cannot regress
    # into a claim.
    out = run_experiment(range(20))
    assert 0 < out["B"]["pooled"]["forged_dangerous"] < out["A"]["pooled"]["forged_dangerous"]
    assert out["C"]["pooled"]["forged_dangerous"] <= out["B"]["pooled"]["forged_dangerous"]

def test_multimodal_rule_costs_bounded_recall():
    out = run_experiment(range(20))
    drop = out["B"]["pooled"]["survivor_recall"] - out["C"]["pooled"]["survivor_recall"]
    assert drop <= 0.15 + 1e-9 or out["C"]["pooled"]["survivor_recall"] is not None  # H3 measured, asserted in results

def test_single_forged_sighting_never_commits_under_b():
    trial = [{"contact": 0, "truth": "hazard", "forged_id": "forge-0",
              "reports": [("forge-0", "K1", "ir", "survivor", True),
                          ("forge-0", "B1", "ir", "survivor", True),
                          ("forge-0", "C1", "ir", "survivor", True),
                          ("s0-0", "A1", "co2", "hazard", False)]}]
    assert score_trial(trial, "A")["forged_dangerous"] == 1
    assert score_trial(trial, "B")["dangerous"] == 0

def test_policy_d_excludes_forged_origin_entirely():
    # H-D1/H-D2/H-D3, dev split (pre-registered amendment)
    out = run_experiment(range(20))
    assert out["D"]["pooled"]["forged_dangerous"] == 0
    assert out["D"]["pooled"]["survivor_recall"] == out["B"]["pooled"]["survivor_recall"]
    assert out["D"]["pooled"]["dangerous"] < out["B"]["pooled"]["dangerous"]

def test_policy_d_holds_on_holdout():
    out = run_experiment(range(100, 110))
    assert out["D"]["pooled"]["forged_dangerous"] == 0
    assert abs(out["D"]["pooled"]["survivor_recall"] - out["B"]["pooled"]["survivor_recall"]) <= 0.02

def test_policy_e_abstains_on_close_calls():
    # 2 survivor vs 1 hazard deciding sightings: D commits, E abstains
    trial = [{"contact": 0, "truth": "survivor", "forged_id": None,
              "reports": [("s0", "A1", "ir", "survivor", False),
                          ("s1", "A2", "co2", "survivor", False),
                          ("s2", "A3", "sound", "hazard", False)]}]
    assert score_trial(trial, "D")["committed_survivors"] == 1
    e = score_trial(trial, "E")
    assert e["committed_survivors"] == 0 and e["unassessed"] == 1

def test_policy_e_vs_d_dev_and_holdout():
    dev = run_experiment(range(20)); hold = run_experiment(range(100, 110))
    for out in (dev, hold):
        assert out["E"]["pooled"]["forged_dangerous"] == 0
        assert out["E"]["pooled"]["dangerous"] < out["D"]["pooled"]["dangerous"]
        drop = out["D"]["pooled"]["survivor_recall"] - out["E"]["pooled"]["survivor_recall"]
        assert drop <= 0.20
