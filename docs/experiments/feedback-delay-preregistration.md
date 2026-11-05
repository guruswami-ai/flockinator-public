# Pre-registration: delayed and missing outcome feedback

Registered before running. Follow-up to modality-betrayal, whose
main stated limit was timely revealed outcomes.

## Question

Field confirmation is slow and incomplete: a dig result may arrive
many contacts later, or never. How much does that degrade
modality-trust learning - measured by time to discount a lying
modality, post-betrayal dangerous DIGs, and survivor recall?

## Setup changes (rest identical to modality-betrayal)

- Arm under test: modality trust only (the winning arm).
- Feedback delay d in {0, 5, 15} contacts: the revealed outcome for
  contact t is applied to trust only at contact t+d.
- Feedback missingness m in {0.0, 0.5}: each revealed outcome is
  dropped entirely with probability m (never applied).
- Betrayal onset at contact 30 of 60, as before. Updates still come
  only from revealed outcomes, never from swarm commits.

## Pre-registered expectations

- H-H1: discount time (contacts from onset until ir trust < 0.3)
  grows with delay: median at d=15 exceeds median at d=0 by at
  least 5 contacts.
- H-H2: at d=15, m=0.5, post-betrayal dangerous DIGs remain below
  the static arm's from the parent experiment on the same seeds
  (learning degraded, not useless) - same-seed comparison.
- H-H3: survivor recall cost vs d=0/m=0 stays within 0.10 at
  d=5/m=0.5 (moderate field conditions are survivable), and is
  reported without bound at d=15/m=0.5.

## Limits

Simulation only; delay/missingness are fixed parameters, not
fitted to field timings (no field timing data published yet).
