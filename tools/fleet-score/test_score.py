"""Scorer regression: must reproduce the cycle-00 coordinator headlines.

Ground truth for expectations is the bundled cycle-00 live capture
(docs/results/sample-runs/cycle-00-live-capture, run 1793752408891):
8/20 found, 6/41 mislabelled (2 Enemy->Friendly), 1 check, (7,10) x14,
16/16 landed.
"""
import json
import pathlib
import tempfile
import unittest

from score import score_run

REPO = pathlib.Path(__file__).resolve().parents[2]
RUN = REPO / "docs/results/sample-runs/cycle-00-live-capture"


class Cycle00Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = score_run(RUN)

    def test_recall(self):
        self.assertEqual(self.s["contacts_total"], 20)
        self.assertEqual(self.s["contacts_found"], 8)

    def test_mislabels(self):
        self.assertEqual(self.s["discoveries"], 41)
        self.assertEqual(self.s["mislabelled"], 6)
        self.assertEqual(self.s["mislabelled_enemy_as_friendly"], 2)

    def test_duplication(self):
        self.assertEqual(self.s["max_units_per_contact"], 14)
        self.assertEqual(self.s["most_duplicated_tile"], [7, 10])

    def test_cooperation(self):
        self.assertEqual(self.s["messages_sent"], 1)
        self.assertEqual(self.s["checks_assigned"], 1)
        self.assertEqual(self.s["checks_completed_with_discovery"], 0)
        # A1 behaviourally completed the check by scanning [5,7] on
        # turn 4; it was a negative check (signals=0, no discovery).
        self.assertEqual(self.s["checks_completed_scan"], 1)
        self.assertEqual(self.s["checks_positive"], 0)
        self.assertEqual(self.s["checks_negative"], 1)
        self.assertEqual(self.s["high_checked_completed"], 1)
        self.assertEqual(self.s["high_checks_negative"], 1)

    def test_energy_and_landings(self):
        self.assertEqual(self.s["units_landed"], 16)
        self.assertEqual(self.s["units"], 16)
        self.assertGreaterEqual(self.s["min_landed_energy"], 4)

    def test_rates_and_priorities(self):
        self.assertEqual(self.s["recall_by_priority"]["High"], 0.5)
        self.assertEqual(self.s["recall_by_priority"]["Normal"], 0.3571)
        self.assertEqual(self.s["mislabel_rate"], 0.1463)
        self.assertEqual(self.s["duplicate_discovery_rate"], 0.8049)
        self.assertEqual(self.s["reserve_floor_violations"], 0)
        self.assertEqual(self.s["scorer_version"], 2)
        self.assertEqual(self.s["committed3_contacts"], 4)
        self.assertEqual(self.s["committed3_mislabelled"], 0)
        self.assertEqual(self.s["committed3_enemy_as_friendly"], 0)

    def test_ruleset_and_source(self):
        self.assertEqual(self.s["ruleset"], "search-board-1")
        self.assertEqual(self.s["source"], "planner_simulation")


class SyntheticRunTest(unittest.TestCase):
    def test_zero_contacts_and_abandoned_waypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = pathlib.Path(tmp)
            (run_dir / "director.json").write_text(json.dumps({
                "run": "synthetic", "ruleset": "test", "source": "test",
                "ground_truth": [],
            }))
            events = [
                {"unit": "A1", "turn": 0, "event": "route_assigned",
                 "tile": [7, 11], "energy": 10, "reserve": 3,
                 "route": [[6, 11], [5, 11]]},
                {"unit": "A1", "turn": 1, "event": "scan",
                 "tile": [6, 11], "energy": 2, "footprint": [[6, 11]],
                 "signals": 0},
                {"unit": "A1", "turn": 2, "event": "landed",
                 "tile": [7, 11], "energy": 1},
            ]
            (run_dir / "A1.jsonl").write_text(
                "\n".join(json.dumps(e) for e in events))
            scores = score_run(run_dir)

        self.assertIsNone(scores["recall"])
        self.assertEqual(scores["abandoned_waypoints"], 1)
        self.assertEqual(scores["units_with_abandoned_waypoints"], 1)
        self.assertEqual(scores["reserve_floor_violations"], 1)


class AsymmetricCommitTest(unittest.TestCase):
    """Cycle-06 rule: Friendly needs unanimous >=3 or >=5 with <=1
    dissent; Enemy needs >=3 strict majority; else uncommitted."""

    def _run(self, truth_kinds, sightings):
        # sightings: {contact_idx0: [reported labels]}
        tmp = tempfile.TemporaryDirectory()
        run_dir = pathlib.Path(tmp.name)
        truth = [{"pos": [i, 0], "kind": k, "priority": "Normal"}
                 for i, k in enumerate(truth_kinds)]
        (run_dir / "director.json").write_text(json.dumps({
            "run": "asym", "ruleset": "test", "source": "test",
            "ground_truth": truth}))
        events = []
        turn = 0
        for idx, labels in sightings.items():
            for lab in labels:
                turn += 1
                events.append({
                    "unit": "A1", "turn": turn, "event": "discovery",
                    "contact": idx + 1, "tile": [idx, 0],
                    "reported_label": lab})
        (run_dir / "A1.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events))
        scores = score_run(run_dir)
        tmp.cleanup()
        return scores

    def test_asymmetric_commit_rules(self):
        s = self._run(
            ["Enemy", "Friendly", "Friendly", "Enemy", "Friendly"],
            {0: ["Enemy", "Enemy", "Friendly"],        # Enemy majority3 -> commit Enemy (correct)
             1: ["Friendly", "Friendly", "Enemy"],     # Friendly 2-1 majority -> NO commit
             2: ["Friendly", "Friendly", "Friendly"],  # unanimous -> commit Friendly
             3: ["Friendly", "Friendly", "Friendly"],  # unanimous wrong -> dangerous commit counts
             4: ["Friendly"] * 4 + ["Enemy"]})         # 5 sightings, 1 dissent -> commit Friendly
        self.assertEqual(s["committed_asym_contacts"], 4)
        self.assertEqual(s["committed_asym_friendly_commits"], 3)
        self.assertEqual(s["committed_asym_mislabelled"], 1)
        self.assertEqual(s["committed_asym_enemy_as_friendly"], 1)
        # committed3 on same data commits the 2-1 Friendly too (5 contacts)
        self.assertEqual(s["committed3_contacts"], 5)


if __name__ == "__main__":
    unittest.main()
