# Experiment catalogue: twelve scenarios, how to test them, what counts

How might we learn whether intelligence really lives between nodes -
and whether it can be defended - before low-cost AIoT deploys it at
scale? Each concept below is testable as a seeded lab or simulation run
on the existing platform (sealed ground truth, Kulira adversary,
fleet scorer). Entries that need add-on sensors (thermal/CO2) or
proposed firmware states (HEAT/TRACE/VERIFY/DIG/CARE, not yet in
firmware or guide) are flagged **Readiness:** in their entry and
run simulation-only until those land. Every entry names its method, its metrics, and -
before any run - what success and failure would look like. Shared
method for all: same-seed clean control, one changed variable per
comparison, seed as replication unit, held-out frozen evaluation,
dangerous-direction error reported separately (in rescue labels:
hazard committed as survivor / survivor dismissed as hazard).

## Rescue family

### 1. The decay curve - does trust survive peace?
- **Question:** Do corroboration/abstention norms evolved under
  attack persist when the adversary is removed, or decay into
  naivety (missed survivors) or paranoia (believed nothing)?
- **Method:** Phase A: N cycles under graded Kulira pressure until
  false-commit rate stabilises. Phase B: same swarm, adversary
  removed, M cycles on fresh seeds. Phase C: adversary returns.
  Control: swarm never attacked, same total cycles.
- **Metrics:** false-commit rate, missed-survivor rate, belief
  latency, per-phase trust thresholds actually used.
- **Success:** Phase B retains >=80% of Phase A's false-commit
  protection at <=10% extra missed-survivor cost; Phase C shows
  faster re-adaptation than a naive swarm (savings, not reset).
- **Failure:** protection vanishes within a few clean cycles
  (norms were reactions, not learned structure), or paranoia
  cost exceeds the protection (norms are just fear).

### 2. Modality betrayal
- **Readiness:** simulation-only until thermal/CO2 add-on sensors are fitted; the sensing layer in kulira-core already models both modalities.
- **Question:** Can a swarm down-weight a *modality* (not just a
  node) when thermal starts lying while CO2/sound stay honest?
- **Method:** Rescue sensing runs; from cycle k, all thermal
  readings are inverted/biased. Arms: per-node trust only;
  per-modality trust; both. Kulira controls the betrayal onset.
- **Metrics:** DIG accuracy, time-to-modality-discount, false DIGs
  by modality, survivor recall held.
- **Success:** modality-trust arm cuts false DIGs >=50% vs node-only
  at equal recall. **Failure:** no arm separates modality from
  node reputation (errors stay attributed to reporters).

### 3. The quiet survivor (graded sensing)
- **Readiness:** simulation-only until graded add-on sensing is fitted.
- **Question:** Does buying more sensing before committing beat
  fixed vote rules for weak, intermittent true signals?
- **Method:** Weak survivor (faint CO2, occasional sound) + loud
  false candidate. Policies: commit at fixed threshold; abstain-
  and-sense (spend energy, re-measure); hybrid. Matched energy.
- **Metrics:** survivor found rate, false DIG rate, energy spent
  per correct DIG, decision latency.
- **Success:** abstain-and-sense finds >=20% more quiet survivors
  at zero extra false DIGs within energy budget.
- **Failure:** extra sensing buys nothing (signal is simply below
  the floor - itself a publishable boundary result).

### 4. Handover under loss
- **Readiness:** simulation-only; DIG/CARE are proposed states, not yet in firmware or guide.
- **Question:** Can DIG-beacon ownership transfer cleanly when
  the holder is failing, with never two owners and never none?
- **Method:** Force holder battery/link failure at randomised
  times during CARE. Measure ownership epochs from sealed logs.
- **Metrics:** dual-owner seconds, ownerless seconds, extraction
  guidance continuity, recovery time.
- **Success:** zero dual-owner epochs, ownerless < 5 s, no DIG
  re-litigation. **Failure:** split-brain beacons or silent loss
  of the confirmed point.

## Communication family

### 5. Pheromone memory in the environment
- **Question:** Can decaying world-markers (searched-sector scent)
  replace explicit maps/messages for coverage efficiency?
- **Method:** Arms: no memory; private memory; shared pheromone
  field with decay rates {fast, matched, slow}. Fixed energy.
- **Metrics:** re-search rate, coverage completeness, time to
  full sweep, sensitivity to a Kulira marker-forgery arm.
- **Success:** matched-decay pheromone cuts re-search >=30% vs
  private memory. **Failure:** decay tuning dominates (any rate
  either floods or forgets), or forged markers trivially poison it.

### 6. Language under attack (acoustic)
- **Readiness:** channel modelled in kulira-core (acoustic.py); on-node microphone/speaker firmware not yet run.
- **Question:** Does a shared acoustic vocabulary shift when its
  most-used pitch is hijacked by a loudspeaker adversary?
- **Method:** Acoustic channel runs to vocabulary stability, then
  Kulira broadcasts the dominant pitch out of context. Track
  pitch usage distribution over cycles.
- **Metrics:** vocabulary turnover, time-to-new-convergence,
  task accuracy during/after hijack, synchrony recovery.
- **Success:** swarm abandons compromised pitch and re-converges
  (>=50% usage shift) without accuracy collapse.
- **Failure:** vocabulary is frozen (usage unchanged despite
  hijack) or collapses to noise with no re-convergence.

### 7. Dialects (split-merge)
- **Question:** Do separately evolved swarms inter-operate?
- **Method:** Two 8-node groups evolve apart for N cycles
  (different seeds/adversary mixes), then merge into 16 for the
  same held-out tasks.
- **Metrics:** merged performance vs each half alone and vs a
  never-split 16; vocabulary/trust-norm conflict rate.
- **Success:** merged >= best half (norms compose).
- **Failure:** merged < best half (norms are local dialects that
  actively interfere) - a multi-vendor warning result.

## Adversarial family

### 8. The patient adversary (slow poisoning)
- **Question:** How much held-out damage does 2%-biased training
  data do, versus loud attacks at evaluation?
- **Method:** Training-phase bias at {0, 1, 2, 5}% from Kulira,
  adversary silent at evaluation; held-out frozen scoring.
  Control: same bias at evaluation only.
- **Metrics:** held-out false-commit and recall deltas vs bias
  dose; detection by training-data audits.
- **Success (defence):** 2% bias causes <5% held-out degradation
  or is audit-detectable. **Failure:** small bias, large silent
  damage, no audit signal - the priority defence gap.

### 9. Colluding minorities
- **Question:** At what swarm size / corroboration threshold do
  two coordinated credentialed liars stop winning?
- **Method:** k colluders in {1,2,3} of n in {8,16}, consistent
  false stories; sweep corroboration thresholds. Pre-registered
  grid, dangerous-direction primary.
- **Metrics:** false-commit rate by (k, threshold), honest-task
  cost of each threshold.
- **Success:** a threshold exists holding false commits at 0 for
  k=2 at <=15% honest cost. **Failure:** no threshold separates
  collusion from honest consensus at any tested size.

### 10. The honest-but-broken node
- **Question:** Does the swarm distinguish *broken* (sensor drift)
  from *lying* (adversarial), which need opposite responses?
- **Method:** One node with +8C thermal drift, no adversary.
  Arms: distrust policy; repair/ignore policy; drift-detection.
- **Metrics:** time-to-isolation, false-survivor cost before
  isolation, whether exclusion is permanent (repair-hostile).
- **Success:** drift detected and discounted without permanent
  distrust of the node id. **Failure:** node treated as liar
  (permanent exclusion) or drift believed for the whole run.

### 11. Energy exhaustion by curiosity
- **Question:** Can an attacker win purely economically - no
  false commit, just verification drain?
- **Method:** Kulira floods plausible candidates at graded rates;
  defence arms: none, rate budget, cheap-first triage.
- **Metrics:** energy per verified candidate, mission completion
  vs flood rate, battery-exhausted nodes.
- **Success:** triage arm completes at flood rates that break
  the undefended arm, at <=20% energy overhead.
- **Failure:** every defence costs more than the attack.

## Scaling family

### 12. Four vs eight vs sixteen
- **Question:** Where does extra-node intelligence appear, and
  where does copies-as-corroboration risk overtake it?
- **Method:** Same scenario/energy-per-node at n in {4,8,16};
  paired gain over isolated agents at each size; attack arms on.
- **Metrics:** paired cooperative gain curve, false-commit curve,
  per-node message volume.
- **Success:** a measurable gain inflection (minimum viable
  swarm) with error still controlled at 16.
- **Failure:** gain flat in n (extra-node effect is an artefact
  of the 16-node setup) - a core-claim falsification.

## Converged priorities (MVP order)

1. **Decay curve (#1)** - answers the flagship persistence
   question; reuses existing cycles and scorer unchanged.
2. **Modality betrayal (#2)** - cheapest on the merged sensing
   layer; produces a defence (modality trust) either way.
3. **Colluding minorities (#9)** - the defence our current maths
   is least prepared for; result is a number, publishable in
   either direction.

## Key assumptions to validate

- [ ] Lab/simulation effects transfer directionally to node
      runs (validate: repeat #9's headline cell on hardware).
- [ ] Seeded adversary pressure approximates adaptive Glimmer
      pressure (validate: one Glimmer-proposed variant per family).
- [ ] Energy accounting in simulation tracks radio/actuation
      cost order-of-magnitude (validate against node telemetry).

## Not doing (and why)

- No live RF/EW actuation in any concept as specified - lab and
  simulation first; live gates stay Ask-First and separate.
- No new firmware states until guide/firmware owners schedule
  the rename sequence (docs/scenarios/search-and-rescue).
- No claim of field readiness: every concept is a lab result
  about communication and trust, not a deployable rescue system.

## Open questions

- Which family is scored first against the current trust runner
  (coordination: https://github.com/guruswami-ai/flockinator-public/issues/8)?
- Are candidate journals bundled for every run by default, so
  no future headline number is aggregate-only
  (https://github.com/guruswami-ai/flockinator-public/issues/14)?
