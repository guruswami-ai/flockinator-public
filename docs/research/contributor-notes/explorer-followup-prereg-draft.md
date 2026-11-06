<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Confirmatory Pre-registration: Team-8 + 1 Explorer (Sim Only)

**Context:** Seeded virtual-world search sim (lost hiker). Loss-bearing regime. Pilot: team-8, 0 explorers = 74.4% found / 11.8 turns; 1 explorer = 76.9% / 9.4 turns; 2 and 4 explorers worse on find rate. Team-14 worse with explorers on all metrics — out of scope here.

**Registered:** 2026-11-06. Simulated data only. No real hardware in this test.

### 1. Hypotheses
- **H1 PRIMARY - time-to-find:** Team-8 with exactly 1 explorer finds *faster* than Team-8 with 0 explorers.
  - Metric: mean turns-to-find **conditional on success** within cap, averaged per-seed over 8 searches.
- **H2 SECONDARY - find rate:** Team-8 with 1 explorer is non-inferior on find rate.
  - Metric: found / attempted per-seed.

### 2. Falsification conditions
- H1 **falsified** if: paired mean difference (Control - Treatment) <= 0.5 turns OR one-tailed paired p >= 0.05.
- H2 **fails** if: Treatment - Control find rate < 0, with lower 95% CI < -5pp.
- Any `seed x condition` omitted, re-run, or code change = protocol violation, report as exploratory.

### 3. Frozen parameters
- Team: 8 panels + 1 controller. Control: 8 exploiters. Treatment: 7 exploiters + **exactly 1 explorer**.
- Regime: loss-bearing (freeze current loss / battery / comms model, no tuning).
- Workload: 8 searches/day per seed.
- Horizon: 24 turns/search max. Failure = not found by 24.
- Policies: freeze exploiter greedy + explorer Levy/random commit hash; map 32x32, same hiker distribution.
- No parameter sweeps in this registration.

### 4. Seeds & pairing — fresh
- Seeds **100-119 inclusive (n=20, fresh, never run)**.
- Paired by seed: for each `s`, run Control(s) and Treatment(s) with identical hiker placement + world RNG substream. Total: 20 pairs = 160 searches/arm.
- Pre-spec sensitivity: repeat primary with failures scored as 24 turns.

### 5. Analysis plan (paired by seed)
1. Per seed compute: `T_c(s), T_t(s)` and `F_c(s), F_t(s)`.
2. Primary: `dT(s)=T_c - T_t`. One-tailed paired t-test, alpha=0.05, + Cohen's dz + two-sided 95% CI. Wilcoxon signed-rank as robustness.
3. Secondary: `dF(s)=F_t - F_c`. Two-tailed paired t-test + 95% CI for non-inferiority (-5pp margin).
4. Report all 40 runs, SDs, and failure counts. No subgroup / seed-dropping.

### 6. Gate to real panel hardware
Test on real 8x ESP32 panels **only if ALL met**:
1. H1 confirmed: mean dT >=1.0 turn reduction, p<0.05.
2. H2 guardrail passed: lower 95% CI of dF > -5pp (no meaningful loss in finds).
3. No sim crashes / message storms.

Otherwise: stay in sim, do not proceed to hardware.
