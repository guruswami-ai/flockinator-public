# One Muse intervention chain, end to end (cycle-07 gate runner)

This is a single, complete example of how the Muse fleet's
review loop caught real defects before they could produce a false
science result. Public artifacts are linked; steps that live only in
the private lab book are marked **[private]** with their commit
hashes so the boundary is explicit.

## The chain

1. **Pre-registration frozen first.** Cycle-07 (peer-report trust)
   froze its treatments (T0-T4), policies (P0-P2), gates (G1-G6) and
   thresholds before any code ran, and sealed holdout seeds 100-109.
   Public residue: the design in
   [`../results/cycle-07/README.md`](../results/cycle-07/README.md);
   full pre-registration + amendments **[private]**.

2. **A lane built the gate runner; review returned it.** Lane
   implementation of `gate_runner.py` was reviewed by another lane
   and independently probed by the supervisor (Muse
   coordinator, human-supervised). The probe re-derived the frozen
   fixture rate by hand and found the runner computing the G2
   mislabel rate over the wrong denominator (Enemy→Friendly /
   discoveries = 0.0041 where the frozen definition — mislabelled /
   committed — gives 0.0750). Three more defects of the same class:
   wrong treatment→gate mapping (T2 left ungated), eligibility
   derived from the candidate instead of the baseline, and a
   baseline cross-check silently skipped for ordered-list baselines.
   Verdict: **RETURNED, nothing gated on it** **[private: supervisor
   runner review]**.

3. **Fix round, re-verified independently.** The fixed runner was
   re-probed by the supervisor: G2 rate exactly 0.075 on the frozen
   fixture, truncated baseline now exits 3 (ERROR) instead of
   silently passing, mapping T2→G3, T3/T4→G4; suite 69 green
   **[private commit 4a6e232]**. The runner that ships in this repo
   (`tools/fleet-score/gate_runner.py`) is that fixed version; its
   tests encode each returned defect as a regression case
   (`tools/fleet-score/test_gate_runner.py`).

4. **A second catch by reading, not running.** Reviewing the
   treatment implementation before release, the supervisor found the
   treatment labels had drifted from the frozen registration
   (T2/T3/T4 semantics permuted). The matrix was held, relabelled,
   identity (T0) re-proven, and production twins checksum-verified
   untouched **[private: step-2 relabel addendum]**. Public residue:
   twin provenance + parity output in
   `docs/results/cycle-07/provenance/`.

5. **A pre-registered treatment turned out vacuous — and was
   reported as such, not rescued.** Engagement instrumentation
   (added by amendment before runs) showed the patient-liar T4 never
   engages at turn ≥30 (0 of 10 opportunities). Rather than quietly
   redefining the threshold after seeing data, an amendment released
   T4 *as frozen* and required the vacuity to be labelled wherever
   the PASS appears — including machine-readably
   (`docs/results/cycle-07/verdicts/annotations.json`).

6. **Results verified before acceptance.** After the matrix ran,
   the supervisor recomputed 4 of 15 verdicts from the journals
   (bitwise gate/value/exit agreement) and re-scored all checked
   score files (80/80 identical) before accepting **[private commit
   92732b5]**. Kulira later re-scored samples independently through
   the public scorer before merging the publication PR.

7. **The uncomfortable result was kept.** The honest baseline fails
   its own frozen floors (they were calibrated to a rejected
   candidate's numbers). The chain's output was not a promotion but
   a recorded calibration flaw, no threshold edits, holdout kept
   sealed, and a named cycle-08 pre-registration to fix the design.

## What this demonstrates

- Review here is computational, not editorial: claims are re-derived
  from journals by a different agent (and a different code path)
  than produced them.
- The loop's most valuable outputs were *refusals*: a returned
  runner, a held matrix, a vacuous PASS labelled, a sealed holdout,
  zero promotions across cycles 00-07.
- Every step leaves an artifact a third party can re-check; where
  the artifact is private, this page says so instead of asking for
  trust.
