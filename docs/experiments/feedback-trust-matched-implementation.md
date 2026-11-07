# Matched-control implementation (unregistered)

**2026-11-07; supports [#172](https://github.com/guruswami-ai/flockinator-public/issues/172).**
This is a separate implementation of the structural controls in the
[matched-control proposal](feedback-trust-matched-control-proposal.md).
It is **not** protocol acceptance, a registration or a fresh experimental run.
No new seed list, acceptance threshold or scientific result is published here.

[`feedback_matched.py`](../../tools/kulira-core/kulira_core/feedback_matched.py)
accepts one supplied sequence and runs four policies on identical observations
and a single precomputed reveal schedule:

| Arm | Weight updates | Survivor-weight floor | Survivor-minus-hazard margin |
|---|---|---|---|
| L1 | existing REP update/clipping rule | 1.5 | 1 |
| F1 | disabled; weights stay one | 1.5 | 1 |
| L2 | existing REP update/clipping rule | 1.5 | 2 |
| F2 | disabled; weights stay one | 1.5 | 2 |

L1 matches historical REP. F1 matches its frozen-unit decision rule without
removing outcome information. F2 matches E: at unit integer weights the floor
requires two survivor reports, and the margin requires two more survivor than
hazard reports. There is no probation arm or altered admission rule.

## Information and timing

All arms receive the same reports and reveal events. First-occurrence
sighting-ID deduplication, clipping, increments and update order mirror the
historical runner. The implementation precomputes outcome-reveal draws to
prevent branch-dependent random-number consumption. Current truth enters the
pending update queue only **after** all current decisions. Delay zero therefore
first affects the next decision. Frozen arms consume the same events but apply
zero weight updates; freezing does not set availability to zero.

The return value contains shared reveal masks/budgets, each arm's decision log,
weight-update application counts, and final weights explicitly labelled
**after final flush**. Final-flush outcomes are diagnostic and never influence
prior decisions. Application counts include clipped updates that leave the
weight unchanged; they are not measured CPU/energy costs.

## Same-window outputs

The default evaluation window is contacts 30–59 inclusive; a caller may provide
an explicit valid window for deterministic fixtures. Every arm reports the same
hazard/survivor/contact denominators, dangerous commits, true finds, commitments,
abstentions, hazard false-action rate, survivor recall and coverage. Undefined
class rates remain null, never zero.

Paired outputs are L1−F1, L2−F2, L2−L1 and the updating-by-margin interaction
`(L2−F2)−(L1−F1)`. They are sequence-level descriptive values, with **no**
confidence intervals or PASS/FAIL rule. A rate interaction can span `[-2,2]`;
it must not silently reuse a `[-1,1]` paired-difference uncertainty bound.
Threshold effects and updating effects remain separate quantities.

## Compatibility check, not a study command

From the repository root, choose a new output path:

```sh
PYTHONPATH=tools/kulira-core uv run --no-project python -m kulira_core.feedback_matched --historical-smoke --out /tmp/feedback-matched-smoke.json
uv run --project tools/kulira-core --locked pytest tools/kulira-core/test_feedback_matched.py tools/kulira-core/test_feedback_trust.py
```

The CLI has **only** a historical compatibility mode. It checks exposed seeds
220–259 in full and sparse/delayed feedback: 80 sequences and 240 decision-log
comparisons against historical REP, E and frozen REP. Its compact output records
checks, exposed seeds and source hashes, not an experiment result table. Output
paths are never overwritten. There is no default fresh-seed run, experimental
CLI mode, seed-search option or registration shortcut.

Tests enumerate all possible survivor/hazard counts up to eight reports for
F2=E, verify L1 compatibility, frozen truth/feedback invariance, positive
reveal-boundary sensitivity, shared budgets, duplicate admission, same-window
rates, null denominators, pairing and file protection. Historical APIs and
artifacts remain unchanged.

## What still gates a study

Before collecting fresh evidence, the owner must accept the protocol's practical
effect/recall tolerances, uncertainty method, budget and seed-exposure policy.
A separate registration commit must contain the checked seed list and pinned
source/configuration, followed by independent implementation review. A future
collection/analysis command must enforce that reviewed configuration; this
sequence-level building block does not enforce or replace those study-level
gates. Compatibility on exposed seeds is implementation evidence only.
