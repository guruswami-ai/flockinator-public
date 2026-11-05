# Pre-registration: colluding minorities vs policy E

Registered before running. Parent: relay-attack experiments
(policies A-E). Policy E (verified-origin + abstention) stops
unverified forgeries by construction. This experiment attacks its
stated boundary: adversaries that hold valid keys.

## Question

If k of the fleet's verified nodes collude to label hazards as
survivors, at what k does policy E start committing hazards, and
does requiring cross-modality agreement (E + >=2 modalities among
deciding sightings) raise that threshold?

## Setup changes (rest identical to parent)

- 8 verified reporting nodes. k in {0,1,2,3} of them are colluders:
  their sightings of hazard contacts always claim survivor, with
  valid (verified) status and their normal modality.
- Colluders behave honestly on survivor contacts.
- Policies: E (verified + margin>=2 abstention) and E-M (E plus
  >=2 modalities among deciding sightings).
- Seeds dev 0-19, holdout 100-109, 40 contacts/seed, as parent.

## Pre-registered expectations and gate

- H-F1: at k=1, E forged-equivalent dangerous commits (deciding set
  includes a colluder sighting) are zero or near-zero because a
  single colluder cannot reach the margin alone without honest
  agreement. Measured, not assumed.
- H-F2: dangerous commits rise with k; the k at which pooled
  dangerous exceeds 0 on dev is reported as the collusion
  tolerance threshold for each policy.
- H-F3: E-M threshold is >= E threshold (modality diversity never
  hurts tolerance), at some recall cost, reported not hidden.
- No policy is "recommended" against collusion from this run alone;
  the deliverable is the tolerance curve k -> dangerous/recall.

## Limits

Simulation only. Colluders are honest-but-for-label-flip; adaptive
colluders that also manipulate modalities are future work.
