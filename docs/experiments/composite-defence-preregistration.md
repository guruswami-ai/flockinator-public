# Pre-registration: composite defence under combined attack

Registered before running. Integration test of the Kulira series'
separately-measured elements, in one world with two simultaneous
attacks. Elements were each measured alone first (relay attack
#36-#39, modality betrayal #40); this asks whether they compose.

## World (lab simulation, synthetic only)

- 40 sequential contacts per seed, survivor/hazard p=0.5.
- 1-3 honest direct sightings per contact (75% identify accuracy,
  modality from {ir, co2, sound}, distinct nodes, unique IDs).
- Attack 1 (from contact 0): on hazards with p=0.5, Kulira forges
  one unverified ir sighting claiming survivor, relayed by 3
  copiers (hearsay).
- Attack 2 (from contact 20): the ir modality betrays - honest ir
  sightings flip their label with p=0.8. Other modalities honest.
- Outcomes revealed after each contact; trust learns only from
  revealed outcomes.

## Policies

- **E:** policy-D pool (direct only, dedup) + abstention margin
  (commit survivor if >=2 survivor sightings and margin >=2).
- **COMP:** same pool and admission, but each deciding sighting is
  weighted by its modality's learned trust (init 1.0; after each
  revealed contact, sightings whose label matched truth +0.05,
  mismatched -0.10, clamp [0.1, 1.0]). Commit if weighted survivor
  sum >= 1.5 and weighted margin >= 1.0 (the trust=1 image of E's
  2-sighting/2-margin rule).

## Pre-registered expectations and gate

- H-K1: post-betrayal (contacts 20-39) dangerous commits under
  COMP are strictly below E's, dev and holdout.
- H-K2: COMP survivor recall (whole run) is no more than 0.15
  below E's on either split.
- H-K3: forged-origin dangerous commits stay 0 under both
  (policy-D admission unchanged by weighting).
- Gate: recommend COMP as the composite if all three hold.

## Limits

Simulation only; trust update rates and commit thresholds are the
registered parameters above, not tuned after seeing results.
