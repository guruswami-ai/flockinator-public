# Amendment: policy E (verified-origin + explicit abstention)

Registered before running. Builds on policy D (direct-verified only,
zero forged-origin commits; remaining error is honest mislabelling).

## Policy E

Deciding pool as in D (direct_verified sightings, deduplicated by
sighting ID). Commit survivor only when the evidence is not close:
survivor-labelled deciding sightings >= 2 **and** survivor count
minus hazard count >= 2. Otherwise the contact is left explicitly
**Unassessed** for a human/operator - not committed either way.

Rationale: when verified witnesses disagree narrowly, the swarm's
honest answer is "we do not know", and a forced binary commit is
where the remaining dangerous errors live.

## Pre-registered expectations and gate

- H-E1: E total dangerous commits are strictly below D's on dev
  (seeds 0-19) and holdout (seeds 100-109); forged-origin stays 0.
- H-E2: E survivor recall drop vs D is at most 0.20 on either split
  (abstention is expected to cost recall; more than 0.20 is too much).
- Recommendation gate: recommend E over D if dangerous commits fall
  by at least 30% vs D on dev with holdout not worse than D, and
  H-E2 holds. Otherwise D remains the recommendation and E is
  reported as measured.

## Metrics

As before, plus Unassessed rate per split (contacts neither
committed survivor nor counted safe - reported, not hidden).

## Limits

Same simulation limits as the parent experiment.
