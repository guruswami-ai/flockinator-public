import pytest

from kulira_core.feedback_trust import score_sequence_feedback
from kulira_core.reputation import PROBATION, generate_sequence, score_sequence


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
    # The first changed outcome, at contact 40, is revealed at 40 + 15 = 55.
    assert a["decision_log"][:55] == b["decision_log"][:55]


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


def _three_report_sequence(truths):
    # Unit weights commit on these two survivor reports and one hazard report.
    return [
        {"contact": i, "truth": truth, "reports": [
            (f"s{i}-0", "A1", "ir", "survivor", False),
            (f"s{i}-1", "A2", "co2", "survivor", False),
            (f"s{i}-2", "B1", "sound", "hazard", False),
        ]}
        for i, truth in enumerate(truths)
    ]


@pytest.mark.parametrize("delay", [0, 3, 15])
def test_rep_changes_decision_at_reveal_and_not_before(delay):
    # Delay zero learns after the current decision, so first affects contact 1.
    reveal_contact = max(1, delay)
    wrong_reports = _three_report_sequence(["hazard"] + ["survivor"] * reveal_contact)
    right_reports = _three_report_sequence(["survivor"] * (reveal_contact + 1))
    wrong = score_sequence_feedback(wrong_reports, "REP", delay=delay, availability=1.0)
    right = score_sequence_feedback(right_reports, "REP", delay=delay, availability=1.0)

    # Only the first truth differs; neither policy can use it before its reveal.
    assert wrong["decision_log"][:reveal_contact] == [True] * reveal_contact
    assert right["decision_log"][:reveal_contact] == [True] * reveal_contact
    # One revealed error lowers the survivor reporters enough to stop committing.
    assert wrong["decision_log"][reveal_contact] is False
    assert right["decision_log"][reveal_contact] is True


@pytest.mark.parametrize("delay", [0, 3, 15])
def test_probation_counts_revealed_outcomes_not_reported_contacts(delay):
    graduation_contact = PROBATION - 1 + max(1, delay)
    seq = _three_report_sequence(["hazard"] * (graduation_contact + 1))
    out = score_sequence_feedback(seq, "REP-P", delay=delay, availability=1.0)

    # Until PROBATION outcomes arrive, the reporters retain full decision weight.
    assert out["decision_log"][:graduation_contact] == [True] * graduation_contact
    # The last required reveal must change the decision immediately, not later.
    assert out["decision_log"][graduation_contact] is False
