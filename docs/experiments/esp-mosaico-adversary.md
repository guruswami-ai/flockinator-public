# ESP-MOSAICO: the dynamic adversary node (research direction)

Status: future research direction, owner-authored hardware in
development on the Kulira host. Not part of any scored cycle yet.

## Concept

Kulira's friction so far is scripted: pre-registered adversary
policies executed by `tools/kulira-core`, with the abliterated Muse
Glimmer model used to *conceptualise* attacks offline. ESP-MOSAICO
closes the loop. It is an ESP-class device with a camera and
microphone, speakers, and a peripheral board carrying multiple
sensors, positioned facing the panels. Driven by the Hermes agent
harness with the Glimmer model, it can:

- **See** the entire fleet state on the wall (the same human-visible
  surface the wall observer records), plus hear and sense its
  environment.
- **Act** through audio, light, ESP-NOW/WiFi radio, and I2C
  peripheral outputs - the extension of Kulira's existing
  interference channels, now with sensory feedback.
- **Adapt**: conceive friction dynamically, observe its visible
  impact on the wall, and revise - the difference between a scripted
  opponent and an evolving one.

That closes the experiment's central loop on the adversary side:
perceive -> propose -> act -> observe -> adapt, at machine speed,
against a fleet that is itself learning whom to trust. It is the
practical testbed for the tiny-model asymmetry question in
`docs/learn/`: what a small, fast, embodied adversary does to
agent-to-agent trust that static attack scripts cannot reveal.

## Rules of engagement (unchanged, and binding on this device)

Dynamic conception does not mean dynamic authority. The existing
Kulira safety contract applies in full:

- Owner-authorised lab use only, on the owner's fleet and network.
- The management/OTA/identity plane is never a target, for this
  device as for every Kulira channel.
- Every actuation passes the established gate: proposal ->
  `campaign validate` -> seeded, bounded, reversible dry run ->
  hash-chained log with provenance. Glimmer proposals are
  proposals; the SafetyGate is the only path to actuation, and its
  action allowlist does not grow because a model asked.
- Live RF/audio/light actuation requires the same separate owner
  gate as every other live channel. Nothing in this document
  authorises transmission.

## Staged programme

1. **Shadow (no actuation).** MOSAICO watches the wall during
   scored runs; Glimmer records what friction it *would* apply and
   when. Compare its choices against the scripted policies and
   against outcomes. Publishable as analysis; zero risk.
2. **Scripted effectors, dynamic timing.** Pre-registered Kulira
   actions, but MOSAICO chooses timing and target from what it
   sees, inside the allowlist. Measures whether perception alone
   makes the same attacks more effective.
3. **Dynamic conception inside the gate.** Glimmer proposes novel
   actions; anything outside the allowlist is logged as a proposal
   and never executed. Measures the proposal distribution itself -
   what an embodied tiny model invents that we did not script.

Each stage needs its own pre-registration, same-seed controls, and
the wall-observer record as the shared ground truth of what the
fleet displayed while it happened.

## Why this matters beyond this fleet

Scripted red teams find the failures you imagined. A perceiving,
adapting adversary finds the ones you did not - which is the entire
argument for evolving defences under real friction rather than
theoretical friction. If a tiny embodied model can learn to move a
16-agent fleet's behaviour by watching its wall, that is a result
about agent-to-agent security in general, measured here first
because here it is safe, seeded, and reversible.
