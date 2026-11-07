# Host rehearsal: canary parity and loss degradation (pre-hardware)

Status: **host-only rehearsal** of the canary scoring path -
no panel, no radio, no on-node evidence. It exists to prove the
comparator and journal semantics behave before firmware exists,
so a future hardware failure is attributable to the device or
link, not the scoring code. Evidence:
`validation/kulira/canary-host-rehearsal-001.json`. Contract:
[canary-contract-v1.md](canary-contract-v1.md) (v1.1).

## Parity under missing-input loss (seed 80, 500 ticks)

One broadcast input stream; the simulated device journals every
tick, replacing dropped ticks with missing-input rows.

| Drop rate | Parity | Missing rows | Hash mismatches |
|---|---|---|---|
| 0 | 1.000 | 0 | 0 |
| 5% | 1.000 | ~25 | 0 |
| 10% | 1.000 | ~50 | 0 |
| 20% | 1.000 | ~100 | 0 |

Parity stays exactly 1.0 at every loss level, with loss visible
only as counted missing-input rows - the v1.1 semantics working
as registered. (An earlier modelling attempt that gave the
device a different loss stream produced parity 0.81-0.96; that
model was wrong - the device is scored on the stream it
received - and was replaced before publication. The numbers
above are from the corrected model in the evidence script
lineage; the comparator also has unit tests for the
missing-row and non-WAIT negative cases.)

## Mission degradation in the sim loop (seed 42)

| Drop fraction | Found at tick | Missing rows journaled |
|---|---|---|
| 0 | 149 | 0 |
| 10% | 163 | 14 |
| 25% | 191 | 42 |
| 50% | 283 | 134 |

Graceful, monotonic degradation: the search still completes at
50% tick loss inside the budget, and every lost tick is
accounted in the journal. This is the behaviour the canary's
H2 gate will look for on hardware, at the registered 10%/20%
levels.

## What this does not prove

Nothing about the ESP32: not its decision latency, not its
journal write reliability, not real radio loss. Those are the
canary's hardware gates, owned by the firmware side. This
rehearsal only removes the scoring code from the list of
suspects when hardware results arrive.
