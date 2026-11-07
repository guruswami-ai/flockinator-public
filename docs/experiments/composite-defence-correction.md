# Correction (2026-11-05): composite comparison is a bundled-policy comparison

This correction is dated and appended; the original
pre-registration and results are preserved unchanged.

## What was wrong

The composite pre-registration described COMP's commit rule
(weighted survivor sum >= 1.5, weighted margin >= 1.0) as "the
trust=1 image of E's 2-sighting/2-margin rule". That equivalence
is false. Counterexample, verified in code and now pinned as a
regression test (`test_composite.py::test_bundled_policies_differ_at_unit_trust`):
with unit trust and deciding sightings of 2 survivor + 1 hazard,
COMP commits while E abstains.

## What the published result therefore shows

The composite experiment compared two **bundled** policies that
differ in two ways at once: (a) learned modality-trust weights,
and (b) a looser commit threshold. The measured effect
(post-betrayal dangerous 23 -> 13, recall 0.215 -> 0.299) is a
valid comparison of those two bundles on identical streams; it
does **not** isolate the effect of learned trust weighting.
Attributing the gain to modality trust alone would be a causal
overstatement, and earlier wording that implied mechanism
isolation is corrected by this note.

## What would isolate the mechanism

A factorial comparison crossing {fixed, learned} weights with
{E thresholds, COMP thresholds} on identical report streams,
pre-registered before running, with a declared primary contrast.
That experiment is proposed, not yet run.

## What is unaffected

Policies D and E, the relay-attack series, modality-betrayal,
and the other single-variable experiments do not rely on the
false equivalence. Cycle-07 and planner scorecard results are
separate artefacts and are unaffected.

## Status update (2026-11-07)

The "proposed, not yet run" statement above records the position on 2026-11-05;
that follow-up has since been completed. See the
[factorial registration](factorial-trust-preregistration.md) and
[factorial results](factorial-trust-results.md), with synthetic evidence in
`validation/kulira/factorial-trust-001.json`. The four cells separate weighting
and thresholds in the composite world, with recall costs reported. This does
not retrospectively repair the original bundled comparison or establish the
same effect under delayed/incomplete feedback; that separate matched-control
question is [still a proposal](feedback-trust-matched-control-proposal.md).
