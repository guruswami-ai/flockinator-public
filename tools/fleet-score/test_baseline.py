"""Baseline CLI regression: main() must print aggregate_means, not crash."""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

import baseline


def _fake_score(seed, dest):
    dest.mkdir(parents=True, exist_ok=True)  # real generate() creates this
    score = {key: None for key in baseline.AGGREGATE_KEYS}
    score.update({"recall": 0.5, "ruleset": "test-ruleset",
                  "scorer_version": "test"})
    return score


class BaselineMainTest(unittest.TestCase):
    def test_main_writes_payload_and_prints_aggregates(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "out"
            stdout = io.StringIO()
            with mock.patch.object(baseline, "generate",
                                   side_effect=_fake_score):
                with contextlib.redirect_stdout(stdout):
                    rc = baseline.main(
                        ["--seeds", "0", "--out", str(out), "--label", "dev"])
            self.assertEqual(rc, 0)
            payload = json.loads(
                (out / "baseline-dev.json").read_text())
            self.assertEqual(payload["aggregate_means"]["recall"], 0.5)
            self.assertIn("recall: 0.5", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()


class ParseSeedsTest(unittest.TestCase):
    def test_range_and_list(self):
        self.assertEqual(baseline.parse_seeds("0-2"), [0, 1, 2])
        self.assertEqual(baseline.parse_seeds("3,5"), [3, 5])

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            baseline.parse_seeds("")

    def test_duplicates_rejected(self):
        with self.assertRaises(ValueError):
            baseline.parse_seeds("1,1")
