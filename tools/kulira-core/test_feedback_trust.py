from kulira_core.feedback_trust import score_sequence_feedback
from kulira_core.reputation import generate_sequence, score_sequence


def test_full_feedback_compatibility():
    for policy in ("E", "REP", "REP-P"):
        base = score_sequence(generate_sequence(11), policy)
        fb = score_sequence_feedback(generate_sequence(11), policy,
                                     delay=0, availability=1.0, reveal_seed=999)
        for k in ("dangerous_first", "dangerous_second", "recall",
                  "rep_colluders", "rep_honest"):
            assert fb[k] == base[k], (policy, k)


def test_truth_boundary_future_outcomes_cannot_affect_early_decisions():
    seq_a = generate_sequence(11)
    seq_b = [dict(c) for c in seq_a]
    for c in seq_b[40:]:  # flip every later truth; reports unchanged in form
        c["truth"] = "hazard" if c["truth"] == "survivor" else "survivor"
    a = score_sequence_feedback(seq_a, "REP", delay=15, reveal_seed=1)
    b = score_sequence_feedback(seq_b, "REP", delay=15, reveal_seed=1)
    # decisions before any flipped outcome could be revealed (40-15=25..)
    assert a["decision_log"][:40] == b["decision_log"][:40]


def test_no_reveal_means_no_learning():
    out = score_sequence_feedback(generate_sequence(11), "REP",
                                  delay=0, availability=0.0, reveal_seed=1)
    assert out["rep_colluders"] == 1.0 and out["rep_honest"] == 1.0


def test_e_policy_ignores_feedback_parameters():
    a = score_sequence_feedback(generate_sequence(11), "E", delay=0, availability=1.0)
    b = score_sequence_feedback(generate_sequence(11), "E", delay=15, availability=0.25)
    assert a["decision_log"] == b["decision_log"]


def test_early_unrevealed_outcomes_cannot_affect_decisions():
    # Issue #158 probe: flip truths at contacts 0-14 (reports kept);
    # with delay=15 none of those outcomes is revealed before
    # contact 15, so decisions 0-14 must be identical. A runner
    # that ignores delay changes decisions at 4, 9, 11, 12 here.
    seq_a = generate_sequence(11)
    seq_b = [dict(c) for c in seq_a]
    for c in seq_b[:15]:
        c["truth"] = "hazard" if c["truth"] == "survivor" else "survivor"
    a = score_sequence_feedback(seq_a, "REP", delay=15,
                                availability=1.0, reveal_seed=1)
    b = score_sequence_feedback(seq_b, "REP", delay=15,
                                availability=1.0, reveal_seed=1)
    assert a["decision_log"][:15] == b["decision_log"][:15]


def test_exact_reveal_boundary_and_learning_sensitivity():
    # Positive control: after the reveal boundary the flipped
    # outcomes MUST be able to change decisions - otherwise the
    # boundary test above would pass vacuously for a runner that
    # never learns at all.
    seq_a = generate_sequence(11)
    seq_b = [dict(c) for c in seq_a]
    for c in seq_b[:15]:
        c["truth"] = "hazard" if c["truth"] == "survivor" else "survivor"
    a = score_sequence_feedback(seq_a, "REP", delay=15,
                                availability=1.0, reveal_seed=1)
    b = score_sequence_feedback(seq_b, "REP", delay=15,
                                availability=1.0, reveal_seed=1)
    assert a["decision_log"] != b["decision_log"]  # learning engages
    frozen = score_sequence_feedback(seq_a, "REP", delay=15,
                                     availability=0.0, reveal_seed=1)
    assert frozen["decision_log"] != a["decision_log"]


def test_permanently_unavailable_feedback_never_discounts():
    out = score_sequence_feedback(generate_sequence(11), "REP-P",
                                  delay=5, availability=0.0, reveal_seed=3)
    assert out["rep_colluders"] == 1.0 and out["rep_honest"] == 1.0
