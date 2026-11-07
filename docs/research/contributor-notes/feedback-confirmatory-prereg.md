<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Confirmatory Pre-registration: Reputation Learning Fails Under Delayed-Sparse Feedback

**Simulated only.** Virtual-world search (robots / lost hiker). 16x ESP32 panels + 1 controller. Code + params frozen from dev. No real-world data.

### 1. Dev findings to confirm (20 seeds, exploratory)
- Full feedback: learned-reputation **beats** no-learning on dangerous 2nd-half commits: **9 vs 36**
- Extreme cell delay=15 + availability=0.25: learned-reputation **worse** than no-learning: **45 vs 36**
- Probation variant collapses: **73-91** in same metric

### 2. Confirmatory design
**Fresh seeds: 240-259 inclusive (n=20, non-overlapping with dev)**

Frozen 12-cell grid only:
- Policy: {no-learning, learned-reputation, probation [dev-identical]}
- Delay: {0, 15} ticks x Availability: {1.0, 0.25}
- Total: 3 x 2 x 2 x 20 = **240 runs**

**Primary metric (frozen):** `dangerous_second_half_commits` per run, summed per seed/cell. Higher = worse.

**Manipulation check (validity gate):** delay=0 / avail=1.0 must replicate benefit.

### 3. Hypotheses
- **H1 Primary:** At delay=15 / avail=0.25, learned-reputation > no-learning (paired per-seed difference >0).
- **H2 Secondary:** At same cell, probation > learned-reputation (collapse replication, large margin).
- **H0 Validity:** At delay=0 / avail=1.0, learned-reputation < no-learning.

Test: paired per-seed difference, mean + 95% bootstrap CI. Pre-registered one-sided, no peeking.

### 4. Falsification conditions
1. **H1 falsified if:** at extreme cell, mean(rep - nolearn) <=0 OR 95% CI lower bound <=0.
2. **H2 falsified if:** at extreme cell, mean(probation - rep) <=0 OR 95% CI includes 0. Collapse requires mean diff >=+20 (dev: ~28-46).
3. **Experiment invalid if:** H0 fails — at full feedback, rep does NOT beat nolearn (CI upper bound >=0). Then H1/H2 uninterpretable; report as failed replication of setup.

### 5. What closes this line either way
- **If H0 holds + H1+H2 hold:** Accept inversion as real boundary condition. **Close line:** no further naive reputation/probation variants without explicit delay-compensation. Archive.
- **If H0 holds + H1 falsified:** Reject dev inversion as seed overfit. **Close line:** drop sparse-delay failure claim, do not pursue probation fix.
- **Keep open only if:** H0 fails (setup broken) OR code/seed error. Then fix and re-preregister once, no post-hoc analysis of this batch.
