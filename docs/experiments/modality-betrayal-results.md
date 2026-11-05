# Results: modality betrayal - node trust vs modality trust

Lab simulation, synthetic data only. Pre-registered in
[modality-betrayal-preregistration.md](modality-betrayal-preregistration.md).
Evidence: `validation/kulira/modality-betrayal-001.json`. From
contact 30 of 60, the ir modality inverts; co2 stays honest.
Outcomes are revealed after each contact; trust learns only from
revealed outcomes.

## Post-betrayal results (contacts 30-59)

| Arm | Dev dangerous DIGs (of 313 hazards) | Dev survivor recall | Holdout dangerous (of 162) | Holdout recall | ir discounted |
|---|---|---|---|---|---|
| static | 306 | 0.983 | 162 | 1.000 | never |
| node trust | 104 | 0.314 | 44 | 0.264 | n/a |
| **modality trust** | **69** | **0.902** | **34** | **0.921** | median 3 contacts |
| both (node x modality) | 27 | 0.266 | 8 | 0.207 | median 3 contacts |

## Verdicts

- **H-G1 confirmed.** Static takes near-total damage (306/313);
  every learning arm is far below it, modality/both below node on
  dangerous DIGs.
- **H-G2 confirmed.** Modality trust discounts the lying modality
  fast: ir trust falls below 0.3 a median of 3 contacts after onset,
  in every seed, dev and holdout.
- **H-G3 confirmed, strongly.** Node trust cannot isolate the
  betrayal: it punishes honest co2 readings from the same nodes,
  and survivor recall collapses to ~0.31 (vs 0.90 for modality).
  Blame pooled at the node is blame misdirected.

## Surprise: "both" is worst where it matters

Multiplying node and modality trust gives the fewest dangerous
DIGs (27) - and unusable recall (0.27). The node factor double-
counts the betrayal: once a modality is identified as the liar,
also discounting its carrier nodes throws away their honest
sensors. Defence-in-depth by multiplying trust scores is not
free; it compounds.

## Recommendation from this run

Attach learned trust to **modalities (claims), not reporters**,
where the sensor type is identifiable; keep node identity for
provenance (policy D) but not as the unit of learned distrust.
That pairing - verified origin for admission, modality trust for
weight - is the current best composite from the Kulira experiment
series, pending the same honesty caveat as always: colluding
verified nodes remain an open problem (see colluding minorities).

## Limits

Simulation only; timely revealed outcomes assumed. Delayed or
missing field confirmation would slow the discount - a separate,
pre-registered follow-up.
