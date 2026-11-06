<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

# Pre-reg: Adaptive Commitment vs Fixed 8 / Fixed 14

**Simulated only.** 16x ESP32 panels + 1 controller, seeded virtual-world hiker search. No real-world data.

### 1. Regime: loss-bearing
- Searches: **8 / day**
- Fault: **p=0.01 / robot / sortie**
- Far fraction: **0.35**, Near: 0.65
- Distance class **known at dispatch** from initial report. No other peeking.
- Seeds: **200-219 inclusive (n=20)**. Same 20 worlds for all arms.

### 2. Arms (60 runs total)
- **A Fixed-8:** launch 8 every search.
- **B Fixed-14:** launch 14 every search.
- **C Adaptive:** launch 8 if report=near, top-up to 14 pre-departure if report=far. No mid-search top-up.

Fleet capped at 16. Losses carry over within a seed run. Order randomized per seed: A-B-C permuted by `seed % 6`.

### 3. Metrics
- **Primary efficacy:** far finds / seed [0-...]
- **Guardrails / efficiency:**
  - `losses`: robots lost / seed
  - `readiness`: % searches launched at full requested strength
  - `total finds`: near+far / seed

Logged by controller per seed: finds, losses, readiness, robots used.

### 4. Hypotheses
- **H1 Efficacy: Adaptive matches 14 on far, beats 8**
  - `mean(C_far) >= 0.9 * mean(B_far)` [non-inferior]
  - `mean(C_far) > mean(A_far)` by >=15%
- **H2 Safety: Adaptive matches 8 on cost, beats 14**
  - `mean(C_losses) <= mean(A_losses) +10%`
  - `mean(C_readiness) within 5pp of mean(A_readiness)`
  - `mean(C_losses) < mean(B_losses)` and `mean(C_readiness) > mean(B_readiness)`

### 5. Falsification conditions
- **F1:** Paired test by seed (Wilcoxon, alpha 0.05): C_far significantly < B_far, OR C_far not significantly > A_far => H1 rejected.
- **F2:** C_losses significantly > A_losses, OR C_readiness significantly < A_readiness, OR C not better than B on losses/readiness => H2 rejected.
- **F3:** If B_far <= A_far => regime invalid, void test.

Analysis paired by seed. Report means + SD + paired differences, no re-seeding, no optional stopping.

### 6. Guardrails / Stop
- Abort arm if fleet available <8 for 2 consecutive searches, or cumulative losses >24 across 20 seeds.
- Controller halts on seed mismatch or panel dropout >2/16.
