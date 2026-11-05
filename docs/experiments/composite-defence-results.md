# Results: composite defence under combined attack

Lab simulation, synthetic data only. Pre-registered in
[composite-defence-preregistration.md](composite-defence-preregistration.md).
Evidence: `validation/kulira/composite-defence-001.json`. Two
simultaneous attacks: unverified forgeries with relays throughout,
and an ir-modality betrayal from contact 20 of 40.

## Results

| Policy | Dev post-betrayal dangerous | Forged-origin | Mean recall | Holdout dangerous | Holdout recall |
|---|---|---|---|---|---|
| E (admission + abstention) | 23 | 0 | 0.215 | 8 | 0.270 |
| **COMP (+ modality trust)** | **13** | **0** | **0.299** | **4** | **0.324** |

## Verdicts

- **H-K1 confirmed:** post-betrayal dangerous commits fall under
  the composite on both splits (23 -> 13 dev, 8 -> 4 holdout).
- **H-K2 confirmed with margin to spare:** recall does not fall -
  it *rises* (0.215 -> 0.299 dev). Once the betrayed modality is
  discounted, its honest-opposing labels stop vetoing true
  survivors, so weighting unblocks commits abstention was holding.
- **H-K3 confirmed:** forged-origin dangerous commits stay 0
  under both policies; admission control is unaffected by adding
  trust weights downstream.

## Gate outcome

The composite passes its pre-registered gate and is the current
recommended stack from the Kulira series:

1. **Admission by provenance** (policy D): only direct_verified
   sightings may decide; unverified/hearsay advisory only.
2. **Commit by margin with abstention** (policy E/F): close calls
   stay Unassessed; bought second looks only where a commit is
   reversible.
3. **Weight by learned modality trust**: distrust attaches to
   claim types, learned from revealed outcomes, never to reporter
   identity pooled across sensors.

Known remaining exposures, measured earlier in this series:
verified collusion (tolerance threshold k=1 of 8) and honest
identify error at fixed accuracy - neither is addressed by this
stack, and both are stated limits, not surprises.

## Limits

Simulation only; the combined world is new, so absolute numbers
are not comparable to the single-attack experiments. Trust rates
and thresholds are the registered parameters, not tuned.
