# Results: colluding minorities vs policy E

Lab simulation, synthetic data only. Pre-registered in
[colluding-minorities-preregistration.md](colluding-minorities-preregistration.md).
Evidence: `validation/kulira/colluding-minorities-001.json`.
Trials are paired by seed across k: identical contacts and honest
sightings; only the number of colluding verified nodes varies.

## Tolerance curve (dangerous commits, dev 800 contacts)

| Colluders k (of 8 verified) | E dangerous | of which colluder-assisted | E mean recall | E-M dangerous | E-M mean recall |
|---|---|---|---|---|---|
| 0 | 3 | 0 | 0.300 | 0 | 0.219 |
| 1 | 14 | 10 | 0.307 | 10 | 0.229 |
| 2 | 35 | 34 | 0.322 | 29 | 0.243 |
| 3 | 65 | 65 | 0.321 | 53 | 0.243 |

Holdout (400 contacts) shows the same shape: E dangerous
9 / 12 / 29 / 43 for k = 0/1/2/3; E-M 6 / 8 / 24 / 32.

## Verdicts

- **H-F1 falsified.** A single colluding verified node already
  produces colluder-assisted dangerous commits (10 on dev). The
  mechanism: colluder + one flipped honest sighting, with no
  opposing label, reaches the margin 2-0. Verified status stops
  outsiders, not insiders.
- **H-F2 measured:** tolerance threshold (first k with
  colluder-assisted commits) is **k=1 of 8** for both policies at
  this sighting rate. Degradation is roughly linear in k, not a
  cliff at majority.
- **H-F3 partly confirmed:** E-M (adding >=2 modalities) cuts
  dangerous commits at every k (65 -> 53 at k=3) but does **not**
  raise the threshold - a lone colluder still gets through when
  honest sightings span modalities. Cost: ~0.08 recall.

## Reading

Policy D/E answers "is this reporter who it claims to be?" -
provenance. Collusion asks a different question: "is this verified
reporter honest?" No corroboration rule over the same sightings
answers that; the defences are of a different kind (behavioural
reputation over time, modality independence, abstention under
disagreement - E's Unassessed queue grows exactly where colluders
operate). The tolerance number that matters for design: at 1-3
sightings per contact, even 1-in-8 verified collusion is enough to
start landing dangerous commits.

## Limits

Simulation only. Colluders flip labels but use their normal
modality and sighting pattern; adaptive colluders are future work.
