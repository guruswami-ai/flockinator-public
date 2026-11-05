# Results (amendment): policy E, verified-origin + abstention

Lab simulation, synthetic data only. Pre-registered in
[relay-attack-amendment-e.md](relay-attack-amendment-e.md).
Evidence: `validation/kulira/relay-attack-e-001.json`.
Parent: [relay-attack-results.md](relay-attack-results.md) ·
[relay-attack-results-d.md](relay-attack-results-d.md).

## Pooled results

| Policy | Split | Dangerous | Forged-origin | Survivor recall | Unassessed (contacts) |
|---|---|---|---|---|---|
| D verified only | dev (800) | 17 | 0 | 0.465 | - |
| **E verified + abstention** | dev | **5** | **0** | 0.3225 | 368 |
| D verified only | holdout (400) | 9 | 0 | 0.5024 | - |
| **E verified + abstention** | holdout | **4** | **0** | 0.343 | 193 |

## Verdicts

- **H-E1 confirmed:** dangerous commits fall 17 -> 5 on dev
  (-71%) and 9 -> 4 on holdout (-56%). Forged-origin stays 0.
- **H-E2 confirmed:** recall cost is 0.1425 (dev) and 0.1594
  (holdout), inside the pre-registered 0.20 bound.
- **Gate passed:** E is recommended over D where an operator can
  act on Unassessed contacts.

## The honest cost

Abstention is not free safety: 368 of 800 dev contacts (46%) are
left Unassessed. At this sighting rate (1-3 sightings per contact)
and 75% identify accuracy, almost half the evidence is genuinely
ambiguous, and E says so instead of guessing. Nearly all remaining
dangerous commits under E are unanimous-but-wrong honest pairs,
which no voting rule can detect - only better sensing can.

Practical reading: E converts silent dangerous errors into visible
operator workload. Whether that trade is good depends on operator
capacity, which a deployment must budget for explicitly.

## Limits

Same simulation limits as the parent experiment. Unassessed counts
contacts with at least one survivor-labelled deciding sighting that
did not reach the commit margin, across both truth classes.
