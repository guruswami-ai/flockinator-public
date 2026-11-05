# Pre-registration: behavioural reputation vs verified colluders

Registered before running. Follow-up to colluding-minorities,
where policy E fell to a single verified liar. Provenance cannot
answer "is this verified reporter honest over time?" - behaviour
might.

## Question

If deciding sightings are weighted by each node's behavioural
reputation - learned from revealed outcomes over sequential
contacts - does the swarm suppress verified colluders fast enough
to matter, and at what recall cost?

## Setup (lab simulation, synthetic only)

- 60 sequential contacts per seed; survivor/hazard p=0.5.
- 8 verified nodes; k=2 are colluders (they label every hazard
  they sight as survivor, valid keys, normal modalities).
- Each contact: 2-3 distinct nodes sight it; honest sightings
  label correctly with p=0.75. Sightings carry modality from
  {ir, co2, sound}; modalities play no role in this experiment.
- Outcomes revealed after each contact; reputation learns only
  from revealed outcomes.
- First half (contacts 0-29) vs second half (30-59) reported
  separately: reputation needs history.

## Policies

- **E:** direct sightings deduped by ID; commit survivor if >=2
  survivor labels and margin >=2 (unweighted).
- **REP:** same pool; each sighting weighted by its node's
  reputation (init 1.0; label matched truth +0.05, mismatched
  -0.15, clamp [0.1, 1.0]); commit if weighted survivor sum >=1.5
  and weighted margin >=1.0.

## Pre-registered expectations and gate

- H-L1: second-half dangerous commits under REP are strictly
  below E's, dev and holdout.
- H-L2: REP whole-run survivor recall is no more than 0.15 below
  E's on either split.
- H-L3: colluders' mean reputation by contact 59 is below honest
  nodes' mean reputation (the mechanism actually separates).
- Gate: recommend REP as an additional layer if all three hold.
  Collusion tolerance is reported as measured, not spun.

## Limits

Simulation only. Colluders are label-flippers with fixed
identity; identity-changing (Sybil) adversaries are out of scope.
