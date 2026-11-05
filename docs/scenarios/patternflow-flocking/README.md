# Patternflow flocking through sound and light

Proposed experiment for Flockinator's sixteen independent node bodies. The swarm
learns to exchange information through sound and explores collective rhythm,
music and animated dance while Kulira introduces graded friction. A camera facing
the grid records early and later runs alongside telemetry, making changes visible
and audible as well as measurable.

This is a scenario specification. Acoustic learning, collective composition and
the recording pipeline require implementation and validation. Patternflow supplies
the visual vocabulary. Its integration must include a pinned upstream revision,
per-pattern attribution and licence review before code is added to this repository.
[Patternflow upstream](https://github.com/engmung/Patternflow)

The scenario follows the existing [architecture](../../architecture.md),
[experimental method](../../experiments.md), [Muse review pipeline](../../meta-muse/README.md)
and [Kulira boundaries](../../kulira-friction.md). Its central question is whether
adaptation improves communication and recovery at a fixed resource budget.

**Relationship to the canonical acoustic work.** The vocabulary,
synchrony, and acoustic-channel definitions used here are the ones in
[Learn: acoustic language](../../learn/acoustic-language.md) and the
tested host model [`acoustic.py`](../../../tools/kulira-core/kulira_core/acoustic.py);
where this scenario uses the same terms, those definitions win.
Patternflow's delta is the performance/visual layer on top: panel
dance, cooperative rhythm, and camera-audible group composition. It
does not redefine the channel model.

## What an audience sees and hears

Each panel has its own listening, signalling, waiting and recovery states. A sound
can change a node's colour, motion or density. A node may answer with a short phrase,
then pause to hear a reply. Groups may develop alternating rhythms or complementary
parts. Dance initially means movement within the panel animation. The camera is an
observer recording the grid. Visual communication between nodes would require a
separate sensing implementation and declared experiment condition.

Expose the selected mode, run ID, generation and fault condition on the web view.
Drive visible events from timestamped runtime state. Show attempted sound output,
observed acoustic input and decoded messages as distinct events. Keep uncertain
source attribution visible. A camera microphone captures the room mixture, while
per-node telemetry records each microphone's observations and speaker actions.

## Three experiments with different claims

| Experiment | Node task | Evidence sought |
|---|---|---|
| Music response | Listen to a recorded stimulus and map measured level/onsets/bands into Patternflow parameters | Repeatable input-to-display response, latency and frame continuity |
| Cooperative performance | Listen, take turns, choose bounded motifs and recover a shared rhythm after disturbance | Participation, timing, turn conflicts, recovery and recordings of the group |
| Acoustic communication | Encode a private cue into sound, interpret peers and choose an answer before a deadline | Held-out decoding and task gain over isolated and fixed-protocol baselines |

Begin with an engineered call-and-response baseline and a fixed motif vocabulary.
Learned encoders/decoders and evolving vocabularies are later candidates. Log which
parts were designed, learned during episodes or changed between generations.
Musical preference is a separately reported, blinded listening assessment.

For the first communication task, the director privately supplies each node with a
noisy binary cue about a hidden state. Cue assignments and quality are frozen by
seed. Nodes exchange bounded acoustic motifs and individually choose 0, 1 or
abstain before the deadline. Ground truth and scoring stay with the director.
This gives a concrete task score while allowing varied signalling strategies.
Select cue quality and episode timing in calibration, then freeze them before
candidate search. Pre-register the reward for correct, wrong and abstained
answers, plus answer coverage, so silence cannot win by hiding errors. Future
tasks may introduce distinct roles or richer messages.

## Ownership and allowed information

| Component | Responsibility in this scenario |
|---|---|
| Node platform | Own microphone/speaker services, timestamp features and actions, render Patternflow, journal locally and enforce resource limits |
| Agent policy | Use declared local observations and memory to listen, emit a motif, answer, abstain or recover |
| Korvo | Manage experiment configuration, starts/stops, run identity, health and archive references |
| External hosts | Record media, score sealed runs, run Muse inference and build candidate firmware |
| Muse node lanes | Assess each node's sealed evidence and propose a cited, bounded change |
| Wonder Full coordinator | Review swarm outcomes and select retain, collect-more, candidate or canary |
| Kulira through Hermes/Glimmer | Propose bounded disturbances that the Kulira execution gate validates and logs |

Default to acoustic peer communication. Radio carries management, private cue
assignment and declared training feedback. Keep peer answers, timing plans and
director truth outside those inputs. Any radio-assisted comparison is a named
condition. Fixed start cues and common music can synchronise a group, so include
controls for both. Allow feedback after training decisions only. Freeze learning
and withhold feedback during evaluation.

Record execution location for every policy and update. Local firmware decisions,
host decisions and copied archives need attributable evidence. Reuse the existing
audio service and authenticated maintenance path. Audio capture, synthesis and
logging need bounded queues and explicit stale-input handling alongside rendering.
A node begins muted, suppresses or marks its own playback and acoustic tail, and
returns to listening after a finite phrase. Calibrate room coupling and each
microphone/speaker before interpreting a neighbour response.

## Additional senses and interactive devices

The node firmware already reads SHTC3 temperature/humidity and QMI8658 motion,
with RTC status and dual-channel microphone capture alongside speaker output.
These inputs can support environmental context, movement cues and acoustic
interaction. Source direction from the microphone pair requires calibration and
an implemented estimator. The board also exposes expansion connections.
[Board resources](https://docs.waveshare.com/ESP32-S3-RGB-Matrix),
[sensor driver](../../../firmware/node-platform/src/sensors.cpp),
[audio driver](../../../firmware/node-platform/src/audio.cpp).

Optional sensing/output modules are listed in the appendix at the end of this document; they are not part of the scored scenario.

Define the actual sensor output, units, sampling rate and calibration for each
module. IR may mean reflected-light, ranging or thermal sensing depending on the
chosen device. Record each reading's validity, age and source, including whether
it was measured on a node, supplied by a host or simulated. Reuse the public
[acoustic model](../../../tools/kulira-core/kulira_core/acoustic.py) and
[sensing analysis](../../../tools/kulira-core/kulira_core/sensing.py) where their
contracts fit. Physical integration needs measured channel and sensor validation.

Maintain a per-node capability manifest with module/driver versions, interface,
reserved pins, electrical requirements, address, sample budget and calibration.
Check the exact board revision and module against the display, SD, audio, memory
and boot-pin allocations before wiring. Shared buses need compatible addresses
and timing. Camera capture and active ranging need their own bandwidth, power and
interference budgets. A companion processor is an option when local resources
are insufficient, with its latency and execution location recorded.

Evaluate audio-only, optional-sensor-only and combined conditions at declared
budgets. Hold hardware and observations fixed for firmware/settings comparisons,
then report added-sensor gains separately. Heterogeneous fleets may allocate senses
to different roles. Rotate roles and placement across runs. Corroboration must
account for shared causes such as one speaker exciting several microphones or
one light affecting several optical sensors.

The recording camera remains an observer by default. Feeding its images to agents
creates an explicit vision-enabled condition with documented field of view and
latency. Link those observations and actuator outcomes to the existing run journal
and media manifest. Every new modality adds its own calibration and acceptance
step before it contributes to an improvement claim.

## Friction that tests the learned behaviour

Kulira's model proposes actions through the existing validated execution path.
An acoustic actuator and its measured stop behaviour are implementation gates.
Record proposed, accepted, actually emitted and observed disturbances separately.
A pure software injection into extracted features is labelled as a simulated
condition. Physical playback requires a recorded stimulus and actuator receipt.

| Treatment | Question |
|---|---|
| Bounded room noise or overlapping motifs | Can nodes wait, repeat or use redundancy when signals are masked? |
| Replayed phrases or imitated motifs | Can they handle stale or misleading claims about a cue or source? |
| Misleading timing cues | Can the group recover tempo and participation after a distraction? |
| Scheduled silence or a missing participant | Can others adapt without inventing a response? |
| Delayed, dropped or conflicting experimental messages in a declared radio-assisted condition | Does the policy distinguish absent, stale and contradictory information? |

An acoustic motif's claimed identity remains uncertain until supported by the
experiment's attribution method. A recording of one phrase replayed twice carries
one underlying observation. Log attributed source and uncertainty separately.

Set named targets, duration, frequency range, calibrated sound level, duty cycle
and stop latency before each campaign. Begin at low output with a measured limit
for the actual room. Cap simultaneous emitters and mute on clipping, sustained
feedback or an expired run lease. Independent stop and recovery must remain
available, with the existing one-second Kulira stop bound verified on the actuator.
Use only approved experimental channels and owned lab equipment. Preserve the
management and evidence paths required by the architecture.

## Comparing generations fairly

Pre-register task, scorer, baselines, training budget, fault budget, minimum useful
gain, allowable regressions, seed sets and replicate count before candidate work.
Cross clean/impaired training with clean/impaired evaluation. Compare each candidate
with the frozen baseline under matched cues, duration, acoustic output and compute
budgets. Include isolated/private-cue, fixed-protocol and shuffled-message controls.
Keep prerecorded common music as a separately labelled stimulus condition.

Freeze waveform assets, disturbance schedules and adversary versions for paired
comparisons. Evaluate an adaptive adversary separately and log its observations,
proposals and actions. Keep unseen seeds and disturbance combinations sealed from
both candidate designers and the adaptive adversary. Use fresh holdouts after a
selection decision exposes a test set. Counterbalance physical run order and repeat
pairs across sessions. Seed equality controls the script, while room acoustics,
background noise and hardware variation must be measured on each run.

| Dimension | Record and compare |
|---|---|
| Communication | Decoding accuracy, confusion counts, abstentions, false claims accepted and decision latency |
| Cooperation | Per-episode task gain over private-cue and fixed-protocol controls at matched budgets |
| Performance | Turn collisions, participation fairness, phase error when rhythm is the task, motif diversity |
| Resilience | Score versus disturbance level, time to recover, persistent exclusion and failure count |
| Cost and health | Output duty cycle, measured power where available, clipping, audio underruns, render timing, heap and journal gaps |
| Learning and evolution | Gain versus training exposure, retained ability after restart, generalisation and accepted/rejected candidates |

Report paired episode differences, sample counts and uncertainty. Nodes within one
run share a room and are correlated. Preserve failures and inconclusive runs.
Estimate power explicitly when measurement is unavailable. Timing metrics require
a measured clock-alignment error below the tolerance used by the scorer.

Assessors use the existing sixteen-lane model matrix and cite node events. The
coordinator may select settings, learning-rule or firmware candidates, including
heterogeneous fleet compositions. Store parent/candidate IDs, source and binary
hashes, per-node settings and learned-state hashes, model/prompt provenance, training
budget, scorer version and the selection reason. Reset or restore learned state
consistently between comparisons. Separate within-run adaptation from an inherited
firmware/settings change. A successful build, deployed candidate and measured gain
are separate milestones. Review whole fleet compositions and rotate candidate
assignments across cells to check positional effects.

Use the existing isolated build and serialised deployment executors. Qualify
candidates through build checks, a one-node canary and an instrumented pair before
fleet evaluation. Promote only after the pre-registered held-out gates and
physical validation pass. Retain the previous binary, settings and learned state for
rollback. Logs and adversarial payloads remain untrusted evidence during review.

## Camera, sound and telemetry as one experiment record

For each run, keep a private manifest linking the run ID to camera video, room
audio, per-node journals, director truth, stimulus and disturbance assets, firmware
composition and deterministic score outputs. Include hashes, original file names,
media timebase, capture settings, clock offsets, drift/error estimates and gaps.
Each node event includes logical node ID, boot/run ID, sequence, local timestamp,
clock uncertainty, policy/settings version, observation reference, selected action
and a concise reason code. Link sound events to motif and playback intervals,
received features and subsequent decisions. Record gaps explicitly. Clock
discipline and media alignment are implementation gates.

Record a visible and audible synchronisation slate before the scored interval,
then reset episode state. A closing slate measures drift. Exclude these slates from
training and scoring. Keep camera position, framing, exposure, microphone placement
and gain consistent. Record automatic gain or exposure when they cannot be locked.
Keep original audio and full-length runs for analysis. Captions and edited montages
reference source timestamps and disclose any playback or sound-level changes.

Create early-versus-later comparisons from preselected matched runs and equal time
windows. Display generation, seed, condition and key scores beside each clip.
Include a failed or inconclusive comparison. Describe collection progress and
missing telemetry so an attractive recording cannot substitute for a scored run.
Keep real-node journals, private identities and raw recordings in private storage.
Public material follows repository policy with synthetic fixtures, reviewed
aggregate results and separately reviewed demonstration media.

## Implementation milestones

1. **Single-node input and output.** Port a licensed Patternflow preset, connect real
   microphone features, produce bounded sound, verify mute/stop, frame timing,
   source attribution limits and recovery. Test synthetic silence, clipping,
   tones, stale input, queue saturation and self-output exclusion first.
2. **Instrumented pair.** Add call-and-response, local event journals and aligned
   camera/audio capture. Repeat with a muted sender and disabled coupling.
3. **Scored communication.** Use the existing host acoustic model as a reference
   and validate its assumptions against pair recordings. Implement the private-cue
   task, deterministic scorer,
   fixed protocol, training/evaluation split and reproducible state resets.
4. **Bounded adversity.** Add the gated acoustic actuator, frozen replay stimuli
   and graded treatments. Verify stop timing, evidence completeness and recovery.
5. **Fleet evolution.** Scale through canaries to sixteen nodes, run the Muse review
   loop, compare homogeneous and heterogeneous candidates, and publish reviewed
   aggregate findings with matched early/later recordings.

Each milestone needs reproducible build/configuration provenance and measured
acceptance before the next physical scale-up. Concrete thresholds belong in the
campaign pre-registration after calibration. The first deliverable is the
single-node measured sound-to-pattern loop and its recording.

## Appendix: optional modules (proposed, not scored)

Optional modules extend the same scenario through declared conditions. The ideas
below are proposed capabilities, subject to exact-module and board compatibility.

| Input or output | Possible experiment | Controlled friction |
|---|---|---|
| Existing microphones and speakers | Acoustic motifs, listening turns and musical responses | Overlapping sound, replay and misleading motifs |
| Existing IMU | A moved or tapped node starts a rhythmic phrase | Unexpected motion or recorded feature perturbations |
| Existing temperature/humidity sensing | Patterns reflect local environmental changes | Baseline drift or stale readings |
| Vision | Observe another panel's dance or respond to human gestures | Occlusion, changed lighting or replayed images |
| LiDAR / time-of-flight ranging | Distance changes tempo or a node's participation | Partial occlusion or missing range samples |
| mmWave | Presence or movement changes group roles | Distractors, changed placement or missing reports |
| IR, UV or lux sensors | Compare optical observations or respond to light cues | Controlled ambient changes or recorded feature perturbations |
| Ultrasonic ranging | Proximity shapes call-and-response | Multiple-emitter cross-talk or delayed samples |
| Optional actuators | A bounded physical movement or haptic response accompanies a phrase | Delayed or unavailable actuator feedback |

