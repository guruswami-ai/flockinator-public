# Results: relay attack vs three corroboration policies

Lab simulation, synthetic data only. Pre-registration (written and
committed before any run): [relay-attack-preregistration.md](relay-attack-preregistration.md).
Evidence: `validation/kulira/relay-attack-001.json`.
Reproduce: `python -m pytest tools/kulira-core -q` and the
`run_experiment` entry in `kulira_core/relay_attack.py`
(dev seeds 0-19, holdout seeds 100-109, evaluated once, unchanged).

## Pooled results

| Policy | Split | Dangerous commits | Of which forged-origin | Survivor recall |
|---|---|---|---|---|
| A reporter-count | dev (800 contacts) | 211 | 201 | 0.465 |
| B sighting-ID dedup | dev | 55 | 45 | 0.465 |
| C direct multi-modal | dev | 42 | 33 | 0.3275 |
| A reporter-count | holdout (400 contacts) | 87 | 84 | 0.5024 |
| B sighting-ID dedup | holdout | 23 | 20 | 0.5024 |
| C direct multi-modal | holdout | 16 | 14 | 0.4251 |

## Verdicts against the pre-registered hypotheses

- **H1 confirmed.** Counting reporters is catastrophically
  vulnerable: one forged sighting relayed by three copiers commits
  almost every attacked hazard as a survivor (201 forged-origin
  dangerous commits on dev).
- **H2 falsified.** Deduplicating by sighting ID cuts forged-origin
  commits roughly fourfold, but not to zero: a forged sighting plus
  a single flipped honest sighting still reaches two distinct IDs
  (45 on dev, 20 on holdout). The multi-modal rule (C) reduces
  further (33/14) but also not to zero. Dedup is necessary and
  insufficient - this is the headline result, and it matches the
  field intuition from the rescue DIG rule: copies are not
  witnesses, but one real error can still chaperone a forgery.
- **H3 confirmed.** The multi-modal rule costs 0.1375 recall on dev
  (0.0773 on holdout), inside the pre-registered 0.15 bound, while
  cutting dangerous commits further. Whether that trade is worth it
  depends on sighting rate, which this simulation fixes.

## Gate outcome

No policy is recommended. The pre-registered gate required zero
forged-origin dangerous commits on dev and holdout; B and C fail it.
The honest-error component (dangerous commits with no forged
sighting in the deciding set: 10 on dev under B) also remains, as
expected at 75% per-sighting identify accuracy.

## Next amendment (to be pre-registered before running)

Add a verified-origin policy D: only direct_verified sightings
(signed, via bridge Contract v1 auth status) may decide a commit;
unverified and hearsay reports are advisory only. Forged sightings
are unverified by construction, so D should reach zero forged-origin
commits - at a recall cost to be measured, not assumed.

## Limits

Simulation only: no hardware, no radio, no on-node inference.
Identify accuracy, sighting counts, and adversary rate are fixed
parameters, not fitted to fleet telemetry.
