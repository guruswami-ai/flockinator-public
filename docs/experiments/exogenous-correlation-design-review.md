# E1 common-cause correlation: design review

**Status: proposal review only, not a pre-registration or result.** Addresses
[issue #173](https://github.com/guruswami-ai/flockinator-public/issues/173),
against public source `c1166a8`. No new experiment seeds were run. The
panel-policy canary retains priority. Recommendation: **revise**, then consider
a small host-only experiment after protocol review.

## 1. Define the claim and isolate correlation

The useful question is whether observable provenance helps avoid counting a
shared mistake repeatedly, without losing too much survivor recall. Agreement
does not necessarily cease to be evidence: perfectly duplicated evidence may
still carry one observation's information. Distinct node identities, signed
reports and different modality names do not establish statistical independence.

Choose one common cause, such as two sensors responding to the same misleading
environmental cue. Keep all nodes honest and report origins authenticated.
Exclude deliberate relay forgery from the first experiment: that changes both
the information structure and the threat model. Duplicate forwarding is already
handled by sighting-ID admission/deduplication; genuine, separately acquired
but correlated observations need distinct IDs.

Hold each sensor's class-conditional error probability, truth distribution,
node/modality assignment, report count, missingness, timing and policy thresholds
fixed between environmental conditions. Merely adding a shared fault on top of
independent noise raises individual error rates and cannot isolate correlation.

A minimal, analytically inspectable generator for equal-error sensors is:

- Within each fixed exposure group and contact, draw `C ~ Bernoulli(rho)`.
- If `C=1`, every member uses a shared error bit `Z ~ Bernoulli(p_y)`.
- Otherwise, members use independent error bits with probability `p_y`.
- Draw different groups independently, conditional on truth class `y`.

For `0 < p_y < 1`, each member has error probability `p_y` in both conditions,
and distinct members' error correlation within a group is exactly `rho`:
`E[E_i E_j] = rho*p_y + (1-rho)*p_y^2`. Set `rho=0` for independence.
This is a stylized common-cue model, not calibrated sensor physics.

Use separate, precomputed streams for truth, report selection, independent
errors, common errors and mixing indicators. All policy arms consume the exact
same generated observations. Across environments, reuse the same primitive
draws while changing only the mixing rule; branch-dependent RNG consumption
must not silently change truth or report schedules.

Check correlation of **errors conditional on truth**, not raw agreement:
independent accurate sensors already agree because they observe the same event.
Truth/error bits and latent group membership belong to evaluation, not the
deployed candidate's input.

## 2. Estimands and falsification

Separate two questions:

1. **Environment effect:** for the frozen baseline, difference in false-action
   rate between correlated and independent conditions, at identical marginal
   sensor error rates.
2. **Defence effect:** within the correlated condition, paired candidate-minus-
   baseline difference in false-action rate, with survivor-recall guardrails
   in both environments.

Define false-action rate as dangerous survivor actions divided by the number of
true hazard contacts. Report survivor recall, action coverage, abstention and
raw numerators/denominators on the same contact window. Do not divide dangerous
actions by true survivors or interpret fewer actions alone as safer performance.
Calibration is secondary unless the policy actually outputs probabilities.
Regret requires a frozen cost function and a precisely defined reference; a
latent-group-aware policy is a privileged diagnostic, not a deployable method.

Compute paired differences per seed, then uncertainty across seeds. Contacts
within a seed and nodes observing the same contact are not independent
replicates. Predeclare how seeds with no hazards/survivors are handled; do not
silently treat an undefined rate as zero. Fix the contact/class schedule if
appropriate, documenting the resulting evaluation population.

Before registration, fill in the primary condition, minimum useful harm
reduction `delta`, allowable recall loss `epsilon`, seed count and precision
rationale, interval construction, and multiplicity policy. One proposed rule
is: the upper uncertainty bound on the candidate-minus-baseline harm difference
is below `-delta`, while lower bounds on recall differences exceed `-epsilon`
in both environments. Predeclare joint coverage for these checks. A demonstrated
recall violation or harmful difference rejects the defence; intervals crossing
the boundaries are inconclusive, not a win. Historical experiment criteria stay
unchanged. No numerical thresholds or seed allocations are selected here.

The first hypothesis is not a universal theorem that correlation worsens every
threshold rule. For a two-report, two-positive rule on hazard contacts, independent
errors yield false-action probability `p_y^2`, whereas fully shared errors yield
`p_y`. This algebraic example demonstrates the mechanism; it does not estimate
the planned experiment's effect or require a new random run.

## 3. Use fair controls and observable inputs

Start with the shipped unweighted E policy and its modality-counting E-M variant.
Add one simple provenance-aware candidate before an online correlation learner:
select one report per observable source/exposure group by a label-independent
rule, then apply the same explicit counting/margin rule. Record selection and
abstention. With only one usable group the rule cannot produce two witnesses;
that loss of coverage must remain visible.

Specify where group metadata comes from before using it. A deployment/configuration
source identifier is plausible; the simulator's hidden common-error indicator is
not. Provide the same observable metadata to every arm. Include a preregistered
misspecification condition: an observed group label can split a real shared cause
or merge independent sources. Keep a true-group-aware reference separate and
label its extra information. If metadata is unavailable, the first claim is
limited to known provenance; learning a latent grouping is a separate project.

Add a simple stricter-count or label-independent report-subsampling control,
chosen on development data at a comparable recall target. Otherwise a candidate
can appear successful merely because it abstains more. Freeze all policies and
thresholds before held-out evaluation; do not tune to equal test-set recall.

## 4. Reuse the right seams

| Existing component | Useful reuse | Limit to preserve |
|---|---|---|
| [relay_attack.py](../../tools/kulira-core/kulira_core/relay_attack.py), `_commit` | Existing E/E-M decision semantics and report tuples | E requires at least two survivor reports and margin at least two; E-M adds distinct modalities, not a latent-cause test |
| [sensing.py](../../tools/kulira-core/kulira_core/sensing.py), `Reading` / `assess_contact` | A separate physical-interpretation fixture | `independent_nodes` counts distinct node IDs; it does not estimate independence, and this policy is not identical to E |
| [bridge.py](../../tools/kulira-core/kulira_core/bridge.py) | Admission and sighting-ID controls | Authentication/deduplication cannot remove common errors with distinct genuine IDs |
| [feedback_trust.py](../../tools/kulira-core/kulira_core/feedback_trust.py) | Reveal-boundary discipline if learning is later added | Do not reuse `reputation.generate_sequence` unchanged: it includes deliberate colluders |
| [modality_betrayal.py](../../tools/kulira-core/kulira_core/modality_betrayal.py) | Prior comparison to avoid duplicating | Its betrayal changes class-conditional IR error probabilities; it is not a fixed-marginal correlation manipulation |

Minimal new work is a separate versioned common-cause observation generator,
a provenance-group policy adapter, and a paired reporter with denominators.
Keep historical runners and their artifacts unchanged. Operations/planner
integration is unnecessary to establish this first mechanism.

Before any seed-based experiment, deterministic fixtures should check marginal
probabilities and pairwise moments by exact enumeration, `rho=0/1` limits,
distinct genuine IDs versus relay duplicates, same-node repeated reports,
missing/incorrect source metadata, report-order invariance where promised,
all-abstain coverage, and invariance of decisions to changes in withheld truth
or latent annotations. Any learned extension needs its own no-future-label test.

## 5. Novelty and go/no-go

The broad observation that correlated information can undermine aggregation is
established. Kao and Couzin model shared and independent environmental cues and
show that larger groups need not be more accurate. Their mechanism makes
"we discovered correlated agreement can be wrong" an insufficient novelty claim.
[Kao & Couzin, 2014](https://www.thekaolab.com/papers/Kao_ProcB_2014.pdf)

Stickler and colleagues also show accuracy consequences of correlated evidence
for ideal observers and early decisions. That is relevant prior art, though it
is not an evaluation of this repository's static policies or provenance defence.
[Stickler et al., 2023](https://journals.aps.org/prresearch/abstract/10.1103/PhysRevResearch.5.033020)

The narrower project contribution could be an auditable failure boundary for
authenticated corroboration, plus the benefit and cost of an implementable
provenance rule when its grouping information is imperfect. This differs from
delayed feedback and modality betrayal, but remains simulation evidence until a
physical common cause and observations are independently established.

**Revise now.** Proceed to registration only after the generator, metadata
availability, candidate/control rules, harm/recall criteria and seed budget are
fixed. Drop the proposed novelty claim if it is only the algebraic two-vote
example. Defer the run if it would displace the canary, require unavailable
ground truth as policy input, or add complexity without a decision the results
would change.

Suggested bounded work after design acceptance: (1) generator and exact
invariant checks; (2) policy adapter and metadata-misspecification fixtures;
(3) paired reporting and independent truth-access review. These can be separate
tasks with fixed interfaces. Collection remains gated on a reviewed registration;
this document authorizes none.
