# Experimental methodology

## Question

Can small agent models, trained in isolation, improve - individually and
as a swarm - when their environment pushes back? Flockinator compresses
nature's slow optimisation (hardship and selection over evolutionary
time) into seeded, measurable runs humans can watch. The search-and-rescue
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
   never touched. Full design: [kulira-friction.md](kulira-friction.md) and `tools/kulira-core/`.
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

The proposed [Patternflow flocking scenario](scenarios/patternflow-flocking/README.md)
extends this method to acoustic communication, collective music and panel dance,
with Kulira disturbances and matched camera/audio/telemetry comparisons across
firmware and settings generations.

## Why this is worth doing

**Security.** Agent swarms that trust peer messages inherit every
failure of naive trust: impersonation, replay, false reports, and
correlated errors that look like consensus. Flockinator makes those
failures cheap, visible, and measurable *before* they are expensive:
bounded adversarial friction (Kulira) against authenticated management
planes, dangerous-direction metrics (Enemy->Friendly, not just raw
accuracy), pre-registered promotion gates, and canary deployment.
A swarm that has never been lied to in training has no earned reason
to be trusted in deployment.

**Extra-node intelligence.** The most interesting signal in these
experiments is not inside any single node. A node's policy can be
scored alone, but corroboration norms, trust weighting, abstention,
and recovery are properties of the *interaction graph* - they exist
between nodes, in the timing and provenance of messages, and in what
the swarm collectively refuses to believe. Nature is full of this:
no single ant, cell, or virion holds the colony-, immune-, or
ecosystem-level strategy, yet those higher-level patterns are real,
adaptive, and abundant. They are also hard to quantify, because our
metrics are built per-agent. Flockinator is an instrument for that
measurement problem: sixteen embodied agents with sealed ground truth,
so extra-node intelligence can be defined operationally - the paired
gain of the communicating swarm over the sum of its isolated agents,
at matched observation and energy budgets - and watched as it emerges,
fails, or is deceived.

**Implication for agent design.** If intelligence can live between
agents, then designing intelligent systems in the AI age is not only
about bigger individual models. It is about the protocols, trust
economics, and selective pressures *between* many small models -
which is trainable, testable, and, as the rejected candidates here
show, falsifiable. Small isolated models plus a well-measured
interaction layer may be a more robust path to capable swarms than
any single large one, because the interaction layer is where
verification, diversity, and recovery naturally live.

Measured cycle results, field findings from the live fleet, and
the next experiment families are tracked in
[results/](results/README.md).
