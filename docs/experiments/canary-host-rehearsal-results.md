# Host rehearsal: canary parity and loss accounting (pre-hardware)

Status: **host-only rehearsal** of the canary scoring path -
no panel, no radio, no on-node evidence. It exercises the
comparator and journal semantics on host-generated journals
before firmware exists. It is a self-comparison: the "device"
rows are the host rows with dropped ticks replaced by
missing-input markers, so it checks that the comparator applies
the contract to a conformant journal. It is not independent
device execution and does not by itself clear the scoring code
(see "What this does not prove"). Evidence:
`validation/kulira/canary-host-rehearsal-001.json` (archived
unmodified). Contract:
[canary-contract-v1.md](canary-contract-v1.md) (v1.1).

## Parity under missing-input loss (seed 80, 500 ticks)

One broadcast input stream; the simulated device journals every
tick, replacing dropped ticks with missing-input rows. The counts
below are the archived values from the evidence JSON; the drop
rate is the nominal per-tick rate requested, and the realised
missing rows (21/38/79 of 500) are what that run produced.

| Drop rate (nominal) | Parity | Missing rows | Hash mismatches (as recorded) |
|---|---|---|---|
| 0 | 1.000 | 0 | 0 |
| 5% | 1.000 | 21 | 21 |
| 10% | 1.000 | 38 | 38 |
| 20% | 1.000 | 79 | 79 |

Parity is 1.000 at every level: under v1.1 a missing-input row
that journals WAIT counts as agreement, and every non-missing row
matches because both journals come from the same host run. The
recorded `hash_mismatches` column equals the missing-row count
because the comparator code published with this file (PR #141,
`dcd9c01`) counted the canonical missing-input marker as a hash
mismatch, which the contract's v1.1 clause ("never hash
mismatches") does not allow. That diagnostic defect is issue
#143, fixed in PR #145; see the dated correction below. The
recorded `decision_mismatches` (0/19/33/72) fall on those same
missing rows, where the host decided on input the device did not
receive while the device journaled WAIT.

The producing script was not published with the evidence. PR #152
later added
[`validation/kulira/canary-host-rehearsal-recipe.py`](../../validation/kulira/canary-host-rehearsal-recipe.py)
(issue #151), whose docstring describes it as the original script
preserved with its mask construction. Run from the repository
root:

```sh
uv run --project tools/kulira-core python validation/kulira/canary-host-rehearsal-recipe.py
```

It regenerates the parity, missing-row and sim-loop values above
and checks them against the archived JSON; it does not regenerate
the recorded `hash_mismatches`, which predate the #143 fix. The
`distribution_sweep` block also regenerates exactly from
`twin.distribution_sweep(80, 2000)`. Matching numbers show that
the recipe reproduces the archived values; that it is the
original run rests on its author's statement, not on an
independent record. (An earlier modelling attempt that gave the
device a different loss stream produced parity 0.81-0.96; that
model was wrong - the device is scored on the stream it received
- and was replaced before publication. The comparator has unit
tests for the missing-row and non-WAIT negative cases.)

## Hold-on-loss accounting in the sim loop (seed 42, one drop pattern)

| Drop fraction | Found at tick | Missing rows journaled |
|---|---|---|
| 0 | 149 | 0 |
| 10% | 163 | 14 |
| 25% | 191 | 42 |
| 50% | 283 | 134 |

In this loop a dropped tick is a hold: the robot does not move
and journals a missing-input row, so each dropped tick delays
completion by one tick (found tick minus missing rows is 149 at
every level). This is a one-seed, one-drop-pattern accounting
observation on the host, not a general robustness result. The
canary's registered H2 gate
([pre-registration](panel-policy-canary-preregistration.md))
scores parity, crash-free operation and timeout-to-WAIT on
hardware at 10%/20% loss; found-at-tick is not one of its
quantities.

## What this does not prove

Nothing about the ESP32: not its decision latency, not its
journal write reliability, not real radio loss. Those are the
canary's hardware gates, owned by the firmware side. This
rehearsal shows that the comparator accepts a contract-conformant
host journal and reports loss as missing-input rows. It does not
clear the scoring path on its own: the comparator does not see
the injected drop mask, so genuine loss and device-labelled
missing rows look the same to it, and that accounting belongs to
the pre-registration's drop-rate audit, not to parity.

**Correction (2026-11-07, issues #143/#144):** the evidence JSON
above recorded `hash_mismatches` 21/38/79 at the three loss
levels; those counts wrongly included canonical missing-input
markers. With the comparator fixed, hash mismatches are 0 at
every level (missing rows are diagnosed as missing, not
corruption) and parity values are unchanged (1.000). The
original JSON is preserved unmodified as the record of what
was first published; this note is the dated correction. The
comparator now also enforces the v1.1 link-failure cutoff
(>50% missing -> `link_failure`, no numerical parity), and the
SIM receiver has an explicit management-authorized `reset()`
for new runs - wire frames alone never reset the replay
watermark.
