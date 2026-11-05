# Pre-registration: priority-split graded sensing

Registered before running. Follow-up to graded-sensing, whose
gate failed because a bought second look also raises dangerous
commits. That result proposed testing the split honestly:

## Question

If second looks are bought only for contacts whose commit is
reversible (low priority), while irreversible (high-priority)
contacts keep policy E's abstention, do we keep E's safety where
it matters and E+R's recall where it is cheap?

## Setup (relay-attack world, unchanged otherwise)

- Each contact is assigned priority high/low with p=0.5
  (deterministic per seed+contact).
- Policy F: high-priority contacts use E (abstain on close calls,
  no recheck). Low-priority contacts use E+R (one 90% second look
  on would-abstain contacts, then margin rule once more).
- References: E (all abstain) and E+R (all recheck), from
  graded-sensing, recomputed on identical trials.

## Pre-registered expectations and gate

- H-J1: F's high-priority dangerous commits equal E's
  high-priority dangerous commits exactly (by construction; the
  run verifies no implementation leakage across priorities).
- H-J2: F's overall survivor recall is at least halfway between
  E's and E+R's overall recall on dev and holdout.
- H-J3: F's overall dangerous commits are strictly below E+R's
  on dev and holdout.
- Gate: recommend F as the operating policy if all three hold;
  otherwise report the split as measured.

## Limits

Simulation only. Priority assignment is random here; in a real
scenario priority comes from the director/scenario, and
reversibility is a property of the action a commit triggers,
which this simulation treats as given.
