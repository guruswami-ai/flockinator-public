# Pre-registration: relay attack vs three corroboration policies

Registered before any run of this experiment. If a gate below is
changed after seeing results, the change and reason must be recorded
in the results document, not edited silently here.

## Question

When an adversary forges one sighting and relays copies of it through
other reporters, which corroboration rule keeps the dangerous error
(hazard committed as survivor) at zero, and what does it cost in
survivor recall?

## Setup (lab simulation, synthetic data only)

- 40 contacts per seed; each is survivor or hazard with p=0.5.
- Each contact receives 1-3 direct sightings from honest nodes.
- Each direct sighting labels the contact correctly with p=0.75
  (inside the 60-82% per-sighting identify band measured for the
  planner scenario); otherwise it flips the label.
- Each direct sighting carries one modality from {ir, co2, sound}
  and a unique sighting ID; sightings come from distinct nodes.
- Adversary: for each hazard contact with p=0.5, Kulira forges one
  sighting (modality ir, label survivor) and relays it as copies
  from 3 additional reporters. Copies share the forged sighting ID.
- Seeds: dev 0-19 for development; holdout 100-109 evaluated once,
  after dev results are written, with no parameter changes between.

## Policies under test

- **A reporter-count:** commit survivor when survivor-labelled
  reports (relayed copies count) are >=2 and outnumber
  hazard-labelled reports.
- **B sighting-ID dedup:** as A, but reports are deduplicated by
  sighting ID before counting.
- **C direct multi-modal:** as B, plus the committing sightings
  must span >=2 modalities and >=2 nodes (the rescue DIG rule).

## Metrics

Per policy, pooled over seeds: dangerous commits (hazard committed
as survivor), survivor recall (survivors committed / all survivors),
abstentions. Reported per seed in the evidence JSON.

## Pre-registered expectations and gates

- H1: policy A admits forged dangerous commits in at least one seed.
- H2: policies B and C admit zero dangerous commits whose deciding
  sightings include the forged sighting ID. (Honest-error dangerous
  commits, from flipped honest sightings, are counted separately
  and are expected to be non-zero at p=0.75.)
- H3: C's survivor recall is no more than 0.15 below B's; if it is,
  the multi-modal rule is too expensive at this sighting rate and
  that is the reported result.
- Gate for recommending a policy: zero forged-origin dangerous
  commits on dev AND holdout, with recall reported, not hidden.

## What this does not claim

Simulation only. No hardware, no radio, no on-node inference.
It tests corroboration logic under a relay adversary, in the same
seeded/gated style as the planner scorecard.
