# Proposal (NOT registered): matched controls for feedback trust

**Revised 2026-11-07 after [#172](https://github.com/guruswami-ai/flockinator-public/issues/172).**
This is a concrete protocol proposal for owner review, **not a registration,
implementation approval or result**. No fresh seeds have been selected or run.
The numerical choices below are proposed decision tolerances, not observed
performance or an assertion of statistical power.

## Question and preserved evidence

Does enabling online updates improve REP relative to its own frozen unit-weight
configuration under delayed, incomplete feedback, at an acceptable recall cost?
The historical E comparison changes thresholds as well as updating. The
[corrected results](feedback-trust-confirmatory-results.md) remain a bundled
policy comparison, not an estimate of the causal effect of learning.

The exposed post hoc diagnostic records 91/83 second-half dangerous commits for
frozen REP versus 45/38 for learned sparse REP (dev/confirmation); E records
36/36. Learning helps its frozen counterpart on those sequences, while sparse
REP does not beat E on dangerous counts. These observations motivate this
proposal but cannot serve as its confirmation. Seeds 220–259 remain exposed.

## Arms and information boundary

Reuse `reputation.generate_sequence` unchanged: 60 contacts, eight authenticated
reporters, two colluders, the current report selection and error process. This
is a simulation about behavioural trust, not honest common-cause correlation.
All arms consume identical reports, outcome-reveal masks and reveal timing.

| Arm | Updating | Weighted survivor floor | Weighted margin |
|---|---|---|---|
| L1 | existing REP updates | 1.5 | 1 |
| F1 | fixed unit weights | 1.5 | 1 |
| L2 | existing REP updates | 1.5 | 2 |
| F2 | fixed unit weights | 1.5 | 2 |

F2 is exactly E for these integer unit-weight reports; verify decision-by-decision
rather than adding a redundant fifth arm. L1/F1 isolate enabling updates at
fixed thresholds. L2/F2 estimate the same effect at the strict threshold. L2/L1
is the threshold effect among learned policies; the difference between the two
updating effects is the interaction. Do not describe L2/L1 alone as the effect
of learning. Exclude REP-P: it introduces a separate graduation rule.

Use the shipped reputation initialization, clipping and increments. The frozen
arms still receive and count the same reveal events, with weight application
disabled. Do not implement freezing by changing availability to zero: although
that reproduces current frozen decisions, it changes the information budget.
Record offered/applied reveal counts and updates per seed. Final post-flush
weights are diagnostics only and must never be used for earlier decisions.
Delay zero means an outcome can first affect the *next* contact; preserve the
runner's decision-before-current-outcome ordering.

Two cells only: full feedback `(D=0, A=1)` and the primary sparse/delayed cell
`(D=15, A=0.25)`. Use the existing separate reveal stream `seed ^ 0xFEED`.
These cells do not identify delay separately from sample count or missingness.

## Endpoints and decision rule proposed for review

Compute **every** endpoint on contacts 30–59, inclusive. For each seed and arm,
retain hazard/survivor counts, dangerous/true-survivor commits, total commits,
abstentions, and reveal/update counts. Define harm as dangerous commits divided
by true hazards, recall as true-survivor commits divided by true survivors, and
coverage as commits/30. Existing whole-sequence `recall` and `decisions` fields
cannot stand in for these fields. Report pooled counts alongside seed means.

Primary contrast is L1 minus F1 in the sparse/delayed cell. Proposed practical
minimum harm reduction is **0.05** (five percentage points per hazard contact);
maximum tolerable recall loss is **0.05** in each of the two cells. These are
explicit project tradeoffs for review, not safety standards or estimated effects.
The three prespecified paired seed differences are sparse harm, sparse recall
and full-feedback recall. A joint success requires:

- the sparse-harm upper bound is below `-0.05`;
- both recall lower bounds are above `-0.05`.

Use the simultaneous bounds in the next section, without rounding comparisons.
If the harm lower bound is at least `-0.05`, the useful-benefit criterion is
rejected; if either recall upper bound is at most `-0.05`, the guardrail is
rejected. Other non-successes are inconclusive. Also state whether harm is
positively worse (lower bound above zero). Equality does not pass. Report all
four arms/cells even when the primary claim fails. Other contrasts are
secondary descriptive estimates, not substitute routes to a positive headline.

## Sample budget and uncertainty

Propose **4,096 fresh evaluation seeds**, fixed before collection. Use only the
already exposed seeds for compatibility/development; no new tuning split is
needed because all candidate rules above are fixed. A seed whose second half
has no hazards or no survivors is ineligible for the joint rate estimand:
report it, exclude it from all three paired estimates, and do not replace it.
The target population is therefore this generator conditional on both classes
being present in the evaluation window. Do not inspect decisions to select
eligible seeds or replace undefined rates with zero.

For each difference `d_i` in `[-1,1]`, use mean `d` and half-width
`h = sqrt(2 * ln(2*m/alpha) / n)`, clipped to `[-1,1]`, where `m=3`, `alpha=0.05`,
and `n` is the eligible seed count. This follows the bounded-variable inequality
and a union bound: `P(any |mean-Emean| > h) <= 2*m*exp(-n*h*h/2)`.
[Hoeffding (1963)](https://www.cs.rpi.edu/academics/courses/spring06/random/hoefding.pdf).

At `n=4096`, `h≈0.04835`: the budget guarantees this conservative absolute
precision under independent seed streams, not power to detect a five-point
benefit. A win would need an observed harm difference below roughly `-0.09835`
and both observed recall differences above roughly `-0.00165`. This demanding
rule may yield an inconclusive result; do not increase N after seeing it. If
fewer than 4,000 eligible seeds remain, report the estimates/bounds but mark the
planned precision incomplete, with no success claim. This bound tolerates
arbitrary within-seed dependence; ticks are not replicates. PRNG streams are a
simulation approximation to the independence assumption, which must be stated.

If the owner prefers a smaller budget or variance-based interval, revise the
proposal and precision rationale **before** registration or evaluation access.
No optional stopping, selected-seed retry, or post hoc interval substitution.

## Before registration and implementation

Owner protocol review must accept or amend these choices. Then publish a
separate registration commit with the complete unique seed list checked against
all exposed artifacts, the source/configuration hashes and the analysis rule.
No evidence file may precede that commit. Numerical seed values are deliberately
not allocated by this proposal. A separate runner must preserve historical APIs
and archives, with tests for F2=E, frozen-weight invariance, same input/reveal
streams, reveal-boundary sensitivity, same-window denominators and interval
edge cases. Collect only after that implementation is independently checked.

Recommendation: **revise/approve the protocol choices, then register**. Until
then there is no new run and no change to the historical claim boundaries.
