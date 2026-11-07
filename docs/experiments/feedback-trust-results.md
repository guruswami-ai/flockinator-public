# Results (DEV): learned trust under delayed/incomplete feedback

Dev seeds 220-239 under
[feedback-trust-preregistration.md](feedback-trust-preregistration.md).
Evidence: `validation/kulira/feedback-trust-dev-001.json`.
Runner: `kulira_core/feedback_trust.py` (truth-boundary and
full-feedback-compatibility tested). Simulation only.

Second-half dangerous commits (lower is safer); E is 36 in
every cell by construction (it never learns):

| Policy | D=0 A=1.0 | D=5 A=0.5 | D=15 A=0.25 |
|---|---|---|---|
| E (no learning) | 36 | 36 | 36 |
| REP | 9 | 19 | 45 |
| REP-P (probation) | 13 | 78 | 91 |

- **HF1 supported.** At full feedback REP (9) beats E (36) -
  the original reputation result replicates on these seeds.
- **HF2 FALSIFIED.** At the extreme cell (15-contact delay,
  25% of outcomes ever revealed) REP records 45 dangerous
  commits, *worse* than never learning at all (36). Stale,
  sparse reputation is not merely useless; it is actively
  misleading, because colluders keep near-initial trust for
  most of the sequence while honest nodes are randomly
  discounted by the few reveals that do arrive.
- **HF3 supported.** Degradation is monotone along the
  registered diagonal for REP (9 -> 19 -> 45 second-half
  dangerous). Diagonal only: at full availability REP across
  delays 0/5/15 is 9/11/9, not monotone. The table is the
  selected registered diagonal; the full 27-cell grid is
  in the evidence JSON.
- **The surprise is REP-P.** Probation (full weight until 10
  observations) is catastrophic under incomplete feedback:
  73-91 dangerous commits, two to three times the no-learning
  baseline. With few reveals, almost nobody graduates from
  probation, so the policy behaves like unweighted counting
  with REP's *lower* commit thresholds - the worst of both.
  At full feedback REP-P was the recall-friendly variant
  (0.49 vs REP 0.38); under sparse feedback that inverts.

Coverage note, per the registered guardrail: REP's recall
*rises* as feedback worsens (0.38 -> 0.59) because undiscounted
colluders push more commits through. The dangerous-commit
increase is therefore not a coverage artefact in the safe
direction - the policy commits more *and* commits worse.

Boundary condition, stated as the finding: learned reputation
is a fair-weather defence. It needs outcome feedback that is
both prompt and substantially complete; below that, the honest
options are unweighted strict counting or abstention, and any
probationary-trust mechanism must count *revealed* observations
before it is allowed to discount anyone. A confirmatory run on
fresh seeds is required before this becomes a claim; the dev
table above is the selected registered diagonal (HF3);
the complete 27-cell grid is in the evidence JSON.

**Correction (2026-11-07, issue #159).** Two statements above
are corrected. (1) The design rule about unrevealed
observations misdescribed this runner: `seen` increments only
when a revealed label is applied, so REP-P already counts
revealed observations only. Its failure mechanism is that
sparse feedback keeps the permissive probation policy active
for most of the sequence while its commit thresholds stay
lower than E's. (2) "Reputation is a fair-weather defence /
helps only when prompt" is too broad: at D=15 with full
availability REP still beats E clearly. The supported claim
is the narrower one in the confirmatory correction: the
advantage inverts when delay and sparse reveal combine, in
this world, for these policies. The threshold confound (E
requires margin >=2, REP >=1) is also acknowledged there.

**Supersession (2026-11-07, #159 follow-up).** The HF2
causal phrase above ("actively misleading", "worse than
never learning") is retracted. E uses a stricter commit
rule than REP, so that comparison does not isolate
learning. Post hoc matched diagnostic on these same
exposed seeds, labelled post hoc and not a registered
result: REP frozen at unit weights (availability 0)
records 91 second-half dangerous commits (dev) and 83
(confirmatory), against learned sparse REP at 45 and 38.
Learning improves on its own frozen configuration in
both splits. At the extreme cell REP-P equals that
frozen unit-weight rule exactly (91 dev, 83
confirmatory): probation never graduates there, so its
excess is the unit-weight rule at REP thresholds, not a
probation dynamic. Historical evidence JSON is
unchanged; no new seeds were run.

Frozen-weight companion evidence: `validation/kulira/feedback-trust-frozen-001.json` (post hoc, generated as labelled there).
