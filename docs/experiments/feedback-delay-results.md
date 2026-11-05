# Results: delayed and missing outcome feedback

Lab simulation, synthetic data only. Pre-registered in
[feedback-delay-preregistration.md](feedback-delay-preregistration.md).
Evidence: `validation/kulira/feedback-delay-001.json`. World
identical to [modality-betrayal](modality-betrayal-results.md)
(ir inverts at contact 30); only the teaching feedback changes.

## Post-betrayal results (modality-trust arm)

| Feedback | Dev dangerous (of 285 hazards) | Dev recall | Median contacts to discount ir | Holdout dangerous (of 164) | Holdout median discount |
|---|---|---|---|---|---|
| d0, none missing | 62 | 0.919 | 2 | 41 | 2 |
| d5, none missing | 85 | 0.906 | 7 | 55 | 7 |
| d5, 50% missing | 95 | 0.910 | 10 | 61 | 11 |
| d15, none missing | 155 | 0.907 | 17 | 96 | 17 |
| d15, 50% missing | 171 | 0.884 | 20 | 105 | 21 |

Reference: the static (no-learning) arm in the parent experiment
took 306 dangerous DIGs on dev. Random streams differ slightly
between the two implementations (feedback draws consume the seeded
stream), so that comparison is directional, not paired.

## Verdicts

- **H-H1 confirmed.** Discount time tracks delay almost one-for-one
  (median 2 -> 17 contacts at d15): the swarm cannot distrust a
  sensor faster than the truth arrives. Missing feedback adds a
  few more contacts on top.
- **H-H2 confirmed.** Even at d15 with half of all outcomes missing,
  dangerous DIGs (171) stay well below the static reference (306).
  Degraded learning is still learning.
- **H-H3 confirmed.** Recall barely moves (0.88-0.92 in all
  conditions): late feedback costs safety during the window before
  discount, not survivor-finding overall. The damage is a
  *window*, sized by feedback latency.

## Reading

The operational variable is feedback latency. Every contact of
delay is roughly a contact of exposure to a betrayed modality.
Systems that report outcomes slowly (or lose half of them) do not
need better trust maths nearly as much as they need faster,
more complete ground-truth return - an argument for investing in
the confirmation channel before the corroboration rule.

## Limits

Simulation only; delay/missingness are chosen parameters, not
field-measured timings.
