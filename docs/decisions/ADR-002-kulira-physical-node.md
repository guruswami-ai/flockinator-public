# ADR-002: Kulira is a physical node - an embodied small-model adversary

## Status

Accepted (2026-11-07). Records existing hardware and the intended
trajectory; live Glimmer actuation remains separately gated (see
Consequences).

## Context

Kulira began as a host running adversary software
(`docs/kulira-friction.md`): scripted and model-proposed friction
against the sixteen-node fleet, inside a safety contract
(proposals only, SafetyGate as the sole actuation path, no
management-plane authority). Two facts about its physical form
were not previously catalogued as experiment design:

- **The host is a single high-capability machine** (Apple M5 Max,
  64 GB RAM) running the abliterated Muse Glimmer model locally
  under the Hermes agent harness. Local inference matters:
  the adversary can run long, autonomous agentic tasks - observe,
  propose, revise - with no cloud dependency, at negligible
  marginal cost, for the duration of an experiment campaign.
- **An embodied peripheral exists**: ESP-MOSAICO, an ESP-class
  device with custom Hermes firmware, a developer-kit sensor
  board, camera, microphone array, speaker and multiple sensors,
  positioned to face the panel wall. It is Kulira's eyes, ears
  and mouth: it can observe the swarm's human-visible state,
  listen, and interact through sound, light, WiFi/ESP-NOW and
  I2C-driven outputs. The project was built externally to
  Flockinator for safety separation, and is catalogued in
  `docs/experiments/esp-mosaico-adversary.md`.

Together they make the adversary a *physical node* in the
experiment, not a script on a server: a small model with a body,
sharing the fleet's sensory world.

## Decision

Catalogue Kulira as a two-part physical adversary node:

1. **Brain (host)**: M5 Max host, Hermes agent harness, local
   abliterated Muse Glimmer (oq8e-class quantisation) as the
   proposal engine for scenarios and attack plans. Abliteration
   is a deliberate choice: the model must generate impersonation,
   deception and disruption proposals for a legitimate, owner-
   authorised red-team experiment without refusing the task.
2. **Body (ESP-MOSAICO)**: the sensory/effector peripheral -
   camera, microphones, speaker, sensor board - through which
   the adversary perceives the wall and acts in the fleet's
   physical and radio environment.
3. **Contract (unchanged)**: Glimmer/Hermes propose;
   `kulira-core`'s SafetyGate is the only actuation path;
   campaigns are seeded, bounded, graded and hash-logged;
   management/OTA/identity is never a target. Embodiment adds
   senses and effectors, never authority.

## The asymmetry hypothesis (why this node matters scientifically)

The interesting question is not whether a small model can attack
- it is the **asymmetry advantage**: attack *discovery* is cheap
and parallel (a small, fast, embodied model proposing many
techniques, observing which ones move the swarm), while defence
appears to require a much larger stack - frontier models writing
firmware, reviewers, frozen gates, confirmatory runs. If small-
model suggestions repeatedly produce outsized changes in swarm
trust behaviour, then agent-to-agent security economics favour
the attacker in a way the field has not measured.

The counter-hypothesis is equally valuable: the larger models
may *find the defences during construction* - in the process of
building and testing panel firmware, the defence could be
designed-in rather than inferred per-attack at runtime, collapsing
the asymmetry. Flockinator can distinguish these: the same
adversary node, the same SafetyGate, and a fleet whose firmware
and trust policies are versioned and scored. Either outcome is
a publishable measurement, not a talking point.

## Alternatives considered

- **Cloud-hosted adversary model.** Simpler to scale, but adds
  dependency, cost and latency to long campaigns, and moves the
  adversary's reasoning off the bench. Rejected: local inference
  on the M5 host is sufficient and keeps the experiment
  self-contained and reproducible.
- **Scripted adversary only (no model in the loop).** Fully
  deterministic and easier to pre-register, but a fixed script
  measures robustness to that script; it cannot discover which
  deceptions still work as defences evolve. Retained as the
  baseline adversary; rejected as the only one.
- **Direct model actuation (Hermes transmits).** Removes the
  human-designed bottleneck and matches "realistic attacker"
  framing - and destroys seeded replayability, bounded scope
  and the safety contract. Rejected unconditionally; the
  SafetyGate path is the design, not a courtesy.

## Consequences

- **Cataloguing debt closed**: hardware inventories and judging
  material may now describe Kulira physically (host class,
  local model, embodied peripheral) without implying fleet
  membership or management authority.
- **Standalone trajectory**: once programmed and tasked, the
  ESP-MOSAICO may run its adversary firmware independently of
  the Hermes/Glimmer host - turning the aggressor into a much
  cheaper, reproducible artefact other labs could build. That
  transition requires its own pre-registration and safety
  review; independence is a research step, not an upgrade to
  apply casually.
- **No status change for live actuation**: this ADR records
  what Kulira *is*. Any Glimmer-driven transmission still
  requires the separate owner live gate, exactly as before.
- **Asymmetry becomes testable**: with the adversary versioned
  (host model, firmware, scenario provenance logged per
  campaign), "small model vs defence stack" stops being a
  metaphor and becomes a measurable comparison across cycles.

Plain-language context: [Kulira friction node](../kulira-friction.md).
Adversary hardware detail: [ESP-MOSAICO adversary](../experiments/esp-mosaico-adversary.md).
