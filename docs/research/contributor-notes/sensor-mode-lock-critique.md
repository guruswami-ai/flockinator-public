<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Verdict: Intent OK, not lock-ready

Good: paired seeds, ordered difficulty SM1 -> SM3, explicit gate after panel-policy canary, no run authorized yet. Do not lock any of them now.

## What's actually frozen

- Seed blocks: SM1 120-139, SM2 140-159, SM3 160-179. `n=20` / arm.
- Directional claims + falsification sentences.
- Gate order: canary first, SM3 needs `EVENT` frame in `kulira_core/simwire.py`.

That's it. Everything else is unfrozen.

## Unfrozen parameters

**World (all SM):** map size, hiker motion, start / spread of 16 nodes, `T_max` per search, Day/Night lighting rule, per-mode `p_detect / p_false-alarm / range`, movement speed. Without this SM1 "diversity wins" is uninterpretable.

**SM1:** 5 modes listed (Day, White-Hot, Black-Hot, Night, IR) but `4/4/4/4` = 4 modes. Which 4? Which node IDs get which? Fixed layout or randomized? Switching "disabled" - enforced where?

**SM2:** Switching policy itself not frozen. Who decides to switch? What threshold? What counts as 1 switch? What happens in 10-tick blackout - blind, frozen, can still move? 10 ticks out of what `T_max`? `>20% slower` - mean or median? Paired or unpaired?

**SM3:** Which mode is degraded? At tick 0 or mid-search tick `t_deg`? `95% -> 30%` - per-look? False alarms `up` from what to what exact numbers? What is "leaving" - switch within `K` ticks? Denominator - only nodes that started degraded? Broadcast wording / timing / retry? Control = same 20 seeds with no degradation?

**Metrics (all):** `mean turns-to-find` with failures? If not-found, censored at `T_max` or excluded? Find rate denominator? No alpha, no test (paired t? Wilcoxon signed-rank?), no handling of ties / node dropouts. With `n=20` paired, power is low - no MDE stated.

## Depends on unfinished systems

1. **Live shared-world + local decision:** SMs require nodes deciding locally. Not built yet - currently controller-driven.
2. **Panel-policy canary:** parity + journal-completeness gates have no thresholds. e.g. parity delta `< ?`, completeness `100%? 99%?`
3. **SIM wire `EVENT` frame:** SM3 broadcast has nowhere to ride yet. Reference is `kulira_core/simwire.py` only.
4. **Director degradation injection + cost enforcement:** 10-tick blackout and `95->30` downgrade have no implementation / owner except "Drishdi-owned planner/firmware."
5. **Logging:** journal schema, switch receipts, broadcast receipts not pinned. Can't measure "fraction leaving" without it.

## What a reviewer would block on

- Mode-count mismatch (5 vs 4) - must fix assignment matrix.
- No `T_max` / censoring rule - mean turns is undefined.
- No frozen switching policy - SM2/SM3 will just measure thrash of an unknown policy.
- SM3 falsification is broken: `find rate equals control despite leaving = theatre` could also = robustness. Split into H3a (leave) + H3b (leave helps).
- No firmware / policy / world-config hash pinning.
- No exclusion rules: panel crash, WiFi loss, straggler >?ms, incomplete journal.
- Gate thresholds missing - canary can never formally "pass."

## Lock checklists

**SM1 - Diversity vs uniformity**
- [ ] World freeze: map, hiker model, `T_max`, per-mode sensor table, lighting
- [ ] Fix 4/4/4/4 mapping: which 4 modes, node-ID -> mode table, spatial layout
- [ ] Switching lock: disabled in firmware, verified in logs (0 switches)
- [ ] Firmware + panel-policy + world-config hashes recorded
- [ ] Canary gates passed with numbers: parity delta, journal completeness %
- [ ] Stats frozen: paired test, one/two-sided, alpha, MDE for n=20, failure handling (e.g. not-found = `T_max` + penalty)
- [ ] Logs required: per-search turns, found/not, journal IDs
- [ ] Falsification rewrite: `Diverse faster OR higher find rate` -> specify AND/OR + test per metric

**SM2 - Switching cost**
- [ ] All SM1 items, plus:
- [ ] Freeze base switching policy (thresholds, cooldown, hysteresis)
- [ ] Freeze cost semantics: 10-tick blackout = no sense + can/can't move, who enforces (controller vs node), tick definition
- [ ] Freeze counting: what is 1 switch, initial assignment excluded, blackout-overlapping switches
- [ ] Freeze comparison: same 20 seeds paired free vs costly, `% slower` defined on median paired difference + CI
- [ ] Falsification split: H2a switches reduced (test), H2b slowdown `<=20%` (equivalence bound)

**SM3 - Trust after degradation**
- [ ] All SM1/SM2 items, plus:
- [ ] Freeze degradation: target mode, `t_deg`, exact `p_detect` 0.95->0.30 definition, `p_fa` from->to exact, range change or not
- [ ] Freeze `EVENT` frame: format in `simwire.py`, broadcast tick, payload text, receipt logging per node
- [ ] Freeze leaving definition: e.g. nodes starting degraded that switch within `K` ticks, denominator = `n_degraded_start`
- [ ] Freeze control: same seeds 160-179 no-degradation replay, same assignments
- [ ] Split hypotheses: H3a `>50%` leave (binomial test vs 0.5), H3b leaving improves find rate vs stay (not vs control alone)
- [ ] Manipulation check: `% EVENT receipts` logged, exclude non-receipts per pre-rule
