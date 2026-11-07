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
