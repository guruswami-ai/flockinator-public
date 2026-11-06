# Results: stall-triggered explorers (seeds 180-199)

Run under
[stall-explorer-preregistration.md](stall-explorer-preregistration.md),
K8 in the loss-bearing regime. Evidence:
`validation/kulira/stall-explorer-001.json`. Simulation only.

| Arm | Find rate | Turns | Ready end | Lost | Damaged |
|---|---|---|---|---|---|
| Control (never) | 0.869 | 9.2 | 10.8 | 1 | 103 |
| Release at T=30 | 0.825 | 11.0 | 10.5 | 2 | 108 |
| Release at T=60 | 0.869 | 9.2 | 10.8 | 1 | 103 |

- **HS1 falsified.** Neither stall arm is faster; T=30 is
  1.8 turns *slower* with fewer finds. T=60 is identical to
  control on every metric - at a 9.2-turn average find time,
  a 60-turn stall almost never occurs, so the mechanism
  effectively never fires.
- **HS2 falsified for T=30** (find rate -4.4pt beyond the 3pt
  guardrail, one extra loss); vacuous for T=60.
- **HS3 supported trivially** (T=60 loses 1 vs T=30's 2), but
  only because T=60 barely releases anyone.

**The explorer line closes here**, as the pre-registration
committed: always-on explorers failed to replicate
(confirmatory seeds 100-119), and stall-triggered release is
either harmful (T=30) or inert (T=60). In this simulator,
systematic sweep by a right-sized team is simply good, and
the romantic cave-explorer mechanism earns nothing. That is a
finding, and it retires a hypothesis the project framing was
fond of - which is what the falsification discipline is for.
