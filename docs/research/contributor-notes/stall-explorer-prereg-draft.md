<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Pre-registration: Stall-Triggered Explorers v1.0
**Simulated data only.** Seeded virtual-world search for lost hiker. 16x ESP32 panels = 16 robots, 1x controller = sweep orchestrator.

**Background:** Always-on explorers did not reduce time-to-find. Confirmatory run falsified benefit. New test: systematic sweep by default, explore only on stall.

### Frozen parameters
- Regime: **loss-bearing**
- Searches/day: **8**
- Fault rate: **0.01 / robot / tick**
- Seeds: **180-199** (n=20, paired across conditions = 60 runs)
- World, hiker policy, sensor noise, sweep speed: frozen from prior run
- No code / param changes after start

### Design
Default: all 16 robots in systematic parallel sweep.

Stall definition: **no new signal for T consecutive ticks** = no detection event and no cell with P(hiker) increase >0.05.

Intervention when stalled:
- Controller releases **exactly 2 explorers**: 2 robots farthest from sweep centroid
- Explorers go to random frontier >2x sweep radius, max 40 ticks
- Rejoin sweep immediately on any new signal or after 40 ticks
- Max 1 release per 50 ticks

Conditions, within-seed:
- **T=never** (control, no explorers)
- **T=30**
- **T=60**

### Hypotheses + falsification

**H1: T=30 finds faster than never.**
Falsified if mean time-to-find(T30) >= mean(never) across seeds 180-199, or one-sided paired Wilcoxon p >= 0.05.

**H2: T=60 finds faster than never, but slower than T=30.**
Falsified if T60 >= never (no benefit), or if T30 >= T60 (no earliness advantage).

**H3 Guardrail: No excess losses.**
Falsified / benefit invalidated if mean robot losses/run in T30 or T60 exceeds never by >0.5 robots, or search-failure rate (not found in limit) exceeds never by >5pp.

### Metrics
- **Primary:** time-to-find (ticks from start to locate)
- Secondary: robot losses/run, failure rate, total distance, explorer activations/run
- Analysis: paired per seed, report mean diff + 95% CI + median. No peeking, no extra seeds.

### Why stall-triggering might succeed where always-on failed
Always-on fragmented the sweep front, thinned coverage, and kept 1-2 robots permanently exposed to faults with low information yield.

Stall-triggering preserves exploitation when gradient is rich, then adds exploration only when marginal gain ~0. It limits fault exposure time and re-concentrates force on new signal, instead of permanent dispersion.
