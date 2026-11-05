# ADR-001: Design the swarm to be watched - human perception as an instrument

## Status

Accepted (2026-11-05)

## Context

Agent-to-agent systems produce behaviour no participant fully
describes: decisions emerge between agents, faster than any human
can follow in raw form. The usual observability answer - more logs,
more graph data - fails on the reader, not the data. Text journals
and binary interaction graphs at swarm scale are effectively
meaningless to a human trying to notice that something *unusual*
is happening.

Humans, by contrast, are exceptionally good at spotting unusual
patterns in visual scenes and sound: the one bird out of formation,
the rhythm that breaks, the light that does not belong. That ability
is a product of our biology, and it is free, fast, and hard to
replicate with a dashboard query written after the fact.

## Decision

Constrain agentic experiments into scenarios whose state is
continuously rendered in human-perceptible form:

- **Visual consolidation.** Sixteen physical nodes on a wall render
  the swarm's state as one scene a human can take in at a glance -
  formation, hesitation, disagreement, and recovery are visible as
  pattern, not as rows in a log.
- **Human-channel checkpoints.** Agent-to-agent experiments route
  through bottlenecks where human senses are useful: displayed
  states, spoken or harmonic auditory markers, and language a
  person can read - so emergent behaviour passes through a medium
  human inference is built for.
- **Humans as discovery instruments.** Unexpected behaviour is
  first *noticed* by a watching human ("that looks wrong"), then
  verified against the sealed journals and scorer. Perception
  proposes; measurement disposes.

Flockinator is, in this framing, a **microscope for emergent
behaviour**: an instrument that makes between-agent phenomena
visible at a scale and speed human comprehension can work with,
and a feedback mechanism researchers can reason about while an
experiment runs - not only after it ends.

## Alternatives considered

- **Logs-first simulation (no physical rendering).** Cheaper and
  faster to iterate, but emergent behaviour must be guessed at in
  advance and queried for; unanticipated patterns - the interesting
  ones - are exactly what nobody writes a query for. Rejected as
  the primary instrument; logs remain the evidence layer.
- **Single central dashboard screen.** One rendered view is easier
  to build, but collapses per-node state into an aggregate someone
  designed; the per-node pattern (who disagrees, who hesitates)
  is the signal. Rejected.
- **Fully autonomous runs with post-hoc review.** Maximises
  throughput and removes the human from the loop entirely - which
  also removes the only pattern-spotter currently able to flag
  behaviour nobody predicted. Rejected for discovery work.

## Consequences

- Scenario design is constrained: states must be renderable,
  checkpoints must exist where a human can usefully look, and
  auditory/visual markers are part of the protocol surface, not
  decoration.
- Human noticing is a bias as well as an instrument: salience is
  not importance. Every human-spotted anomaly must be confirmed
  or refuted in the sealed evidence before it becomes a claim,
  and the scorer - not the audience - decides results.
- The same wall serves communication: a commander, a class, or a
  judge can see trust fail and recover without reading a journal.

Plain-language version: [Learn: a microscope for emergent behaviour](../learn/microscope-for-emergence.md).
Method context: [experimental methodology](../experiments.md).
