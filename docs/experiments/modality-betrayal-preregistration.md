# Pre-registration: modality betrayal - node trust vs modality trust

Registered before running. Catalogue rescue family #2.

## Question

Halfway through a run, one sensing modality (thermal/IR) starts
lying - it reports anomalies on hazards and goes quiet on
survivors - while other modalities stay honest. Can a swarm learn
to distrust the *modality* without distrusting the *nodes* that
also carry honest sensors?

## Setup (lab simulation, synthetic only)

- 60 sequential contacts per seed; survivor/hazard p=0.5.
- Each contact is read by 2 nodes, each reporting 2 modalities
  (ir, co2): a modality reads "anomalous" for a survivor with
  p=0.85, for a hazard with p=0.10 (honest regime).
- From contact 30 onward (betrayal onset, Kulira-controlled), ir
  inverts: survivor p=0.10, hazard p=0.85. co2 stays honest.
- After each contact the outcome is revealed (field confirmation:
  crews dig or clear the point), so trust can be updated from
  revealed outcomes - never from the swarm's own commits.
- DIG rule: weighted anomalous votes >= 1.0, where each anomalous
  reading votes with its arm's trust weight; absent readings vote 0.

## Arms

- **static:** all weights 1.0 forever (no learning).
- **node:** one trust per node (pooled across its modalities),
  updated after each revealed outcome: agreement +0.1, disagreement
  -0.15, clamped [0.05, 1.0]. A reading agrees if anomalous matches
  survivor truth.
- **modality:** one trust per modality, same update.
- **both:** weight = node trust x modality trust.

## Pre-registered expectations

- H-G1: post-betrayal dangerous DIGs (DIG on hazard, contacts
  30-59) are highest in static, and modality/both are below node.
- H-G2: in modality and both arms, ir trust falls below 0.3 within
  15 contacts of onset (median over seeds).
- H-G3: node arm cannot isolate the betrayal: its post-betrayal
  survivor recall falls at least 0.10 below modality arm's, because
  honest co2 readings from the same nodes are discounted too.
- Deliverable: post-betrayal dangerous DIGs + survivor recall per
  arm, and time-to-discount for ir. No deployment recommendation
  from simulation alone.

## Limits

Simulation only. Revealed-outcome feedback is assumed timely; in
the field it is delayed and sometimes missing - that delay is a
separate experiment.
