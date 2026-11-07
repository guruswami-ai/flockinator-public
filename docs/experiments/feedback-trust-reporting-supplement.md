# Post hoc reporting supplement: feedback trust

**2026-11-07; exposed seeds only, not a new registered test.** Supports
[#134](https://github.com/guruswami-ai/flockinator-public/issues/134).
The additive [`feedback_audit.py`](../../tools/kulira-core/kulira_core/feedback_audit.py)
replays the unchanged policy/generator on development seeds 220–239 and historical
confirmatory seeds 240–259. It reports all 27 development and 12 confirmatory
policy/condition cells. Historical registrations, JSONs and point-rule verdicts
are preserved; these new summaries cannot strengthen them retroactively.

Artifact: [`feedback-trust-posthoc-audit-001.json`](../../validation/kulira/feedback-trust-posthoc-audit-001.json).
It contains reporter and source-module SHA-256 hashes, every per-seed count/rate,
paired REP-minus-E and REP-P-minus-E differences, pooled counts/rates and
reconstructed update-event budgets. Only synthetic public data is used.

## Same-window findings

All metrics below use **contacts 30–59 inclusive**. Harm is dangerous commits /
true hazards; recall is true-survivor commits / true survivors; coverage is all
commits / 600 contacts per split. Rates in this table are pooled counts, whereas
the artifact's paired mean differences weight each seed equally. They need not
be numerically identical. Undefined per-seed class rates remain null and their
counts are reported; none occur in these historical cells.

| Split / feedback | Policy | Dangerous / hazards | Found / survivors | Commits / contacts |
|---|---|---|---|---|
| Dev, full `(0,1)` | E | 36 / 308 | 135 / 292 | 171 / 600 |
| Dev, full | REP | 9 / 308 | 94 / 292 | 103 / 600 |
| Dev, full | REP-P | 13 / 308 | 111 / 292 | 124 / 600 |
| Dev, sparse/delayed `(15,0.25)` | E | 36 / 308 | 135 / 292 | 171 / 600 |
| Dev, sparse/delayed | REP | 45 / 308 | 166 / 292 | 211 / 600 |
| Dev, sparse/delayed | REP-P | 91 / 308 | 208 / 292 | 299 / 600 |
| Historical confirmation, full | E | 36 / 294 | 137 / 306 | 173 / 600 |
| Historical confirmation, full | REP | 12 / 294 | 95 / 306 | 107 / 600 |
| Historical confirmation, full | REP-P | 22 / 294 | 108 / 306 | 130 / 600 |
| Historical confirmation, sparse/delayed | E | 36 / 294 | 137 / 306 | 173 / 600 |
| Historical confirmation, sparse/delayed | REP | 38 / 294 | 152 / 306 | 190 / 600 |
| Historical confirmation, sparse/delayed | REP-P | 83 / 294 | 215 / 306 | 298 / 600 |

At full feedback REP's lower harm comes with lower survivor recall than E.
At sparse/delayed feedback REP finds more survivors and commits slightly more
hazards than E in the historical confirmation. Neither comparison establishes
unqualified dominance. The threshold confound remains: E requires margin two,
REP margin one with a weight floor. The exposed frozen diagnostic, discussed in
[the corrected results](feedback-trust-confirmatory-results.md), is the relevant
post hoc comparison for whether updating helps its own configuration.

## Paired uncertainty is descriptive

The supplement reports paired per-seed rate differences and **marginal** 95%
bounded-variable intervals: `mean +/- sqrt(2*ln(40)/n)`, clipped to `[-1,1]`.
With `n=20` the half-width is about **0.60736**, intentionally reflecting how
weak a distribution-free guarantee is at this sample count. The bound assumes
independent seed streams; contacts within a seed are not independent replicates.
[Hoeffding (1963)](https://www.cs.rpi.edu/academics/courses/spring06/random/hoefding.pdf).

These intervals were selected after the historical observations were exposed,
are not adjusted across cells/endpoints, and do not restore confirmatory
coverage after adaptive analysis selection. They are a conservative descriptive
sensitivity calculation, not a new hypothesis test. There is **no PASS/FAIL
field**, no new acceptance threshold and no significance claim. The small
confirmation REP-minus-E sparse harm difference is about +0.00905 in mean
per-seed hazard rate; this evidence does not establish a population penalty.

## Update events and cost boundary

The reveal stream is reconstructed from the same seed (`seed ^ 0xFEED`),
availability and deduplicated report IDs used by the historical runner.
One outcome draw occurs after each decision. A selected outcome offers one
update per retained report. Its first application is at
`max(originating_contact+1, originating_contact+delay)`; updates beyond contact
59 are applied only by the historical final flush. Thus delay zero never makes
the current label available to its own decision.

| Split / feedback | Selected outcomes (whole 60-contact sequences) | Offered report updates | Applied before a decision | Of those, before decisions 30–59 | Final-flush updates |
|---|---|---|---|---|---|
| Dev, full | 1200 | 2992 | 2939 | 1505 | 53 |
| Dev, sparse/delayed | 302 | 740 | 533 | 361 | 207 |
| Historical confirmation, full | 1200 | 3011 | 2957 | 1516 | 54 |
| Historical confirmation, sparse/delayed | 307 | 783 | 632 | 408 | 151 |

The before-decision and final-flush columns partition offered report updates.
The window column counts *application times*, not labels originating in that
window; the artifact also distinguishes selected outcomes originating there.
Counts are identical across E/REP/REP-P within a seed/condition because the
historical runner updates bookkeeping for all three, even though E ignores
weights when deciding. Do not infer that an efficient deployed E needs these
updates, or that equal event counts imply equal CPU cost. Counts include clipped
updates that do not change a weight; they are application attempts, not effective
changes. Historical wall-clock time, memory, energy and API costs were not
recorded and remain unavailable. No current benchmark is presented as past cost.

## Primary-literature context and limits

Joulani, Gyorgy and Szepesvari study delayed feedback in online learning and
analyze regret under adversarial and stochastic settings. Their delay-aware
algorithms and formal guarantees establish that delayed-feedback learning is
an existing research problem; this repository's clipped reputation heuristic
is not one of their algorithms and does not inherit those guarantees.
[Joulani et al., ICML 2013](https://proceedings.mlr.press/v28/joulani13.html).

Cesa-Bianchi, Lugosi and Stoltz study prediction with expert advice when outcome
queries are limited, deriving error/regret guarantees for label-efficient
prediction. Their forecaster chooses queries under a budget; here labels are
withheld by an exogenous Bernoulli process and there is no query strategy.
Consequently this experiment is a particular finite-horizon harm/recall
comparison, not a new solution to label-efficient learning.
[Cesa-Bianchi et al., COLT 2004](https://mercurio.srv.di.unimi.it/~cesabian/Pubblicazioni/C25.pdf).

The useful contribution is the inspectable failure/tradeoff boundary of these
specific policies and assumptions. The current grid does not distinguish the
causal effect of delayed labels from fewer updates available before decisions;
that would require a separately frozen information-budget control. It does not
show physical rescue benefit or a universal limit of reputation learning.

## Reproduce and verify

Run from the repository root, writing to a **new** output path:

```sh
PYTHONPATH=tools/kulira-core uv run --no-project python -m kulira_core.feedback_audit --out /tmp/feedback-trust-audit.json
cmp /tmp/feedback-trust-audit.json validation/kulira/feedback-trust-posthoc-audit-001.json
uv run --project tools/kulira-core --locked pytest tools/kulira-core/test_feedback_audit.py tools/kulira-core/test_feedback_trust.py
```

Choose another path if it already exists: the command refuses overwrites. There
is no CLI option to run fresh seeds. Module hashes make source changes visible;
with identical sources the JSON is byte-deterministic. Regression tests also
reproduce all historical aggregate cells and exercise decision/reveal boundaries,
window denominators, duplicates, undefined rates, pairing and output protection.

This completes the retrospective reporting and literature-context portion of
#134. Any claim isolating online learning from thresholds still requires the
[matched-control proposal](feedback-trust-matched-control-proposal.md), owner
protocol review and separate registration. The lack of measured historical
runtime cost is retained as a limitation, not filled with reconstructed numbers.
