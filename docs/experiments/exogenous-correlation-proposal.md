# Draft protocol: honest common-cause correlation (NOT registered)

**2026-11-07; addresses [#173](https://github.com/guruswami-ai/flockinator-public/issues/173).**
Follows the accepted [design review](exogenous-correlation-design-review.md).
This is a reviewable draft, not a registration or experimental result. No new
seeds, firmware or device activity. The exact feasibility calculation below
already rejects the first simple candidate under the proposed recall guardrail:
**do not spend a seed-based evaluation budget confirming that known failure.**

## Narrow question and fixed candidate

Can known exposure-group provenance reduce false survivor actions caused by a
shared misleading cue, while losing at most five percentage points of survivor
recall relative to E in either environment? All four simulated reporters are
honest and authenticated. No collusion, forged relay, learning or outcome
feedback. This isolates an information-dependence failure, not malicious intent.

Use four synthetic reporters `n1`–`n4`, one genuine observation per reporter per
contact, unique sighting IDs, no missingness or delay. The latent exposure groups
are `{n1,n2,n3}` and `{n4}`. Deployment metadata supplies those groups in the
primary condition; it does not reveal whether a common error actually occurred.
Modality assignments are fixed (`ir,co2,sound,co2`), so modality names themselves
cannot certify independent information. None of these are physical node records.

Each seed has 200 contacts, exactly 100 hazards and 100 survivors, with a
precomputed random ordering. For each group/contact draw `C~Bernoulli(rho)`.
When C=1 all members use one shared error bit; otherwise use independent error
bits. Error probability is `p_hazard=0.25` or `p_survivor=0.05` according to the
true class. Groups are conditionally independent. Compare `rho=0` with
`rho=0.75`, keeping these marginals, reports and class schedules fixed. Draw
primitive streams separately and reuse them across environments and policies;
branching cannot consume a different number of RNG draws. See the review for
marginal/covariance derivation. The process is stylized, not calibrated physics.

Primary policy P selects the lexicographically first reporter from each
**observed** group, independent of report labels, then applies E unchanged.
With two selected reports, E acts only when both report survivor. Baselines:

- E on all four reports (at least two survivor reports and margin at least two,
  hence at least three survivor reports here).
- E-M on the same four reports, retaining its modality-diversity requirement.
- S, E on fixed reporters `n2,n4`, a label-independent two-report subsample.
  In the primary geometry it has the same expected behaviour as P; this control
  exposes how much any benefit is attributable to retaining two sources.
- T, all four reports required to say survivor, a stricter-count control.

All arms receive the same observable group metadata; E/E-M/S/T deliberately do
not use it. They never receive truth, error bits or common-error indicators.
The true-group-aware reference is a diagnostic only when observed labels are
wrong, never advertised as deployable.

Freeze two metadata stress conditions: **split**, all four observed groups are
distinct; **merge**, all four share one observed group. P then respectively
reduces to E or always abstains. Those are intentional failure controls, not
missing-data cases to discard. Metadata and candidate choice must not change
according to contact labels or condition outcomes.

## Exact feasibility screen: this candidate fails the guardrail

On independent survivor contacts each report is positive with probability
`q=0.95`. E's recall is `4*q^3*(1-q)+q^4 = 0.98598125`. P's recall is
`q^2 = 0.9025`, because its selected reporters come from independent groups.
The recall loss is **0.08348125**, or **8.348125 percentage points**. It exceeds
the proposed five-point limit without any sampling uncertainty. S has the same
recall; a provenance label adds no advantage over this preselected control in
this known geometry. These are exact model probabilities, not empirical
estimates, device observations or a registered experiment outcome.

This is not evidence that provenance can never help. It rejects **this policy,
geometry and guardrail combination**. Simply loosening the limit after this
calculation would select an easier objective, not improve the defence. A new
candidate needs a separately reviewed rationale and exact harm/recall screen.
An honest outcome for #173 is to publish this bounded negative design finding
and defer a seeded study until a nontrivial, decision-relevant candidate exists.

## Proposed analysis contract if a revised candidate merits registration

The primary contrast is candidate minus E on hazard false-action rate within
the correlated condition. Secondary environment contrast is E correlated minus
E independent; correlation does not necessarily harm every threshold rule.
Report per-seed dangerous/true-survivor commits, denominators, recall,
coverage and abstention for every arm/environment/metadata condition. All use
the same 200-contact window. Balanced truth gives 100 in each class; a missing
or malformed contact is an implementation error, not an excluded observation.

Proposed useful harm reduction `delta=0.05`; allowable recall loss
`epsilon=0.05` in **both** independent and correlated environments. These are
project choices for owner review. Success requires the primary harm upper
bound below `-delta` and both recall lower bounds above `-epsilon`. Failure
is established if the harm lower bound is at least `-delta` or either recall
upper bound is at most `-epsilon`; otherwise non-success is inconclusive.
Report a positively harmful effect separately. Comparisons use unrounded values.
No metadata robustness claim follows from primary-condition success; the
split/merge controls explicitly delimit the claim.

A possible fixed evaluation budget is 4,096 independently seeded worlds, with
three simultaneous bounded-difference intervals (`alpha=0.05`, `m=3`):
`mean +/- sqrt(2*ln(2*m/alpha)/4096)`, clipped to `[-1,1]`. The half-width is
about 0.04835. This is a conservative precision guarantee under the simulation's
independent-stream assumption, not a power claim. It avoids treating contacts
or nodes as independent replicates. The
[matched-control proposal](feedback-trust-matched-control-proposal.md#sample-budget-and-uncertainty)
gives the inequality and reference. Secondary contrasts are descriptive;
include their complete raw counts and paired distributions without selecting a
positive headline. Do not replace the primary method after looking at results.

Use exact enumeration and exposed development fixtures to select/verify code;
no fresh tuning sample is currently needed. Before any subsequent evaluation,
a separate registration must specify and commit its unique unexposed seed list,
source/config hashes and all revised candidate rules. Any observed development
seeds must be recorded as exposed and excluded from confirmation. No seeds are
allocated here, and **the current rejected candidate must not advance to that
registration merely because a budget has been described**.

## Minimal implementation, only after protocol decisions

A versioned generator and policy adapter can reuse E/E-M's `_commit` semantics;
do not change historical runners. A paired reporter must check complete
arm/condition/seed identity and distinguish invalid data from adverse results.
Deterministic acceptance fixtures should cover:

1. Exact marginals/moments, `rho=0/1`, and the recall calculation above.
2. Distinct genuine IDs versus forwarded duplicates; same-node repeat handling.
3. Identical primitive draws/report ordering across arms; report-order invariance
   where promised; no truth/latent-annotation influence on candidate decisions.
4. Split/merge labels, all-abstain coverage and exact denominator validation.
5. Falsification/interval boundary equality and missing-arm/seed rejection.

The candidate, sample plan and implementation still require review before a
registration. No physical or rescue-effectiveness claim follows from this work.
**Recommendation: drop this candidate under the proposed guardrail; retain the
construct and analysis contract for a justified revised defence.** The general
correlation effect is established prior art, as documented in the design review.
