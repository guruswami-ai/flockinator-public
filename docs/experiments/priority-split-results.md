# Results: priority-split graded sensing (policy F)

Lab simulation, synthetic data only. Pre-registered in
[priority-split-preregistration.md](priority-split-preregistration.md).
Evidence: `validation/kulira/priority-split-001.json`.
F: high-priority contacts use E (abstain), low-priority use E+R
(bought second look). E and E+R recomputed on identical trials.

## Pooled results

| Policy | Split | Dangerous | of which high-priority | Survivor recall |
|---|---|---|---|---|
| E | dev (800) | 5 | 3 | 0.3225 |
| E+R | dev | 7 | 4 | 0.6825 |
| **F split** | dev | **6** | **3** | **0.5275** |
| E | holdout (400) | 4 | 2 | 0.343 |
| E+R | holdout | 9 | 6 | 0.6812 |
| **F split** | holdout | **5** | **2** | **0.5121** |

## Verdicts

- **H-J1 confirmed exactly:** F's high-priority dangerous commits
  equal E's on both splits (3 and 2). No recheck ever touches an
  irreversible contact; the implementation leaks nothing across
  the split.
- **H-J2 confirmed, marginally on holdout:** F recall (0.5275 dev)
  sits above the E/E+R midpoint (0.5025). On holdout F lands
  exactly on the midpoint (0.5121 vs 0.5121) - the halfway promise
  is met, with no margin to spare.
- **H-J3 confirmed:** F's overall dangerous (6/5) is strictly
  below full recheck E+R (7/9) on both splits.

## Gate outcome

Policy F passes its pre-registered gate and is recommended as
the operating policy *where priority/reversibility is known per
contact*: E's safety on irreversible commits, most of E+R's
recall on reversible ones. The extra dangerous commits F accepts
over E (one per split) occur only on low-priority contacts, by
design and now by measurement.

## Reading

This closes the abstention arc with a usable composite:
D (verified origin) for admission, E (abstain) where a commit is
irreversible, bought second looks where it is not, modality trust
for weighting, and an operator queue sized by the Unassessed rate.
Each element was measured separately before being combined.

## Limits

Simulation only. Priority here is random; in deployment it comes
from the scenario, and reversibility is a property of the action
a commit triggers.
