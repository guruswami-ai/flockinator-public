# Experimental methodology

## Question

Can small agent models, trained in isolation, improve - individually and
as a swarm - when their environment pushes back? Flockinator compresses
nature's slow optimisation (hardship and selection over evolutionary
time) into seeded, measurable runs humans can watch. The drone-survey
scenario is a visualisation of that question, not an operational system.

## Three loci of intelligence

- **In the node** — the small local model/policy each ESP32 body carries.
- **External to the node** — learning and review on the Korvo or hosts,
  including the Muse assessor/coordinator swarm (see
  [meta-muse](meta-muse/README.md)).
- **Between nodes** — inter-node trust, corroboration, and communication
  norms that emerge (or fail) under pressure.

## Method

1. **Isolation first.** Train each small model alone; record its private
   cues, memory, and policy version.
2. **Controlled comparison.** Every claim needs a same-seed control:
   clean vs impaired training crossed with clean vs impaired testing,
   plus a no-communication / private-cue baseline. One changed variable
   per comparison.
3. **Graded adversity (Kulira).** Friction is seeded, logged, bounded,
   and reversible: application/layer-1-3 interference, impersonation,
   and false reports on the experimental channel only. Network jamming
   devices are never used; management, stop, and recovery traffic is
   never touched. See `tools/kulira-core/`.
4. **Held-out judgement.** Grade on fresh seeds with learning frozen.
   Report distributions, failures, and inconclusive results - not a
   single intelligence score.
5. **Provenance.** Director (ground) truth is stored separately from
   anything agents could observe, and revealed only at scoring. Forwarded
   copies never count as independent corroboration.

## What counts as evidence

| Dimension | Measure |
|---|---|
| Individual competence | Held-out task accuracy, calibration, recovery |
| Cooperative benefit | Paired gain over private-cue baseline at matched budgets |
| Communication | Delivered/consumed vs stale/duplicate/rejected messages |
| Learning | Gain vs exposure; retention; generalisation to unseen scenarios |
| Resilience | Performance under each fault; false-message acceptance; recovery time |
| Cost | Decision time, memory, message volume, log completeness |

Synchronised animation, packet counts, and extra observations are not,
by themselves, evidence of cooperation or intelligence.

## Reference scenario

The illustrated quadcopter survey
([guide](scenarios/quadcopter-survey/README.md)) walks one full cycle:
orders, deployment, scanning, sightings, sharing, doubt, verification,
return, and charging - including the false-report (deception) beat that
Kulira-style experiments formalise.

## Measured results so far

The planner-intelligence loop has run five generations under this
method (dev seeds 0-19, 16 eligible; holdout 100-109 sealed):
coverage nearly tripled (sighted recall 0.2141 -> 0.6226) while four
successive commit policies were rejected by their own pre-registered
gates - committed Enemy->Friendly must stay at zero, and no
sighting-count voting rule meets it at useful yield under 60-82%
identification accuracy. Zero unsafe promotions shipped. Charts,
gate tables, the deterministic scorer, and sample journals are in
[results/](results/README.md).
