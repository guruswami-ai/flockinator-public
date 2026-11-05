# Results: graded sensing - buy a second look at close calls

Lab simulation, synthetic data only. Pre-registered in
[graded-sensing-preregistration.md](graded-sensing-preregistration.md).
Evidence: `validation/kulira/graded-sensing-001.json`. Policy
E+R: where policy E would abstain, buy one extra direct sighting
at 90% identify accuracy from a fresh node, then reapply the
margin rule once.

## Pooled results

| Policy | Split | Dangerous | Survivor recall | Rechecks/contact |
|---|---|---|---|---|
| E abstain | dev (800) | 5 | 0.3225 | 0 |
| E+R second look | dev | 7 | 0.6825 | 0.46 |
| E abstain | holdout (400) | 4 | 0.343 | 0 |
| E+R second look | holdout | 9 | 0.6812 | 0.48 |

## Verdicts

- **H-I1 falsified.** The second look more than doubles survivor
  recall, but dangerous commits rise (5 -> 7 dev, 4 -> 9 holdout).
  A 90%-accurate extra sighting still flips 10% of the time, and
  on hazards with one flipped honest sighting already present, it
  can supply the deciding vote. Better evidence is not free of
  the original sin: it is still a single sighting.
- **H-I2 partly met on its own terms** (recall +0.36, recheck rate
  0.46-0.48 within budget), but the gate requires both hypotheses.

## Gate outcome

E+R is **not recommended** over E under the safety-first gate.
The recall is real and large; so is the direction of the
dangerous error. Where the dangerous direction must stay at the
abstention floor, operator review of the Unassessed queue (E)
remains the recommendation, and graded sensing is a recall tool
for lower-stakes contacts only - a per-priority split the next
amendment could test honestly: second looks allowed except where
a commit would be irreversible.

## Reading

This is the abstention trade from the other side. E spends human
attention; E+R spends energy and accepts a few more dangerous
errors. The experiment's value is pricing both: ~0.46 extra
sightings per contact buys +0.36 recall at +2 to +5 dangerous
commits per 800/400 contacts at these parameters.

## Limits

Simulation only; 90% second-look accuracy and sighting costs are
chosen parameters, not node telemetry.
