# Results: behavioural reputation vs verified colluders

Lab simulation, synthetic data only. Pre-registered in
[reputation-defence-preregistration.md](reputation-defence-preregistration.md).
Evidence: `validation/kulira/reputation-defence-001.json`. Two of
eight verified nodes lie on every hazard they sight.

## Results

| Policy | Split | Dangerous, contacts 0-29 | Dangerous, contacts 30-59 | Survivor recall | Mean reputation: colluders vs honest |
|---|---|---|---|---|---|
| E unweighted | dev (1200 contacts) | 37 | 36 | 0.487 | - |
| **REP reputation-weighted** | dev | 39 | **19** | 0.413 | **0.136 vs 0.752** |
| E unweighted | holdout (600) | 15 | 30 | 0.534 | - |
| **REP reputation-weighted** | holdout | 20 | **10** | 0.455 | **0.160 vs 0.722** |

## Verdicts

- **H-L1 confirmed.** Once reputation has history, dangerous
  commits fall by roughly half (dev) to two-thirds (holdout)
  versus the unweighted policy - 36 -> 19 and 30 -> 10 in the
  second half.
- **H-L2 confirmed.** Recall cost is 0.07-0.08, inside the
  pre-registered 0.15 bound.
- **H-L3 confirmed strongly.** Reputation separates the
  populations: colluders end at ~0.14-0.16, honest nodes at
  ~0.72-0.75. The mechanism is visible, not inferred.

## The honest caveat: reputation has a childhood

In the first 30 contacts REP is slightly *worse* than E
(39 vs 37 dev; 20 vs 15 holdout). Before outcomes accumulate,
reputation weights are noise, and weighting by noise perturbs
margins randomly. Behavioural defences protect the future, not
the present: a swarm is most exposed to a verified insider early,
before anyone has a track record. Cold-start remains a design
problem (probationary weighting, slower trust accrual, abstention
until reputations stabilise - all testable follow-ups).

## Gate outcome

REP passes its gate and is recommended as an **additional layer**
over the composite stack (admission by provenance, margin +
abstention, modality trust), specifically as the first measured
defence in this series that acts on verified collusion - the
exposure the earlier policies stated but could not address.
It does not eliminate colluder damage (19-20 dangerous commits
remain in the second half); it suppresses it over time.

## Limits

Simulation only. Colluders keep fixed identities; an adversary
that rotates identities (Sybil) defeats reputation accrual by
construction and is out of scope.
