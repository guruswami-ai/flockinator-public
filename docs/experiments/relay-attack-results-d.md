# Results (amendment): policy D, verified-origin only

Lab simulation, synthetic data only. Pre-registered in
[relay-attack-amendment-d.md](relay-attack-amendment-d.md) before
running. Evidence: `validation/kulira/relay-attack-d-001.json`.
Parent experiment: [relay-attack-results.md](relay-attack-results.md).

## Pooled results

| Policy | Split | Dangerous | Forged-origin | Survivor recall |
|---|---|---|---|---|
| B sighting-ID dedup | dev (800) | 55 | 45 | 0.465 |
| C direct multi-modal | dev | 42 | 33 | 0.3275 |
| **D direct-verified only** | dev | **17** | **0** | **0.465** |
| B sighting-ID dedup | holdout (400) | 23 | 20 | 0.5024 |
| C direct multi-modal | holdout | 16 | 14 | 0.4251 |
| **D direct-verified only** | holdout | **9** | **0** | **0.5024** |

## Verdicts

- **H-D1 confirmed** on both splits: zero forged-origin dangerous
  commits. The forged sighting and its relays are unverified or
  hearsay under bridge Contract v1, so they never enter the
  deciding pool.
- **H-D2 confirmed:** D recall equals B recall exactly on both
  splits - excluding the adversary costs no survivor recall here,
  because the adversary only attacks hazard contacts.
- **H-D3 confirmed:** D total dangerous commits (17 dev / 9 holdout)
  are strictly below B's. The remainder is honest error: at 75%
  per-sighting identify accuracy, two flipped honest sightings can
  still commit a hazard. D fixes *provenance*, not *accuracy*.

## Gate outcome

Policy D passes the pre-registered recommendation gate (zero
forged-origin on dev and holdout; recall within 0.02 of B) and is
**recommended over B and C** for the deciding rule, with the
multi-modal requirement of C retained where modalities exist as an
additional cost/benefit choice, not a safety requirement.

The remaining dangerous error is an accuracy problem, addressed by
the already-named levers - graded sensing and explicit abstention -
not by corroboration rules.

## Limits

Simulation only; the forged sighting is unverified by construction
in this model. A real adversary holding a stolen valid key is a
different threat (key compromise), handled by provisioning and
rotation, not by this rule.
