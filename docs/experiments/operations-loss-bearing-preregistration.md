# Pre-registration: loss-bearing commitment regime (seeds 40-59)

Status: **pre-registered before this variant was run.** Simulation
only. Follows operations-reserve (seeds 0-19) and operations-binding
(seeds 20-39), in both of which aircraft **lost** was zero under
every strategy, so losses could not discriminate commitment
strategies. Contributor-model drafts and a parameter critique are
in `docs/research/contributor-notes/`; the freeze below adapts
their recommendations (lower fault rate than first drafted,
absolute rather than percentile battery threshold, miscalibration
rule independent of hypothesis direction) to this simulator.

## Regime (only changes from binding regime)

Binding regime retained: 8 incidents, 160 daylight turns,
recharge +4, damage grounds for the rest of the window. New:

- `p_fail = 0.01` per airborne turn (was 0.002). Independent
  mechanical fault rate, identical for all strategies.
- Far-survivor fraction 0.35 (was 0.15), return cost far = 14.
- Start battery 75 (was 100), so long far sorties can land below
  the 15-point tactical reserve and trigger the pre-registered
  forced-landing split (lost 0.1 / damaged 0.5 / empty-safe 0.4).

## Strategies

K8, K8R, K14, K16, ESC as before.

## Primary metrics

Aircraft lost (mean per window), unattempted incidents,
second- and fifth-incident readiness. Secondary: find rate,
turns-to-find, ready at end, damaged events.

## Hypotheses and falsification (paired by seed)

- **HL1:** K16 loses more aircraft than K14 (more airborne
  exposure). Falsified if mean lost K16 <= K14.
- **HL2:** K14 has no more unattempted incidents than K16 and a
  find-rate cost <= 5 points vs the best strategy. Falsified on
  either failure.
- **HL3:** ESC has the fewest lost + unattempted combined.
  Falsified if any strategy beats it on that sum.
- **Miscalibration rule (checked before hypotheses):** if pooled
  mean lost across strategies is < 0.2 or > 6 per window, declare
  the regime miscalibrated, report metrics without hypothesis
  verdicts, and register a successor with new seeds.

## Seeds

40-59, frozen here. Design-exposed in the wider programme; no
holdout claim. Any planner/firmware change remains a proposal to
the planner owner.
