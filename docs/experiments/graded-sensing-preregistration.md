# Pre-registration: graded sensing - buy a second look at close calls

Registered before running. Follow-up to policy E (abstention):
E converts narrow-margin contacts into Unassessed workload.
This experiment spends energy instead of operator attention.

## Question

When verified evidence is too close to commit, does one extra,
better sighting (a closer/longer look) recover most of the recall
E gives up, without reopening the dangerous door?

## Setup (relay-attack world, unchanged otherwise)

- Trials exactly as the relay-attack parent (policies' world:
  honest direct sightings at 75% identify accuracy, Kulira forged
  sighting + relays on hazards with p=0.5).
- Policy E as reference. Policy E+R: when E would abstain on a
  contact that has at least one survivor-labelled deciding
  sighting, the swarm buys ONE extra direct sighting from a node
  not already in the deciding pool, at 90% identify accuracy
  (modality drawn at random). Then the E margin rule is applied
  once more. Forged/hearsay reports still never decide (policy D
  pool throughout).
- Energy proxy: rechecks per contact and total extra sightings.

## Pre-registered expectations and gate

- H-I1: E+R dangerous commits <= E's on dev and holdout
  (the extra look must not reopen forged/honest dangerous commits
  beyond E's abstention floor by more than zero net).
- H-I2: E+R survivor recall exceeds E's by at least 0.10 on dev,
  at a recheck rate of at most 0.5 extra sightings per contact.
- Gate: recommend E+R over E if H-I1 and H-I2 both hold on dev
  and holdout direction agrees. Otherwise E stands.

## Limits

Simulation only. The 90% second-look accuracy and unit energy
cost are chosen parameters, not fitted from node telemetry;
on-node graded sensing (dwell/range) is the hardware analogue.
