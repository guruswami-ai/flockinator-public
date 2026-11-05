# Amendment: policy D (verified-origin) - registered before running

Follows the relay-attack results (H2 falsified: sighting-ID dedup
alone cannot reach zero forged-origin commits). This amendment adds
one policy; the original setup, seeds, and metrics are unchanged.

## Policy D: direct-verified only

Only direct_verified sightings may decide a commit (bridge Contract
v1 auth status: signed origin report, not forwarded, not unverified).
Unverified and hearsay_relayed reports are advisory only and never
enter the deciding pool. Within the deciding pool, sightings are
deduplicated by sighting ID; commit survivor when survivor-labelled
deciding sightings are >=2 and outnumber hazard-labelled ones.

In the simulation, honest node sightings are direct_verified; the
forged Kulira sighting and its relayed copies are unverified/hearsay
by construction (no valid key), so they are excluded before counting.

## Pre-registered expectations and gate

- H-D1: policy D admits zero forged-origin dangerous commits on dev
  (seeds 0-19) and holdout (seeds 100-109). This is expected by
  construction; the run verifies the implementation enforces it.
- H-D2: D survivor recall equals B (dedup) recall, because the
  adversary only attacks hazard contacts.
- H-D3: D total dangerous commits are strictly below B's, the
  remainder being honest-error commits only.
- Recommendation gate: recommend D over B/C if H-D1 holds on both
  splits and D recall is no more than 0.02 below B's on either split.
  Honest-error dangerous commits are reported, not hidden; D does
  not claim to fix identify accuracy.

## Limits

Same simulation limits as the parent experiment: fixed parameters,
no hardware, no radio, no on-node inference.
