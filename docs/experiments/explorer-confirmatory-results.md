# Results: explorer confirmatory, K8 + 1 explorer (seeds 100-119)

Run under
[explorer-confirmatory-preregistration.md](explorer-confirmatory-preregistration.md).
Evidence: `validation/kulira/explorer-confirmatory-001.json`.
Simulation only.

| Arm | Find rate | Mean turns | Ready end | Lost |
|---|---|---|---|---|
| K8, no explorer | 0.800 | 11.74 | 10.25 | 2 |
| K8, 1 explorer | 0.644 | 11.89 | 9.95 | 3 |

**HC1 falsified.** The paired time difference is +0.14 turns
(explorer *slower*, threshold was >=1.0 turn faster), and the
find-rate guardrail also fails (0.644 vs 0.800, far beyond the
3pt allowance). The dev-split explorer benefit (seeds 60-79:
+2.5pt, -2.4 turns) **did not replicate** on fresh seeds.

Conclusion: there is currently no evidence that a single
explorer improves a committed-8 search in this simulator, and
the confirmatory result removes the basis for proposing it as
the live-test starting configuration. The interesting dev-split
signal was most likely seed variance - exactly what the
confirmatory split exists to catch. Any future explorer test
needs a different mechanism (e.g. explorers dispatched only
after the systematic sweep stalls) registered from scratch.
