#!/usr/bin/env python3
"""Matrix generator smoke: writes only under --out, never the archive.

Runs the generator in a fresh subprocess (its imports assert the
provenance twin; an in-process import would reuse cached modules).
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
GM_PATH = REPO / "docs/results/cycle-07/generate_matrix.py"
CYCLE = REPO / "docs/results/cycle-07"

DRIVER = """
import importlib.util, sys
spec = importlib.util.spec_from_file_location("gm", sys.argv[1])
gm = importlib.util.module_from_spec(spec); spec.loader.exec_module(gm)
assert "provenance" in gm.twin.__file__, gm.twin.__file__
gm.TREATMENTS = ("T0",); gm.SEEDS = [0]
gm.main(["--out", sys.argv[2]])
"""


class GenerateMatrixSmokeTest(unittest.TestCase):
    def test_out_only_and_import_paths(self):
        archive_engagement = CYCLE / "engagement.json"
        before = archive_engagement.stat().st_mtime_ns
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, "-c", DRIVER,
                                str(GM_PATH), tmp],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr[-500:])
            self.assertTrue((pathlib.Path(tmp) / "engagement.json").exists())
            self.assertTrue(
                (pathlib.Path(tmp) / "scores/T0/seed-0.json").exists())
        self.assertEqual(archive_engagement.stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()
