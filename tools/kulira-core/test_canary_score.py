import pytest

from kulira_core.canary_score import load_device_csv, main, score_journal
from kulira_core.twin import WAIT, missing_hash, run_twin, to_csv


def test_perfect_journal_scores_parity_one():
    rows = run_twin(80, 100, p_loss=0.0)
    dev = load_device_csv(to_csv(rows))
    rep = score_journal(dev, ticks=100)["80"]
    assert rep["parity"] == 1.0 and not rep["link_failure"]


def test_missing_rows_counted_not_failed():
    rows = run_twin(80, 100, p_loss=0.0)
    for i in (10, 20, 30):
        rows[i] = {**rows[i], "input_hash": missing_hash(rows[i]["tick"], 80),
                   "decision": WAIT}
    rep = score_journal(load_device_csv(to_csv(rows)), ticks=100)["80"]
    assert rep["parity"] == 1.0 and rep["missing_input_rows"] == 3


def test_truncated_journal_is_failure_not_score():
    rows = run_twin(80, 100, p_loss=0.0)[:90]
    rep = score_journal(load_device_csv(to_csv(rows)), ticks=100)["80"]
    assert rep["parity"] is None and rep["length_mismatch"]


def test_bad_header_rejected():
    with pytest.raises(ValueError):
        load_device_csv("a,b,c\n1,2,3\n")


def test_gate_a_cli_configuration_scores_ideal_journal():
    # Gate A manifest: 100 ticks x seeds 80, 81, 82 (300 golden rows).
    rows = []
    for seed in (80, 81, 82):
        rows.extend(run_twin(seed, 100, p_loss=0.0))
    dev = load_device_csv(to_csv(rows))
    # Default 500-tick assumption must fail closed, not score.
    assert score_journal(dev)["80"]["parity"] is None
    rep = score_journal(dev, ticks=100, expected_seeds=(80, 81, 82))
    assert all(rep[str(s)]["parity"] == 1.0 for s in (80, 81, 82))


def test_missing_expected_seed_is_failure_not_omission():
    rows = run_twin(80, 100, p_loss=0.0) + run_twin(81, 100, p_loss=0.0)
    rep = score_journal(load_device_csv(to_csv(rows)), ticks=100,
                        expected_seeds=(80, 81, 82))
    assert rep["82"]["parity"] is None and rep["82"]["missing_seed"]
    assert rep["82"]["device_rows"] == 0


def test_empty_journal_against_manifest_fails_per_seed():
    rep = score_journal([], ticks=100, expected_seeds=(80, 81, 82))
    assert set(rep) == {"80", "81", "82"}
    assert all(r["parity"] is None for r in rep.values())


def test_cli_exit_code_matches_verdict(tmp_path):
    rows = run_twin(80, 100, p_loss=0.0)
    good = tmp_path / "good.csv"
    good.write_text(to_csv(rows))
    assert main([str(good), "--ticks", "100", "--seeds", "80"]) == 0
    truncated = tmp_path / "truncated.csv"
    truncated.write_text(to_csv(rows[:90]))
    assert main([str(truncated), "--ticks", "100", "--seeds", "80"]) == 1
    # Missing expected seed must fail the process, not exit 0.
    assert main([str(good), "--ticks", "100", "--seeds", "80,82"]) == 1


def test_one_wrong_decision_fails_gate_a_acceptance(tmp_path):
    # Watch finding 2026-11-07: one flipped decision gave parity
    # 0.99 with exit 0. With a manifest, acceptance is 1.0 only.
    rows = []
    for seed in (80, 81, 82):
        rows.extend(run_twin(seed, 100, p_loss=0.0))
    rows[0] = {**rows[0], "decision": (rows[0]["decision"] + 1) % 3}
    journal = tmp_path / "onewrong.csv"
    journal.write_text(to_csv(rows))
    assert main([str(journal), "--ticks", "100",
                 "--seeds", "80,81,82"]) == 1
    # Scoring-only mode (no manifest) still publishes the number.
    assert main([str(journal), "--ticks", "100"]) == 0
