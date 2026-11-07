"""Scorer regression: must reproduce the cycle-00 coordinator headlines.

Ground truth for expectations is the published cycle-00 capture under docs/results/sample-runs/ (private lab-book original:
2026-11-04-cycle-00/coordinator-summary.md (run 1793752408891):
8/20 found, 6/41 mislabelled (2 Enemy->Friendly), 1 check, (7,10) x14,
16/16 landed.
"""
import json
import pathlib
import tempfile
import unittest

from score import score_run

REPO = pathlib.Path(__file__).resolve().parents[2]
RUN = (REPO / "docs/results/sample-runs/cycle-00-planner-capture")


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
        self.assertEqual(self.s["scorer_version"], 4)
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


class Cycle00TrustKeysTest(unittest.TestCase):
    """Scorer v3 additions on the frozen legacy run: all discoveries are
    legacy (no auth fields) so the census is all-direct and every
    trust metric takes its honest-baseline value."""

    @classmethod
    def setUpClass(cls):
        cls.s = score_run(RUN)

    def test_auth_census_all_direct(self):
        self.assertEqual(self.s["reports_by_auth_status"], {
            "direct_verified": 41, "hearsay_relayed": 0,
            "unverified": 0, "forged_rejected": 0})

    def test_no_forgery_no_unverified_commits(self):
        # G1 quantity is zero on the honest fixture; pressure is zero too.
        self.assertEqual(self.s["forged_vote_entries"], 0)
        self.assertEqual(self.s["forged_vote_shaped_attempts"], 0)
        self.assertEqual(self.s["committed_inclusive_delta"], 0)

    def test_commits_per_energy_unit(self):
        # 2 asym commits over 170 total energy; pinned, not recomputed.
        self.assertEqual(self.s["total_energy_spent"], 170)
        self.assertEqual(self.s["committed_asym_contacts"], 2)
        self.assertEqual(self.s["commits_per_energy_unit"], 0.0118)

    def test_stage2_stubs_null(self):
        # Attribution needs claimed_sender/l2_source + treated-unit
        # designation; detection latency needs a policy-visible signal
        # event. Neither exists in journals yet: null, never fabricated.
        self.assertIsNone(self.s["attribution_accuracy"])
        self.assertIsNone(self.s["detection_latency_turns"])


class AuthSegregationTest(unittest.TestCase):
    """Scorer v3 segregation: forged/unverifiable discoveries never vote
    and never reach contact_of (no crash on non-truth tiles)."""

    TRUTH = [
        {"pos": [0, 0], "kind": "Enemy", "priority": "Normal"},
        {"pos": [1, 0], "kind": "Friendly", "priority": "Normal"},
    ]

    def _score(self, events):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = pathlib.Path(tmp)
            (run_dir / "director.json").write_text(json.dumps({
                "run": "auth", "ruleset": "test", "source": "test",
                "ground_truth": self.TRUTH}))
            per_unit = {}
            for ev in events:
                per_unit.setdefault(ev["unit"], []).append(ev)
            for unit, evs in per_unit.items():
                (run_dir / (unit + ".jsonl")).write_text(
                    "\n".join(json.dumps(e) for e in evs))
            return score_run(run_dir)

    def _disc(self, unit, turn, contact, tile, label, auth=None):
        ev = {"unit": unit, "turn": turn, "event": "discovery",
              "contact": contact, "tile": tile, "reported_label": label}
        if auth is not None:
            ev["auth_status"] = auth
        return ev

    def _energy(self):
        return [
            {"unit": "A1", "turn": 0, "event": "route_assigned",
             "tile": [7, 11], "energy": 30, "reserve": 3, "route": []},
            {"unit": "A1", "turn": 9, "event": "landed",
             "tile": [7, 11], "energy": 25},
        ]

    def _honest_commit(self):
        # Contact 1 (Enemy): 3 direct Enemy -> asym Enemy commit.
        evs = [self._disc("A1", t, 1, [0, 0], "Enemy") for t in (1, 2, 3)]
        evs.append(self._disc("B1", 4, 2, [1, 0], "Friendly"))
        return evs + self._energy()

    def test_forged_malformed_excluded_no_crash(self):
        evs = self._honest_commit()
        evs.append(self._disc("X9", 5, 99, [9, 9], "Friendly",
                              "forged_rejected"))   # invalid contact
        evs.append(self._disc("X9", 6, 1, [5, 5], "Friendly",
                              "forged_rejected"))   # valid contact, wrong tile
        evs.append(self._disc("X9", 7, 1, [0, 0], "Enemy",
                              "bogus_status"))       # unrecognized status
        s = self._score(evs)
        self.assertEqual(s["discoveries"], 4)
        self.assertEqual(s["contacts_found"], 2)
        self.assertEqual(s["committed_asym_contacts"], 1)
        self.assertEqual(s["reports_by_auth_status"], {
            "direct_verified": 4, "hearsay_relayed": 0,
            "unverified": 0, "forged_rejected": 2,
            "bogus_status": 1})
        self.assertEqual(s["forged_vote_entries"], 0)
        self.assertEqual(s["forged_vote_shaped_attempts"], 0)
        self.assertEqual(s["committed_inclusive_delta"], 0)

    def test_forged_shaped_attempts_counts_naive_slip(self):
        # Well-formed forgery (valid contact, matching tile): a naive
        # scorer would vote it and commit contact 1 on 2E+1F; v4 excludes it.
        evs = [self._disc("A1", 1, 1, [0, 0], "Enemy"),
               self._disc("A1", 2, 1, [0, 0], "Enemy"),
               self._disc("X9", 3, 1, [0, 0], "Friendly",
                          "forged_rejected")]
        s = self._score(evs)
        self.assertEqual(s["forged_vote_entries"], 0)
        self.assertEqual(s["forged_vote_shaped_attempts"], 1)
        self.assertEqual(s["discoveries"], 2)
        self.assertEqual(s["committed_asym_contacts"], 0)
        control = self._score(evs[:2])
        self.assertEqual(control["forged_vote_shaped_attempts"], 0)
        self.assertEqual(control["discoveries"], s["discoveries"])
        self.assertEqual(control["committed_asym_contacts"],
                         s["committed_asym_contacts"])

    def test_inclusive_delta_counterfactual(self):
        # 1 direct + 2 unverified Enemy: direct-only cannot commit (total 1)
        # but the inclusive fusion reaches 3-unanimous -> cfu 1, asym 0.
        evs = [self._disc("A1", 1, 1, [0, 0], "Enemy", "direct_verified"),
               self._disc("B1", 2, 1, [0, 0], "Enemy", "unverified"),
               self._disc("C1", 3, 1, [0, 0], "Enemy", "hearsay_relayed")]
        s = self._score(evs)
        self.assertEqual(s["discoveries"], 1)
        self.assertEqual(s["committed_asym_contacts"], 0)
        self.assertEqual(s["committed_inclusive_delta"], 1)
        self.assertEqual(s["reports_by_auth_status"], {
            "direct_verified": 1, "hearsay_relayed": 1,
            "unverified": 1, "forged_rejected": 0})

    def test_attacker_only_unit_excluded(self):
        # Finding 2: X9 appears only in non-voting discoveries, so it is
        # not a fleet unit and has no per-unit entry. Pre-fix this added
        # "X9" to units and "X9: 0" to per_unit_discoveries.
        evs = self._honest_commit()
        evs.append(self._disc("X9", 5, 1, [0, 0], "Friendly",
                              "forged_rejected"))
        s = self._score(evs)
        self.assertEqual(s["units"], 2)
        self.assertEqual(s["per_unit_discoveries"], {"A1": 3, "B1": 1})

    def test_legacy_default_and_commits_per_energy_unit(self):
        s = self._score(self._honest_commit())
        self.assertEqual(s["reports_by_auth_status"], {
            "direct_verified": 4, "hearsay_relayed": 0,
            "unverified": 0, "forged_rejected": 0})
        self.assertEqual(s["forged_vote_entries"], 0)
        self.assertEqual(s["forged_vote_shaped_attempts"], 0)
        self.assertEqual(s["committed_inclusive_delta"], 0)
        # 1 asym commit over 5 spent energy; attribution/detection null.
        self.assertEqual(s["commits_per_energy_unit"], 0.2)
        self.assertIsNone(s["attribution_accuracy"])
        self.assertIsNone(s["detection_latency_turns"])


class AuthRobustnessTest(unittest.TestCase):
    """Amendment 1 finding 4: non-string auth fails closed, bool contact
    rejected. Same TRUTH/helpers shape as AuthSegregationTest."""

    TRUTH = AuthSegregationTest.TRUTH

    def _score(self, events):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = pathlib.Path(tmp)
            (run_dir / "director.json").write_text(json.dumps({
                "run": "auth", "ruleset": "test", "source": "test",
                "ground_truth": self.TRUTH}))
            per_unit = {}
            for ev in events:
                per_unit.setdefault(ev["unit"], []).append(ev)
            for unit, evs in per_unit.items():
                (run_dir / (unit + ".jsonl")).write_text(
                    "\n".join(json.dumps(e) for e in evs))
            return score_run(run_dir)

    def test_non_string_auth_fails_closed_no_crash(self):
        evs = [{"unit": "A1", "turn": 1, "event": "discovery",
                "contact": 1, "tile": [0, 0], "reported_label": "Enemy"}]
        for i, bad in enumerate([None, 123, True, ["direct_verified"]]):
            ev = {"unit": "X9", "turn": 10 + i, "event": "discovery",
                  "contact": 1, "tile": [0, 0], "reported_label": "Enemy",
                  "auth_status": bad}
            evs.append(ev)
        s = self._score(evs)
        self.assertEqual(s["discoveries"], 1)
        self.assertEqual(s["contacts_found"], 1)
        self.assertEqual(s["units"], 1)
        self.assertEqual(sorted(s["per_unit_discoveries"]), ["A1"])
        self.assertEqual(s["reports_by_auth_status"], {
            "direct_verified": 1, "hearsay_relayed": 0,
            "unverified": 0, "forged_rejected": 0,
            "invalid_auth_status": 4})
        self.assertEqual(s["forged_vote_entries"], 0)
        self.assertEqual(s["forged_vote_shaped_attempts"], 0)

    def test_bool_contact_rejected_strict(self):
        ev = {"unit": "A1", "turn": 1, "event": "discovery",
              "contact": True, "tile": [0, 0],
              "reported_label": "Enemy", "auth_status": "direct_verified"}
        with self.assertRaises(ValueError):
            self._score([ev])

    def test_out_of_range_and_noninteger_direct_contacts_rejected(self):
        for contact in (0, -1, 3, 1.0, "1", None):
            with self.subTest(contact=contact), self.assertRaises(ValueError):
                self._score([{"unit": "A1", "turn": 1, "event": "discovery",
                             "contact": contact, "tile": [0, 0],
                             "reported_label": "Enemy"}])

    def test_direct_tile_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "ground truth pos"):
            self._score([{"unit": "A1", "turn": 1, "event": "discovery",
                         "contact": 1, "tile": [9, 9],
                         "reported_label": "Enemy"}])

    def test_empty_run_rejected(self):
        with self.assertRaisesRegex(ValueError, "no journal events"):
            self._score([])

    def test_malformed_nonvoting_tile_fails_closed(self):
        for status in ("forged_rejected", "hearsay_relayed", "unverified"):
            for tile in (None, 1, True, 1.5, "bad", {}, {"x": 0, "y": 0}):
                with self.subTest(status=status, tile=tile):
                    result = self._score([{
                        "unit": "X9", "turn": 1, "event": "discovery",
                        "contact": 1, "tile": tile, "reported_label": "Enemy",
                        "auth_status": status}])
                    self.assertEqual(result["discoveries"], 0)
                    self.assertEqual(result["forged_vote_shaped_attempts"], 0)
                    self.assertEqual(result["committed_p1_contacts"], 0)
                    self.assertEqual(result["committed_inclusive_delta"], 0)

    def test_bool_contact_lenient_none(self):
        ev = {"unit": "X9", "turn": 1, "event": "discovery",
              "contact": True, "tile": [0, 0],
              "reported_label": "Enemy", "auth_status": "forged_rejected"}
        s = self._score([ev])
        self.assertEqual(s["discoveries"], 0)
        self.assertEqual(s["forged_vote_shaped_attempts"], 0)

    def test_unhashable_sender_skipped_no_crash(self):
        evs = [
            {"unit": "A1", "turn": 1, "event": "discovery",
             "contact": 1, "tile": [0, 0], "reported_label": "Enemy",
             "auth_status": "direct_verified"},
            {"unit": "B1", "turn": 2, "event": "discovery",
             "contact": 1, "tile": [0, 0], "reported_label": "Enemy",
             "auth_status": "hearsay_relayed",
             "claimed_sender": ["not", "a", "string"], "origin_turn": 1},
        ]
        s = self._score(evs)
        self.assertEqual(s["discoveries"], 1)
        self.assertEqual(s["committed_p1_contacts"], 0)


class TrustFilterTest(unittest.TestCase):
    """Amendment 1.3: one leak-class fixture per finding-3 class. Each
    forged non-discovery event must leave every non-pressure field
    identical to the honest base."""

    TRUTH = [{"pos": [0, 0], "kind": "Enemy", "priority": "Normal"}]
    PRESSURE_KEYS = {"reports_by_auth_status", "forged_vote_entries",
                     "forged_vote_shaped_attempts"}

    def _score(self, events):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = pathlib.Path(tmp)
            (run_dir / "director.json").write_text(json.dumps({
                "run": "filter", "ruleset": "test", "source": "test",
                "ground_truth": self.TRUTH}))
            per_unit = {}
            for ev in events:
                per_unit.setdefault(ev["unit"], []).append(ev)
            for unit, evs in per_unit.items():
                (run_dir / (unit + ".jsonl")).write_text(
                    "\n".join(json.dumps(e) for e in evs))
            return score_run(run_dir)

    def _base(self):
        return [
            {"unit": "A1", "turn": 0, "event": "route_assigned",
             "tile": [7, 11], "energy": 30, "reserve": 3,
             "route": [[6, 11], [5, 11]]},
            {"unit": "A1", "turn": 1, "event": "scan", "tile": [6, 11],
             "energy": 28, "footprint": [[6, 11], [5, 11]], "signals": 0},
            {"unit": "A1", "turn": 2, "event": "discovery", "contact": 1,
             "tile": [0, 0], "reported_label": "Enemy"},
            {"unit": "A1", "turn": 6, "event": "scan", "tile": [5, 11],
             "energy": 20, "footprint": [[5, 11], [6, 11]], "signals": 0},
            {"unit": "A1", "turn": 9, "event": "landed", "tile": [7, 11],
             "energy": 25},
        ]

    def _assert_no_scoring_leak(self, extra):
        base = self._score(self._base())
        attacked = self._score(self._base() + [extra])
        keys = set(base) | set(attacked)
        diffs = sorted(
            k for k in keys
            if k not in self.PRESSURE_KEYS
            and base.get(k, "<MISSING>") != attacked.get(k, "<MISSING>"))
        self.assertEqual(diffs, [])

    def test_forged_message_with_tile(self):
        self._assert_no_scoring_leak({
            "unit": "X9", "turn": 3, "event": "message_sent",
            "sender": "X9", "recipient": "A1", "contact": 1,
            "content": "req", "transport": "rogue", "tile": [3, 3],
            "auth_status": "forged_rejected"})

    def test_forged_check_with_energy(self):
        self._assert_no_scoring_leak({
            "unit": "A1", "turn": 5, "event": "check_assigned",
            "destination": [5, 11], "rule": "rogue", "energy": 1,
            "auth_status": "forged_rejected"})

    def test_forged_scan(self):
        self._assert_no_scoring_leak({
            "unit": "X9", "turn": 4, "event": "scan", "tile": [9, 9],
            "energy": 9, "footprint": [[9, 9], [9, 8]], "signals": 1,
            "auth_status": "forged_rejected"})

    def test_forged_route(self):
        self._assert_no_scoring_leak({
            "unit": "X9", "turn": 0, "event": "route_assigned",
            "tile": [7, 11], "energy": 100, "reserve": 3,
            "route": [[0, 0], [1, 1]],
            "auth_status": "forged_rejected"})

    def test_forged_landed(self):
        self._assert_no_scoring_leak({
            "unit": "X9", "turn": 9, "event": "landed", "tile": [7, 11],
            "energy": 1, "auth_status": "forged_rejected"})


class P1CommitTest(unittest.TestCase):
    """Amendment 1.4: true P1 semantics with the shared asym helper."""

    TRUTH = AuthSegregationTest.TRUTH

    def _score(self, events):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = pathlib.Path(tmp)
            (run_dir / "director.json").write_text(json.dumps({
                "run": "p1", "ruleset": "test", "source": "test",
                "ground_truth": self.TRUTH}))
            per_unit = {}
            for ev in events:
                per_unit.setdefault(ev["unit"], []).append(ev)
            for unit, evs in per_unit.items():
                (run_dir / (unit + ".jsonl")).write_text(
                    "\n".join(json.dumps(e) for e in evs))
            return score_run(run_dir)

    def _hearsay(self, unit, turn, contact, tile, label, sender, origin):
        return {"unit": unit, "turn": turn, "event": "discovery",
                "contact": contact, "tile": tile,
                "reported_label": label, "auth_status": "hearsay_relayed",
                "claimed_sender": sender, "origin_turn": origin}

    def test_hearsay_only_never_commits_p1(self):
        # 3 unanimous hearsay, no direct support: inclusive analysis
        # commits (delta 1) but P1 opens nothing — the G1-superseding
        # assertion holds by construction.
        evs = [self._hearsay("B1", t, 1, [0, 0], "Friendly", "B1", t)
               for t in (1, 2, 3)]
        s = self._score(evs)
        self.assertEqual(s["discoveries"], 0)
        self.assertEqual(s["committed_asym_contacts"], 0)
        self.assertEqual(s["committed_p1_contacts"], 0)
        self.assertEqual(s["committed_inclusive_delta"], 1)

    def test_p1_votes_with_direct_support(self):
        evs = [{"unit": "A1", "turn": 1, "event": "discovery",
                "contact": 1, "tile": [0, 0], "reported_label": "Enemy",
                "auth_status": "direct_verified"},
               self._hearsay("B1", 2, 1, [0, 0], "Enemy", "B1", 2),
               self._hearsay("C1", 3, 1, [0, 0], "Enemy", "C1", 3)]
        s = self._score(evs)
        self.assertEqual(s["committed_asym_contacts"], 0)
        self.assertEqual(s["committed_p1_contacts"], 1)
        self.assertEqual(s["committed_p1_mislabelled"], 0)
        self.assertEqual(s["committed_inclusive_delta"], 1)

    def test_p1_dedup_same_observation(self):
        # Same (sender, origin) relayed twice counts once: 1 direct + 1
        # effective hearsay vote, no commit.
        evs = [{"unit": "A1", "turn": 1, "event": "discovery",
                "contact": 1, "tile": [0, 0], "reported_label": "Enemy",
                "auth_status": "direct_verified"},
               self._hearsay("B1", 2, 1, [0, 0], "Enemy", "B1", 5),
               self._hearsay("C1", 3, 1, [0, 0], "Enemy", "B1", 5)]
        s = self._score(evs)
        self.assertEqual(s["committed_p1_contacts"], 0)
        # Inclusive fusion has no dedup: 3 unanimous, delta still fires.
        self.assertEqual(s["committed_inclusive_delta"], 1)

    def test_p1_fallback_sender_origin(self):
        # Hearsay without step-2 fields falls back to (unit, turn);
        # distinct turns are distinct observations.
        evs = [{"unit": "A1", "turn": 1, "event": "discovery",
                "contact": 1, "tile": [0, 0], "reported_label": "Enemy",
                "auth_status": "direct_verified"}]
        for unit, turn in (("B1", 2), ("C1", 3)):
            evs.append({"unit": unit, "turn": turn, "event": "discovery",
                        "contact": 1, "tile": [0, 0],
                        "reported_label": "Enemy",
                        "auth_status": "unverified"})
        s = self._score(evs)
        self.assertEqual(s["committed_p1_contacts"], 1)

    def test_p1_relay_of_direct_observation_deduped(self):
        # A relay of the exact voted observation adds nothing.
        evs = [{"unit": "A1", "turn": 1, "event": "discovery",
                "contact": 1, "tile": [0, 0], "reported_label": "Enemy",
                "auth_status": "direct_verified"},
               self._hearsay("B1", 2, 1, [0, 0], "Enemy", "A1", 1)]
        s = self._score(evs)
        self.assertEqual(s["committed_p1_contacts"], 0)
        self.assertEqual(s["committed_inclusive_delta"], 0)

    def test_p1_mixed_contacts_g1_superseding(self):
        # Contact 1: 3 direct Enemy + 2 hearsay Friendly -> P1 still
        # commits Enemy. Contact 2: hearsay-only Friendly x3 -> P1 opens
        # nothing without direct sighting.
        evs = [{"unit": "A1", "turn": t, "event": "discovery",
                "contact": 1, "tile": [0, 0], "reported_label": "Enemy",
                "auth_status": "direct_verified"} for t in (1, 2, 3)]
        evs += [self._hearsay("B1", 4, 1, [0, 0], "Friendly", "B1", 4),
                self._hearsay("C1", 5, 1, [0, 0], "Friendly", "C1", 5)]
        evs += [self._hearsay("B1", 6, 2, [1, 0], "Friendly", "B1", 6),
                self._hearsay("C1", 7, 2, [1, 0], "Friendly", "C1", 7),
                self._hearsay("D1", 8, 2, [1, 0], "Friendly", "D1", 8)]
        s = self._score(evs)
        self.assertEqual(s["committed_p1_contacts"], 1)
        self.assertEqual(s["committed_p1_enemy_as_friendly"], 0)
        self.assertEqual(s["committed_inclusive_delta"], 1)


class CompareVersionGateTest(unittest.TestCase):
    """Amendment 1.5: compare() refuses cross-version pairings."""

    def _payload(self, version):
        rows = [{"seed": i, "contacts_total": 10, "units": 16,
                 "recall": 0.2, "mislabelled": 1, "discoveries": 10,
                 "mislabelled_enemy_as_friendly": 0,
                 "discoveries_per_energy": 0.04, "units_landed_home": 16,
                 "reserve_floor_violations": 0} for i in range(16)]
        payload = {"per_seed": rows}
        if version is not None:
            payload["scorer_version"] = version
        return payload

    def test_equal_versions_compare(self):
        from compare import compare
        result = compare(self._payload(4), self._payload(4), "dev")
        self.assertIn("all_gates_pass", result)

    def test_mismatch_raises(self):
        from compare import compare
        with self.assertRaises(ValueError):
            compare(self._payload(3), self._payload(4), "dev")

    def test_unstamped_pass_through(self):
        from compare import compare
        result = compare(self._payload(None), self._payload(None), "dev")
        self.assertIn("all_gates_pass", result)


class BaselineAggregateTest(unittest.TestCase):
    """Amendment 1.5: trust metrics aggregate; nulls stay unmeasured."""

    def test_trust_keys_aggregated(self):
        from baseline import summarize, AGGREGATE_KEYS
        for key in ("forged_vote_entries", "forged_vote_shaped_attempts",
                    "committed_inclusive_delta", "committed_p1_contacts",
                    "committed_p1_mislabelled",
                    "committed_p1_enemy_as_friendly",
                    "committed_p1_friendly_commits",
                    "commits_per_energy_unit"):
            self.assertIn(key, AGGREGATE_KEYS)
        rows = [
            {"seed": 0, "ruleset": "r", "scorer_version": 4, "recall": 0.5,
             "forged_vote_entries": 0, "forged_vote_shaped_attempts": 2,
             "committed_inclusive_delta": 1, "committed_p1_contacts": 1,
             "committed_p1_mislabelled": 0,
             "committed_p1_enemy_as_friendly": 0,
             "committed_p1_friendly_commits": 0,
             "commits_per_energy_unit": 0.5,
             "reports_by_auth_status": {"direct_verified": 5,
                                        "forged_rejected": 1},
             "attribution_accuracy": None,
             "detection_latency_turns": None},
            {"seed": 1, "ruleset": "r", "scorer_version": 4, "recall": None,
             "forged_vote_entries": 1, "forged_vote_shaped_attempts": 0,
             "committed_inclusive_delta": 0, "committed_p1_contacts": 2,
             "committed_p1_mislabelled": 1,
             "committed_p1_enemy_as_friendly": 1,
             "committed_p1_friendly_commits": 0,
             "commits_per_energy_unit": None,
             "reports_by_auth_status": {"direct_verified": 3},
             "attribution_accuracy": None,
             "detection_latency_turns": None},
        ]
        payload = summarize(rows, "dev", "cand")
        agg = payload["aggregate_means"]
        self.assertEqual(agg["forged_vote_entries"], 0.5)
        self.assertEqual(agg["forged_vote_shaped_attempts"], 1.0)
        self.assertEqual(agg["committed_inclusive_delta"], 0.5)
        self.assertEqual(agg["committed_p1_contacts"], 1.5)
        # None energy is skipped, never averaged as 0.
        self.assertEqual(agg["commits_per_energy_unit"], 0.5)
        self.assertEqual(agg["reports_by_auth_status_totals"], {
            "direct_verified": 8, "forged_rejected": 1})
        self.assertNotIn("attribution_accuracy", agg)
        self.assertNotIn("detection_latency_turns", agg)
        self.assertEqual(payload["scorer_version"], 4)


class MetadataFallbackTest(unittest.TestCase):
    """a2 re-review item 1: run/ruleset/source must never fall back to a
    filtered-out (e.g. forged) event. Probe shape: director without the
    keys + forged event first in 0X.jsonl + honest events elsewhere."""

    TRUTH = [{"pos": [0, 0], "kind": "Enemy", "priority": "Normal"}]

    def _score(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = pathlib.Path(tmp)
            (run_dir / "director.json").write_text(json.dumps({
                "ground_truth": self.TRUTH}))
            for name, evs in files.items():
                (run_dir / (name + ".jsonl")).write_text(
                    "\n".join(json.dumps(e) for e in evs))
            return score_run(run_dir)

    def _honest(self, run="honest-run"):
        base = {"unit": "A1", "run": run, "ruleset": "search-board-1",
                "source": "planner_simulation"}
        return [
            dict(base, turn=0, event="route_assigned", tile=[7, 11],
                 energy=30, reserve=3, route=[]),
            dict(base, turn=9, event="landed", tile=[7, 11], energy=25),
        ]

    def _forged_first(self):
        return {"unit": "X9", "turn": 1, "event": "discovery",
                "contact": 1, "tile": [0, 0], "reported_label": "Enemy",
                "auth_status": "forged_rejected", "run": "FORGED-RUN",
                "ruleset": "FORGED-RULESET", "source": "FORGED-SOURCE"}

    def test_metadata_from_scoring_events_only(self):
        s = self._score({"0X": [self._forged_first()],
                         "A1": self._honest()})
        self.assertEqual(s["run"], "honest-run")
        self.assertEqual(s["ruleset"], "search-board-1")
        self.assertEqual(s["source"], "planner_simulation")

    def test_metadata_null_when_nowhere_scored(self):
        honest = [dict(ev, run=None, ruleset=None, source=None)
                  for ev in self._honest()]
        # Drop the keys entirely: null fallback, as for missing director
        # values, never the forged stamp.
        for ev in honest:
            ev.pop("run", None)
            ev.pop("ruleset", None)
            ev.pop("source", None)
        s = self._score({"0X": [self._forged_first()], "A1": honest})
        self.assertIsNone(s["run"])
        self.assertIsNone(s["ruleset"])
        self.assertIsNone(s["source"])


class BridgeShapedJournalTest(unittest.TestCase):
    """Kulira Contract-v1 journals: direct sightings may omit `turn`
    (hearsay carries origin_turn instead). Scoring must not crash,
    and check completion must fail closed without ordering."""

    def test_turnless_direct_and_hearsay_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = pathlib.Path(tmp)
            (run_dir / "director.json").write_text(json.dumps({
                "run": "bridge", "ruleset": "test", "source": "test",
                "ground_truth": [
                    {"pos": [0, 0], "kind": "Enemy", "priority": "High"}]}))
            events = [
                {"unit": "K1", "event": "discovery", "contact": 1,
                 "tile": [0, 0], "reported_label": "Friendly",
                 "auth_status": "direct_verified",
                 "claimed_sender": "K1", "sighting_id": "s1"},
                {"unit": "C1", "event": "discovery", "contact": 1,
                 "tile": [0, 0], "reported_label": "Friendly",
                 "auth_status": "hearsay_relayed",
                 "claimed_sender": "K1", "origin_turn": 4,
                 "sighting_id": "s1"},
                {"unit": "D1", "event": "discovery", "contact": 1,
                 "tile": [0, 0], "reported_label": "Friendly",
                 "auth_status": "hearsay_relayed",
                 "claimed_sender": "K1", "origin_turn": 4,
                 "sighting_id": "s1"},
                {"unit": "A1", "event": "check_assigned",
                 "destination": [0, 0]},
            ]
            (run_dir / "K1.jsonl").write_text(
                "\n".join(json.dumps(e) for e in events))
            s = score_run(run_dir)
        # one direct false sighting is visible at assessed level…
        self.assertEqual(s["assessed_enemy_as_friendly"], 1)
        # …but neither asym nor P1 commits it (hearsay deduped to
        # at most one extra vote; total stays below commit floor)
        self.assertEqual(s["committed_asym_enemy_as_friendly"], 0)
        self.assertEqual(s["committed_p1_enemy_as_friendly"], 0)
        self.assertEqual(s["checks_completed_with_discovery"], 0)
        self.assertEqual(s["checks_completed_scan"], 0)


if __name__ == "__main__":
    unittest.main()
