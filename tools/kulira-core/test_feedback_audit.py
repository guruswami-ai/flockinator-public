"""Regression evidence for additive historical reporting, no fresh experiment seeds."""
import copy
import json
from pathlib import Path

import pytest

from kulira_core.feedback_audit import (
    audit_seed, build_report, difference_summary, main, paired_metrics,
    reveal_counts, window_metrics,
)
from kulira_core.feedback_trust import run_feedback, score_sequence_feedback


def fixture():
    return [{"contact": i, "truth": truth, "reports": [
        (f"s{i}-0", "A1", "ir", "survivor", False),
        (f"s{i}-1", "A2", "co2", "survivor", False),
        (f"s{i}-2", "B1", "sound", "hazard", False),
    ]} for i, truth in enumerate(["hazard", "survivor", "hazard", "survivor"])]


def test_window_counts_are_not_whole_sequence_fields():
    out = window_metrics(fixture(), [True, False, False, True], 2, 4)
    assert out == dict(contacts=2, hazards=1, survivors=1, dangerous=0,
                       found=1, commits=1, abstentions=1, harm_rate=0,
                       recall=1, coverage=0.5)
    assert window_metrics(fixture(), [False]*4, 0, 1)["recall"] is None


def test_reveal_budget_preserves_current_contact_and_flush_boundaries():
    seq = fixture()
    full = reveal_counts(seq, 0, 1, 0, 2, 4)
    assert full == dict(outcome_draws=4, selected_outcomes=4,
                        selected_outcomes_in_window=2, offered_report_updates=12,
                        applied_before_decisions=9, applied_before_window_decisions=6,
                        post_horizon_flush=3)
    delayed = reveal_counts(seq, 3, 1, 0, 2, 4)
    assert delayed["applied_before_decisions"] == 3
    assert delayed["post_horizon_flush"] == 9
    assert reveal_counts(seq, 0, 0, 0, 2, 4)["offered_report_updates"] == 0


def test_budget_deduplicates_ids_and_never_reads_truth_or_labels():
    seq = fixture()
    seq[0]["reports"].append(seq[0]["reports"][0])
    original = reveal_counts(seq, 0, 1, 0, 2, 4)
    for c in seq:
        c.pop("truth")
        c["reports"] = [(r[0],) for r in c["reports"]]
    assert reveal_counts(seq, 0, 1, 0, 2, 4) == original
    assert original["offered_report_updates"] == 12


def test_audit_does_not_change_source_decisions_or_future_truth_boundary():
    first = fixture()
    later = copy.deepcopy(first)
    later[0]["truth"] = "survivor"
    a = score_sequence_feedback(first, "REP", delay=3, availability=1)
    b = score_sequence_feedback(later, "REP", delay=3, availability=1)
    saved = copy.deepcopy(a)
    window_metrics(first, a["decision_log"], 0, 4)
    reveal_counts(first, 3, 1, 0, 0, 4)
    assert a == saved
    assert a["decision_log"][:3] == b["decision_log"][:3]
    assert a["decision_log"][3] != b["decision_log"][3]
    assert reveal_counts(first, 3, 1, 0, 0, 4) == reveal_counts(later, 3, 1, 0, 0, 4)


def test_pairing_and_undefined_rates_remain_explicit():
    a = window_metrics(fixture(), [True, False, False, True], 0, 4)
    b = window_metrics(fixture(), [False]*4, 0, 4)
    assert paired_metrics(a, b)["harm_rate"] == 0.5
    assert paired_metrics(a, b)["recall"] == 0.5
    empty = difference_summary([None, None])
    assert empty == dict(n=0, undefined=2, mean=None, interval=None)
    out = difference_summary([0.2, None, -0.2])
    assert out["n"] == 2 and out["undefined"] == 1 and out["mean"] == 0
    assert out["interval"] == [-1, 1]


@pytest.mark.parametrize("seed", [219, 260, True, 220.0])
def test_audit_rejects_unexposed_or_malformed_seeds(seed):
    with pytest.raises(ValueError):
        audit_seed(seed, 0, 1)


@pytest.mark.parametrize("delay,availability", [(-1,1), (True,1), (0,float("nan")), (0,True), (0,1.1)])
def test_invalid_reveal_parameters_reject(delay, availability):
    with pytest.raises(ValueError):
        reveal_counts(fixture(), delay, availability, 0, 0, 4)


def test_malformed_windows_and_decisions_reject():
    with pytest.raises(ValueError):
        window_metrics(fixture(), [1]*4, 0, 4)
    with pytest.raises(ValueError):
        window_metrics(fixture(), [False]*4, 3, 2)
    with pytest.raises(ValueError):
        window_metrics(list(reversed(fixture())), [False]*4, 0, 4)


def test_historical_aggregates_and_report_are_unchanged_and_complete():
    root = Path(__file__).resolve().parents[2]
    report = build_report()
    published = root/"validation/kulira/feedback-trust-posthoc-audit-001.json"
    assert report == json.loads(published.read_text())
    for split, seeds, delays, avails in (
        ("dev", range(220,240), (0,5,15), (1.0,0.5,0.25)),
        ("confirmatory", range(240,260), (0,15), (1.0,0.25)),
    ):
        expected = json.loads((root/f"validation/kulira/feedback-trust-{split}-001.json").read_text())["results"]
        assert run_feedback(seeds, delays, avails) == expected
        cells = report["splits"][split]["cells"]
        assert len(cells) == len(delays)*len(avails)
        for cell in cells:
            assert [r["seed"] for r in cell["per_seed"]] == list(seeds)
            for policy in ("E","REP","REP-P"):
                key = f"{policy} d={cell['delay']} a={cell['availability']}"
                assert cell["summary"]["policies"][policy]["dangerous"] == expected[key]["dangerous_second"]
            for row in cell["per_seed"]:
                budget = row["feedback"]
                assert budget["offered_report_updates"] == budget["applied_before_decisions"]+budget["post_horizon_flush"]


def test_cli_is_deterministic_and_never_overwrites(tmp_path):
    first, second = tmp_path/"one.json", tmp_path/"two.json"
    main(["--out",str(first)])
    main(["--out",str(second)])
    assert first.read_bytes() == second.read_bytes()
    saved = first.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(["--out",str(first)])
    assert exc.value.code == 2 and first.read_bytes() == saved
