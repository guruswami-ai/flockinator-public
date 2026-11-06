#!/usr/bin/env python3
"""Step-2 gate-runner tests (cycle-07 trust stage 1).

Covers the Amendment-2.3 harness pins (stamped-candidate version assert,
per-seed G1) and the supervisor fix-review items 1-7: the committed-mislabel
rate, the frozen T2->G3 / T3+T4->G4 mapping with never-vacuous verdicts,
baseline-side eligibility and ordered-baseline cross-checks that raise,
three-valued exits, and mandatory parity evidence. Plus the Amendment-2
relay-chain dedup fixture (claimed_sender is the originator, never the
relayer; origin_turn pins the observation so duplicate relays dedup to one
P1 vote).
"""

import json
import pathlib
import tempfile
import unittest

from gate_runner import (assert_versions, evaluate, main,
                         pair_baseline, validate_evidence,
                         validate_seeds)
from score import SCORER_VERSION, score_run

HOME = [7, 11]
REPO = pathlib.Path(__file__).resolve().parents[2]
EVIDENCE = {"result": "pass", "evidence": str(REPO / "docs/results/cycle-07/provenance/parity-out.txt")}


def make_row(seed, *, forged=0, ef=0, mis=0, commits=0, discoveries=3,
             recall=1.0, eligible=True, energy=100, home=True):
    units = 4
    return {
        "seed": seed,
        "eligible": eligible,
        "contacts_total": 1 if eligible else 0,
        "units": units,
        "recall": recall,
        "discoveries": discoveries,
        "forged_vote_entries": forged,
        "forged_vote_shaped_attempts": 0,
        "reports_by_auth_status": {},
        "committed_asym_contacts": commits,
        "committed_asym_mislabelled": mis,
        "committed_asym_enemy_as_friendly": ef,
        "committed_p1_contacts": commits,
        "committed_p1_mislabelled": mis,
        "committed_p1_enemy_as_friendly": ef,
        "total_energy_spent": energy,
        "units_landed_home": units if home else 0,
        "reserve_floor_violations": 0,
    }


class VersionAssertTest(unittest.TestCase):
    def test_unstamped_candidate_rejected(self):
        with self.assertRaises(ValueError):
            assert_versions({"scorer_version": SCORER_VERSION}, None)

    def test_mismatched_candidate_rejected(self):
        with self.assertRaises(ValueError):
            assert_versions({"scorer_version": SCORER_VERSION},
                            SCORER_VERSION + 1)

    def test_matching_stamped_pair_passes(self):
        self.assertEqual(
            assert_versions({"scorer_version": SCORER_VERSION},
                            SCORER_VERSION),
            SCORER_VERSION)

    def test_legacy_unstamped_baseline_accepted_as_frozen_side(self):
        self.assertIsNone(assert_versions({"label": "dev"},
                                          SCORER_VERSION))


class PerSeedG1Test(unittest.TestCase):
    def test_all_clean_passes(self):
        rows = [make_row(s) for s in range(4)]
        for r in rows:  # engaged treatment: forgery pressure existed
            r["forged_vote_shaped_attempts"] = 3
        verdict = evaluate("T1", "P0", rows, None)
        self.assertTrue(verdict["gates"]["G1"]["pass"])
        self.assertEqual(verdict["gates"]["G1"]["value"], 0)

    def test_single_poisoned_seed_fails_despite_clean_mean(self):
        rows = [make_row(s) for s in range(4)]
        for r in rows:
            r["forged_vote_shaped_attempts"] = 3
        rows[2]["forged_vote_entries"] = 1
        mean = sum(r["forged_vote_entries"] for r in rows) / len(rows)
        self.assertAlmostEqual(mean, 0.25)  # mean looks almost clean
        verdict = evaluate("T1", "P0", rows, None)
        g1 = verdict["gates"]["G1"]
        self.assertFalse(g1["pass"])
        self.assertEqual(g1["value"], 1)  # max, never the mean
        self.assertIn("failing seeds [2]", g1["detail"])
        self.assertFalse(verdict["all_applicable_pass"])

    def test_g1_not_applicable_off_t1(self):
        rows = [make_row(s) for s in range(2)]
        verdict = evaluate("T0", "P0", rows, None)
        self.assertFalse(verdict["gates"]["G1"]["applicable"])
        self.assertIsNone(verdict["gates"]["G1"]["pass"])


class GateArithmeticTest(unittest.TestCase):
    def test_g5_sums_contacts(self):
        rows = [make_row(s, commits=20) for s in range(2)]
        verdict = evaluate("T0", "P0", rows, EVIDENCE)
        g5 = verdict["gates"]["G5"]
        self.assertEqual(g5["value"], {"pooled_contacts": 40})
        self.assertTrue(g5["pass"])

    def test_g2_rate_is_committed_mislabel_over_commits(self):
        # Frozen form: pooled mislabelled / pooled commits (cycle-06 3/40).
        rows = [make_row(0, ef=0, mis=1, commits=20, discoveries=100),
                make_row(1, ef=1, mis=2, commits=20, discoveries=100)]
        verdict = evaluate("T0", "P0", rows, EVIDENCE)
        g2 = verdict["gates"]["G2"]
        self.assertEqual(g2["value"],
                         {"pooled_ef": 1, "committed_mislabel_rate": 0.075})
        self.assertTrue(g2["pass"])

    def test_g2_rate_denominator_is_commits_not_discoveries(self):
        # Same EF/discoveries, different commit counts: the old
        # EF/discoveries form cannot tell these apart; the frozen form can.
        rows = [make_row(0, ef=1, mis=3, commits=4, discoveries=100)]
        verdict = evaluate("T0", "P0", rows, EVIDENCE)
        self.assertEqual(
            verdict["gates"]["G2"]["value"]["committed_mislabel_rate"], 0.75)
        self.assertFalse(verdict["gates"]["G2"]["pass"])

    def test_p2_columns_unmeasured_never_zero(self):
        rows = [make_row(s) for s in range(2)]
        verdict = evaluate("T0", "P2", rows, None)
        for name in ("G2", "G3", "G4", "G5", "G6"):
            self.assertIsNone(verdict["gates"][name]["pass"])
            self.assertIsNone(verdict["gates"][name]["value"])


class GateMappingTest(unittest.TestCase):
    """Frozen mapping: T0->G2/G5/G6, T1->G1, T2->G3, T3+T4->G4."""

    def test_g3_applies_to_t2_only(self):
        rows = [make_row(s) for s in range(2)]
        g3 = evaluate("T2", "P0", rows, EVIDENCE)["gates"]["G3"]
        self.assertTrue(g3["applicable"])
        for treatment in ("T0", "T1", "T3", "T4"):
            other = evaluate(treatment, "P0", rows, EVIDENCE)["gates"]["G3"]
            self.assertFalse(other["applicable"])

    def test_g4_applies_to_t3_and_t4_only(self):
        rows = [make_row(s) for s in range(2)]
        for treatment in ("T3", "T4"):
            g4 = evaluate(treatment, "P0", rows, EVIDENCE)["gates"]["G4"]
            self.assertTrue(g4["applicable"])
        for treatment in ("T0", "T1", "T2"):
            other = evaluate(treatment, "P0", rows, EVIDENCE)["gates"]["G4"]
            self.assertFalse(other["applicable"])

    def test_unknown_treatment_errors_never_succeeds(self):
        with self.assertRaises(ValueError):
            evaluate("T9", "P0", [make_row(0)], EVIDENCE)

    def test_t1r_replay_label_rejected_not_remapped(self):
        # T1R is the ungated replay emitter: explicitly never T2, so gate
        # configs carrying it must ERROR, not evaluate under any gate.
        with self.assertRaises(ValueError):
            evaluate("T1R", "P0", [make_row(0)], EVIDENCE)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_main(tmp, "T1R", "P0", {0: 1},
                         {"label": "seeded",
                          "per_seed": [{"seed": 0, "contacts_total": 1,
                                        "units": 4}]}, EVIDENCE)


def write_run(root, truth, journals):
    root = pathlib.Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "director.json").write_text(json.dumps({
        "run": "runner-fixture", "ruleset": "search-board-1",
        "source": "planner_simulation", "ground_truth": truth,
    }))
    for unit, events in journals.items():
        with open(root / f"{unit}.jsonl", "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")


def route(unit, energy=30):
    return {"unit": unit, "turn": 0, "event": "route_assigned",
            "tile": HOME, "energy": energy, "reserve": 3, "route": []}


def landed(unit, energy=25):
    return {"unit": unit, "turn": 9, "event": "landed",
            "tile": HOME, "energy": energy}


def disc(unit, turn, auth, claimed, origin, label="Enemy", l2=None):
    return {"unit": unit, "turn": turn, "event": "discovery",
            "contact": 1, "tile": [3, 3], "reported_label": label,
            "auth_status": auth, "claimed_sender": claimed,
            "l2_source": l2 or unit, "origin_turn": origin}


def tiny_run(root, n_contacts, units=("A1", "B1", "C1", "D1")):
    truth = [{"pos": [c, 0], "kind": "Enemy", "priority": "Normal",
              "outcome": "Unassessed"} for c in range(n_contacts)]
    write_run(root, truth,
              {u: [route(u), landed(u)] for u in units})


def run_main(tmp, treatment, policy, seed_contacts, baseline, parity):
    runs = pathlib.Path(tmp) / "runs"
    for seed, n in seed_contacts.items():
        tiny_run(runs / f"seed-{seed}", n)
    base = pathlib.Path(tmp) / "baseline.json"
    base.write_text(json.dumps(baseline))
    cfg = pathlib.Path(tmp) / "config.json"
    cfg.write_text(json.dumps({"treatment": treatment, "policy": policy,
                               "seeds": sorted(seed_contacts),
                               "parity": parity}))
    out = pathlib.Path(tmp) / "out"
    code = main(["--baseline", str(base), "--runs", str(runs),
                 "--config", str(cfg), "--out", str(out)])
    verdict = json.loads((out / "verdict.json").read_text())
    return code, verdict


class PairingTest(unittest.TestCase):
    def test_ordered_baseline_mismatch_raises(self):
        # Ordered list (no seed keys, no seeds list): single row claiming
        # 7 contacts pairs positionally with seed 1, whose run has 1.
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_main(tmp, "T0", "P0", {1: 1},
                         {"label": "ordered",
                          "per_seed": [{"contacts_total": 7, "units": 4}]},
                         EVIDENCE)

    def test_ordered_baseline_match_by_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, verdict = run_main(
                tmp, "T0", "P0", {1: 1},
                {"label": "ordered",
                 "per_seed": [{"contacts_total": 1, "units": 4}]},
                EVIDENCE)
            self.assertEqual(verdict["per_seed"][0]["eligible"], True)
            self.assertEqual(code, 1)  # G5 yield floor fails on 1 seed

    def test_unknown_seed_raises(self):
        baseline = {"label": "seeded",
                    "per_seed": [{"seed": 0, "contacts_total": 1,
                                  "units": 4}]}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_main(tmp, "T0", "P0", {0: 1, 999: 1}, baseline,
                         EVIDENCE)

    def test_seeded_baseline_mismatch_raises(self):
        baseline = {"label": "seeded",
                    "per_seed": [{"seed": 0, "contacts_total": 9,
                                  "units": 4}]}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_main(tmp, "T0", "P0", {0: 1}, baseline, EVIDENCE)

    def test_zero_contact_seed_ineligible_from_baseline(self):
        baseline = {"label": "seeded",
                    "per_seed": [{"seed": 3, "contacts_total": 0,
                                  "units": 16}]}
        with tempfile.TemporaryDirectory() as tmp:
            runs = pathlib.Path(tmp) / "runs"
            tiny_run(runs / "seed-3", 0, units=tuple(
                f"{r}{c}" for r in "ABCD" for c in range(1, 5)))
            base = pathlib.Path(tmp) / "baseline.json"
            base.write_text(json.dumps(baseline))
            cfg = pathlib.Path(tmp) / "config.json"
            cfg.write_text(json.dumps({"treatment": "T0", "policy": "P0",
                                       "seeds": [3], "parity": EVIDENCE}))
            out = pathlib.Path(tmp) / "out"
            main(["--baseline", str(base), "--runs", str(runs),
                  "--config", str(cfg), "--out", str(out)])
            verdict = json.loads((out / "verdict.json").read_text())
            self.assertFalse(verdict["per_seed"][0]["eligible"])


class ParityEvidenceTest(unittest.TestCase):
    def _main(self, tmp, parity):
        return run_main(tmp, "T0", "P0", {0: 1},
                        {"label": "seeded",
                         "per_seed": [{"seed": 0, "contacts_total": 1,
                                       "units": 4}]}, parity)

    def test_missing_parity_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                self._main(tmp, None)

    def test_empty_evidence_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                self._main(tmp, {"result": "pass", "evidence": "  "})

    def test_evidence_recorded_in_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, verdict = self._main(tmp, EVIDENCE)
            self.assertEqual(verdict["parity_evidence"], EVIDENCE["evidence"])


class ExitCodeTest(unittest.TestCase):
    def test_p2_is_unmeasured_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, verdict = run_main(
                tmp, "T0", "P2", {0: 1},
                {"label": "seeded",
                 "per_seed": [{"seed": 0, "contacts_total": 1,
                               "units": 4}]}, EVIDENCE)
            self.assertIsNone(verdict["all_applicable_pass"])
            self.assertEqual(code, 2)

    def test_t2_end_to_end_gate_is_real_not_vacuous(self):
        # One contact, no sightings: recall 0 -> G3 must FAIL (exit 1),
        # never report vacuous success.
        with tempfile.TemporaryDirectory() as tmp:
            code, verdict = run_main(
                tmp, "T2", "P0", {0: 1},
                {"label": "seeded",
                 "per_seed": [{"seed": 0, "contacts_total": 1,
                               "units": 4}]}, EVIDENCE)
            self.assertTrue(verdict["gates"]["G3"]["applicable"])
            self.assertFalse(verdict["gates"]["G3"]["pass"])
            self.assertEqual(code, 1)


TRUTH = [{"pos": [3, 3], "kind": "Enemy", "priority": "High",
          "outcome": "Unassessed"}]


class RelayDedupTest(unittest.TestCase):
    """Amendment-2 pin: claimed_sender is the originator (never the relayer)
    and origin_turn is the original sighting turn; the P1 dedup key
    (contact, claimed_sender, origin_turn) collapses relay chains to one."""

    def test_duplicate_relays_dedup_to_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp) / "seed-0"
            write_run(d, TRUTH, {
                "A1": [route("A1"), disc("A1", 5, "direct_verified",
                                          "A1", 5), landed("A1")],
                # Relayers B1/C1 repeat A1's observation verbatim in the
                # pin fields; only l2_source names the relayer.
                "B1": [route("B1"),
                       disc("B1", 6, "hearsay_relayed", "A1", 5, l2="B1"),
                       landed("B1")],
                "C1": [route("C1"),
                       disc("C1", 7, "hearsay_relayed", "A1", 5, l2="C1"),
                       landed("C1")],
            })
            s = score_run(d)
        self.assertEqual(s["discoveries"], 1)  # relays never vote direct
        self.assertEqual(s["reports_by_auth_status"]["hearsay_relayed"], 2)
        self.assertEqual(s["reports_by_auth_status"]["direct_verified"], 1)
        # Without dedup the P1 fusion would see 3 Enemy sightings and
        # commit; with the pin it sees one and stays uncommitted.
        self.assertEqual(s["committed_p1_contacts"], 0)
        self.assertEqual(s["committed_asym_contacts"], 0)

    def test_distinct_observations_still_fuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp) / "seed-0"
            write_run(d, TRUTH, {
                "A1": [route("A1"), disc("A1", 5, "direct_verified",
                                          "A1", 5), landed("A1")],
                # Two genuinely distinct relays (different origin turns)
                # are two votes, not one observation.
                "B1": [route("B1"),
                       disc("B1", 6, "hearsay_relayed", "B1", 6),
                       landed("B1")],
                "C1": [route("C1"),
                       disc("C1", 7, "hearsay_relayed", "C1", 7),
                       landed("C1")],
            })
            s = score_run(d)
        self.assertEqual(s["committed_p1_contacts"], 1)
        self.assertEqual(s["committed_p1_enemy_as_friendly"], 0)


if __name__ == "__main__":
    unittest.main()


class SeedValidationTest(unittest.TestCase):
    def test_empty_seeds_rejected(self):
        with self.assertRaises(ValueError):
            validate_seeds([])

    def test_duplicate_seeds_rejected(self):
        with self.assertRaises(ValueError):
            validate_seeds([0, 0])

    def test_bool_and_float_seeds_rejected(self):
        for bad in ([True], [0.5], ["0"]):
            with self.assertRaises(ValueError):
                validate_seeds(bad)

    def test_evaluate_empty_rows_refuses_vacuous_success(self):
        with self.assertRaises(ValueError):
            evaluate("T0", "P0", [], EVIDENCE)

    def test_g6_missing_energy_unmeasured_never_passes(self):
        rows = [make_row(s, energy=None) for s in range(4)]
        verdict = evaluate("T0", "P0", rows, EVIDENCE)
        self.assertIsNone(verdict["gates"]["G6"]["pass"])

    def test_g6_partially_missing_energy_unmeasured(self):
        rows = [make_row(0, energy=100), make_row(1, energy=None),
                make_row(2, energy=100), make_row(3, energy=100)]
        verdict = evaluate("T0", "P0", rows, EVIDENCE)
        self.assertIsNone(verdict["gates"]["G6"]["pass"])

    def test_stale_verdict_cleared_when_run_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "out"
            out.mkdir()
            (out / "verdict.json").write_text('{"all_applicable_pass": true}')
            runs = pathlib.Path(tmp) / "runs"
            tiny_run(runs / "seed-0", 1)
            base = pathlib.Path(tmp) / "baseline.json"
            base.write_text(json.dumps({"label": "x", "per_seed": [
                {"seed": 0, "contacts_total": 1, "units": 4}]}))
            cfg = pathlib.Path(tmp) / "config.json"
            cfg.write_text(json.dumps({"treatment": "T9", "policy": "P0",
                                       "seeds": [0], "parity": EVIDENCE}))
            with self.assertRaises(ValueError):
                main(["--baseline", str(base), "--runs", str(runs),
                      "--config", str(cfg), "--out", str(out)])
            self.assertFalse((out / "verdict.json").exists())


class WfMeasurementFixesTest(unittest.TestCase):
    """2026-11-07 reassessment counterexamples, as regression tests."""

    def test_zero_pressure_t1_is_unmeasured_not_pass(self):
        rows = [make_row(0, commits=0, discoveries=0, energy=None)]
        verdict = evaluate("T1", "P0", rows, EVIDENCE)
        self.assertIsNone(verdict["gates"]["G1"]["pass"])
        self.assertIsNone(verdict["all_applicable_pass"])

    def test_zero_commit_t3_is_unmeasured_not_pass(self):
        rows = [make_row(0, commits=0, discoveries=0, energy=None)]
        verdict = evaluate("T3", "P0", rows, EVIDENCE)
        self.assertIsNone(verdict["gates"]["G4"]["pass"])

    def test_unrounded_rate_comparison(self):
        row = make_row(0, commits=1999, mis=150)
        verdict = evaluate("T0", "P0", [row], EVIDENCE)
        self.assertFalse(verdict["gates"]["G2"]["pass"])  # 0.07503 > 0.0750

    def test_duplicate_baseline_rows_rejected(self):
        base = {"per_seed": [{"seed": 0, "contacts_total": 1},
                             {"seed": 0, "contacts_total": 30}]}
        with self.assertRaises(ValueError):
            pair_baseline(base, [0])

    def test_bool_baseline_seed_rejected(self):
        base = {"per_seed": [{"seed": False, "contacts_total": 30}]}
        with self.assertRaises(ValueError):
            pair_baseline(base, [0])

    def test_validate_evidence_rejects_exact_duplicates(self):
        import json as _json, pathlib, tempfile
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            ev = {"unit": "A1", "seq": 1, "turn": 1, "event": "discovery",
                  "tile": [5, 5], "contact": 1, "reported_label": "Friendly"}
            (d / "events.jsonl").write_text(_json.dumps(ev) + "\n" + _json.dumps(ev) + "\n")
            with self.assertRaises(ValueError):
                validate_evidence(d)

    def test_validate_evidence_rejects_missing_reserve_and_nan(self):
        import json as _json, pathlib, tempfile
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            ev = {"unit": "A1", "event": "route_assigned", "turn": 0,
                  "tile": [7, 11], "energy": 30, "route": []}
            (d / "events.jsonl").write_text(_json.dumps(ev) + "\n")
            with self.assertRaises(ValueError):
                validate_evidence(d)
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            ev = {"unit": "A1", "event": "route_assigned", "turn": 0,
                  "tile": [7, 11], "energy": float("nan"), "reserve": 3, "route": []}
            (d / "events.jsonl").write_text(_json.dumps(ev) + "\n")
            with self.assertRaises(ValueError):
                validate_evidence(d)
