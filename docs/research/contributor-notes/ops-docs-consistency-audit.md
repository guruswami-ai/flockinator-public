<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Audit scope

Provided:
- `index` — Fleet-commitment experiments: index and synthesis
- `operations-binding-results.md` — Results: binding-regime commitment and reserve (seeds 20-39)

Not provided — not audited, no claims made:
`operations-reserve-dev-results.md`, `operations-loss-bearing-results.md`, `explorer-fraction-results.md`, `explorer-confirmatory-results.md`, `operations-binding-preregistration.md`, `validation/kulira/operations-binding-001.json`

Simulation-only framing is consistent in both docs.

## Discrepancies

**1. `operations-binding-results.md` dominance claim vs its own table — `Ready before inc 2`**
- Text: "K14 dominates K16 on every reported axis except turns-to-find."
- Table:
  - K14 park 2: Find 0.981, Turns 6.1, Ready end 14.55, **Ready inc2 15.90**, Ready inc5 15.55, Damaged 29, Lost 0, Unattempted 0
  - K16 launch all: Find 0.938, Turns 5.6, Ready end 14.55, **Ready inc2 15.95**, Ready inc5 15.30, Damaged 29, Lost 0, Unattempted 0
- K14 is *worse* on Ready inc2 (15.90 < 15.95) and tied on Ready end, Damaged, Lost, Unattempted. Cannot be "dominates on every axis except turns-to-find."

**2. `operations-binding-results.md` Pareto claim underspecified / inconsistent**
- Text: "Pareto frontier: **ESC and K8**."
- Table on Find rate (higher better) / Turns-to-find (lower better):
  - K8: 0.994 / 11.0
  - K14: 0.981 / 6.1
  - ESC: 0.981 / 17.0
  - K16: 0.938 / 5.6
- ESC is dominated by K14 on those two axes (same find, 17.0 vs 6.1) and by K8 (lower find, slower). ESC is only best on `Ready end` (14.75). No Pareto axes defined in doc. Requires correction to state axes or revise frontier.

## Checks passed — no discrepancy

- **Seeds:** index lists Binding as `20-39`; results header lists `seeds 20-39`. Match.
- **Headline numbers:** index "0.938 vs 0.981" matches table K16 0.938, K14 0.981.
- **Regime:** index "8 incidents, recharge +4, damage grounds for window" matches results "8 incidents, 160 daylight turns, recharge +4, damage grounds for rest of window."
- **Seed reuse:** index ranges 0-19, 20-39, 40-59, 60-79, 100-119 show no overlap. Gap 80-99 unexplained but not reuse. No reuse detected in provided docs.
- **HB1/HB2/HB4 text vs table:** Ready inc5 ~15.3-15.6, Lost/Unattempted 0/0 for K14/K16, ESC Unattempted 2 (most), ESC Ready end 14.75 (most) all match table.
