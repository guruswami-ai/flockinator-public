# Results: feedback-trust confirmatory (seeds 240-259)

Run under
[feedback-trust-confirmatory-preregistration.md](feedback-trust-confirmatory-preregistration.md).
Evidence: `validation/kulira/feedback-trust-confirmatory-001.json`.
Simulation only. Second-half dangerous commits:

| Policy | D=0 A=1.0 | D=15 A=0.25 |
|---|---|---|
| E (no learning) | 36 | 36 |
| REP | 12 | 38 |
| REP-P | 22 | 83 |

- **HC1 confirmed (narrowly).** REP at the extreme cell (38)
  is again worse than never learning (36). The dev effect
  replicates in direction, with a smaller margin than the dev
  split suggested (45 vs 36) - the honest estimate is "about
  parity-to-worse", not a large penalty.
- **HC2 confirmed.** REP-P at 83 is 2.3x the no-learning
  baseline: the probation collapse is real and large.
- **HC3 sanity holds.** REP at full feedback (12) beats E (36).

**The line closes with the boundary claim:** learned
reputation helps only when outcome feedback is prompt and
substantially complete. Delay alone at full availability
still helps (REP D=15 A=1.0, dev grid); it is delay *combined
with* sparse reveal that inverts the advantage, and any
probationary weighting that counts un-revealed observations
is dangerous in exactly that regime. Defence design rule
carried forward: a node may only discount a reporter on
outcomes it has actually received, and when feedback quality
is unknown, strict counting or abstention is the safe default.

**Correction and narrowing (2026-11-07, issue #159).** The
registered HC outcomes above stand, but the conclusion is
narrower than first stated:

- The HC1 effect is **small**: paired per-seed differences
  (REP minus E, extreme cell) average +0.10 dangerous commits
  per seed (per-seed evidence:
  `validation/kulira/feedback-trust-paired-001.json`). This
  supports a small observed aggregate reversal in this world,
  not a well-established population penalty. No post hoc
  interval is presented as a registered test.
- Coverage differs in the same window: REP commits more
  (190 vs E 173) and finds more true survivors (152 vs 137 of
  306). Precision is comparable (0.800 vs 0.792). "More
  dangerous commits" alone does not establish blanket
  inferiority; it establishes a harm/recall trade-off that
  needs an explicit objective to judge.
- E and REP also differ in commit thresholds (margin >=2 vs
  >=1 plus a weight floor), so this comparison does **not**
  isolate learning as the cause of the difference relative
  to E. A causal claim needs the matched frozen-weight
  control registered as future work in issue #159.
- Delay alone does not remove the benefit (REP at D=15,
  A=1.0: 20 vs E 36 in this run). The accurate boundary is:
  reputation's advantage inverts in this grid only when delay
  and sparse reveal combine, for these policies and horizon.
