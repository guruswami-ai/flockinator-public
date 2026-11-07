# Reading the Flockinator swarm

A visual field guide to the **search-and-rescue scout survey rehearsal** (non-weaponized quadcopter platform): what a
panel shows, what the state is intended to mean, and what evidence would justify
the next action.

Open [the published illustrated guide](https://guruswami-ai.github.io/flockinator-public/),
or open `index.html` locally. Use the standalone
[timeline](assets/survey-timeline.svg), [decision tree](assets/survey-decision-tree.svg)
and [communication strip](assets/communication-strip.svg) in a presentation.

## First, separate the picture from the experiment

The physical ESP32 panels render a shared, scripted simulation. They make node
roles visible. A smooth flight animation is not a flight controller; a battery
icon is not a physical measurement; a green receive flash is not proof that a
radio message arrived. The source describes the panel model as scripted display
theatre, with no navigation, inference or actuator outputs.

This guide contains three deliberately different things:

| Layer | What it establishes | What it does not establish |
| --- | --- | --- |
| Code-rendered panel thumbnails | How the firmware draws a selected state and communication overlay | That the pictured event occurred on hardware |
| Explanatory decision tree and “thinking” captions | A vocabulary for narrating cooperative survey decisions | The actual transition algorithm or a captured private reasoning trace |
| An instrumented experiment with observations, messages, decisions and outcomes | Evidence that a particular message or policy changed a measured result | General intelligence or real-world aircraft performance |

The first-person captions are **presenter explanations**. They should be read as
“this state represents…”, not as text recovered from a drone's internal thoughts.
A retrospective explanation from a Muse reviewer is also different from a reason
code recorded when the node made its decision.

The 25 illustrated states are a selected subset of the 30-state shared model.
See the [state compatibility map](../../state-compatibility.md) for omitted
states, browser aliases and sensor-rendering limits.

## 1. Mission objectives and the visible story

The current scripted model exposes the goals **Observe**, **Compare reports** and
**Recovery**. The ORDERS panel renders them as SURVEY, COMPARE and RECOVER. It also
shows SHARE DATA and KEEP CLEAR. These labels are the mission's narrative context.

- **Observe:** follow the survey, notice a candidate observation and make it
  available for review.
- **Compare reports:** foreground verification and unresolved disagreements.
- **Recovery:** foreground availability and the return sequence.

The state vocabulary supports a story with preparation, observation, cooperation
and recovery. Individual panels need not visit every state, nor visit them in the
order shown below. The illustrated tree is an interpretation, not an executable
policy and not a real-aircraft operating procedure.

![Selected survey milestones with panel thumbnails](assets/survey-timeline.svg)

**Prepare:** READY → APPROVED → ORDERS → TAKEOFF → DEPLOY.

**Observe and compare:** SCAN / LOITER → SEEN → SHARE → CHECK. If the observation
is lost, LOST represents searching again. If reports conflict, DOUBT makes the
uncertainty visible. HOLD represents waiting for coordination.

**Recover:** R2B → LAND → CHARGE / STANDBY. Recovery can branch from observation;
it is not contingent on obtaining a positive observation. A run with no finding
is a valid outcome.

The scripted battery and altitude graphics are presentation values. The guide
intentionally supplies no operational battery threshold, navigation procedure or
real-world flight envelope.

## 2. A conceptual decision tree

![Conceptual survey decision tree](assets/survey-decision-tree.svg)

The questions to narrate are:

1. **What objective is active?** Identify the authorised rehearsal and its goal.
2. **Should this survey continue?** Consider completion and the represented
   recovery condition. Waiting or returning can be the correct outcome.
3. **What can this node actually observe?** Distinguish a fresh private observation
   from a peer's report, an old view or absent information.
4. **Would another viewpoint resolve uncertainty?** SHARE and CHECK express the
   invitation to corroborate an observation.
5. **Is the evidence independent and consistent?** Two repeated claims from one
   underlying source do not become two independent observations. Keep disagreement
   visible rather than manufacturing certainty.
6. **What changed, and what happened next?** Record the observation, message,
   decision and result before claiming that cooperation helped.

The existing state scheduler does not evaluate this diagram. To describe a real
run's decision path, use that run's scenario version and event records. Label a
future policy implementation separately from the current presentation.

## 3. What the flashing border means

The firmware renderer draws a **one-pixel perimeter** around the 64 × 64 frame.
The source colours are converted to RGB565 before being sent to the panel:

| Cue | Source colour | Intended meaning | Example footer |
| --- | --- | --- | --- |
| Orange | `#ff8a24` | TX: this node is the sender | `TX B1` or `TX ALL` |
| Green | `#32ed70` | RX: this node is the receiver | `RX A1` |

The actual rhythm is a short double flash:

| Event age | Border | TX/RX footer |
| --- | --- | --- |
| 0 to less than 250 ms | On | Visible |
| 250 to less than 375 ms | Off | Still visible |
| 375 to less than 625 ms | On | Visible |
| 625 ms onward | Off | Normal state footer returns |

![Paired transmitter and receiver panels through the double flash](assets/communication-strip.svg)

For the illustrated unicast event, **A1 sends to B1**. A1 displays `TX B1` in
orange; B1 displays `RX A1` in green. A broadcast uses `TX ALL` at the source and
`RX A1` at each illustrated recipient. The footer names the peer; it is not the
payload, a confidence value or an acknowledgement.

The overlay temporarily replaces normal detail text such as REPORT or VERIFY.
READY, APPROVED, ORDERS and BLANK return before the general border overlay. Other
visual effects can use a red border; red is not a third communication direction.

### What is implemented today

The scripted panel runtime derives event participants and ages from the scenario.
The browser preview likewise constructs both endpoints of a presentation event.
Synchronous orange and green flashes therefore demonstrate a consistent **visual
representation**. They do not measure radio delivery, latency, packet loss,
acknowledgement, agreement or a resulting change of decision.

In the general browser preview, SHARE represents a paired event. ALERT, ASSIGN
and FRIEND are eligible broadcast presentation states. The separate coordination
fixture explicitly schedules its own source, claims and assignment broadcast.
These fixtures are not interchangeable with measured network telemetry.

### Explaining “come and look” accurately

A useful narration is: “A1 has a candidate observation and offers a report. B1
receives the represented request and enters a verification role. We now need to
see whether B1's own observation supports, contradicts or fails to resolve it.”

That narration explains SHARE / REPORT and CHECK / VERIFY. It is **not a literal
message decoded from the pixels**. An experiment must supply the actual report
content, source, receipt record and next action before we can say that a node
responded to a request to inspect something.

Receiving is not believing. Believing is not agreement. Agreement is not proof
that the underlying observation was correct.

## 4. The twelve-second coordination illustration

This timing is taken from `previews/recon-hud/coordination.mjs`. It describes the
**browser presentation fixture**, not the complete firmware mission timeline.
The source, candidate owner and challenger are deterministically selected; P1/P2
labels are presentation labels rather than inferred priorities.

| Preview phase | What the group shows | What the event represents |
| --- | --- | --- |
| 0–2 s: ALERT | The shared beacon P1 is announced | The source broadcasts at 0 s |
| 2–4 s: PRIORITY | P1 FIRST | The scenario's task order is displayed; no new message event |
| 4–6 s: CLAIM | Two selected nodes show CLAIM; others show CHECK | Owner candidate → source at 4.000 s; challenger → source at 4.875 s |
| 6–10 s: ASSIGN | One node shows ASSIGN; other nodes show YIELD | Source broadcasts at 6 s; OWNER identifies the chosen observer |
| 10–12 s: OBSERVE | Owner shows SEEN; other nodes show SCAN | The group returns to observation roles; no new message event |

**Important identity distinction:** the source that broadcasts the assignment can
be different from the owner named on the panel. “I transmitted the assignment”
and “I own the observation task” are different roles.

This illustration explains how duplicate ownership might be avoided. It does
not establish a learned auction, optimal selection or a distributed-consensus
implementation.

## 5. State atlas

All thumbnails below use `recon::render`, the firmware renderer. Most fixtures
show A1 at phase 2.1 s, with a fixed camera/variation, sensor mode and synthetic
scene context. APPROVED uses 0.1 s so its blinking text is visible; CRASH uses
1.2 s. The manifest records the inputs. These are selected survey, coordination
and health states, not every effect in the broader display catalogue.

<!-- STATE_ATLAS_START -->

### READY — Waiting for a mission

![READY firmware-rendered panel](assets/READY.png)

**Explanatory caption:** “I have no active task.”

The panel shows READY and REMOTE START.

**Next question or action:** An operator-authorised rehearsal can begin. Readiness is a display state, not proof that every subsystem passed a pre-flight check.

### APPROVED — Mission acknowledged

![APPROVED firmware-rendered panel](assets/APPROVED.png)

**Explanatory caption:** “The demonstration has been authorised.”

MISSION APPROVED blinks on a black panel.

**Next question or action:** Show the mission briefing. This is not a real aircraft arming signal.

### ORDERS — Understand the objective

![ORDERS firmware-rendered panel](assets/ORDERS.png)

**Explanatory caption:** “My task is to survey, compare reports or recover.”

The briefing shows SURVEY, COMPARE or RECOVER with SHARE DATA and KEEP CLEAR.

**Next question or action:** Interpret later observations against the selected objective. The illustration uses the survey briefing.

### TAKEOFF — Enter the simulated world

![TAKEOFF firmware-rendered panel](assets/TAKEOFF.png)

**Explanatory caption:** “The rehearsal is starting.”

The camera and altitude presentation transition into the flight view.

**Next question or action:** Proceed to the deployment presentation. No motor command is produced by this renderer.

### DEPLOY — Form up

![DEPLOY firmware-rendered panel](assets/DEPLOY.png)

**Explanatory caption:** “I am moving into my assigned part of the scene.”

DEPLOY and FORM UP accompany the simulated movement.

**Next question or action:** Begin the observation phase. The moving picture alone does not establish a computed flight plan.

### SCAN — Look for an observation

![SCAN firmware-rendered panel](assets/SCAN.png)

**Explanatory caption:** “I am looking for something relevant to the task.”

A scanning overlay marks the observation phase.

**Next question or action:** Keep searching, or enter SEEN when the scenario presents a candidate observation.

### LOITER — Continue observing

![LOITER firmware-rendered panel](assets/LOITER.png)

**Explanatory caption:** “I am maintaining an observation role.”

LOITER is accompanied by a GRID or ORBIT caption.

**Next question or action:** Continue observing, respond to a review request, or move into the recovery branch when the scenario requires it.

### SEEN — A candidate observation

![SEEN firmware-rendered panel](assets/SEEN.png)

**Explanatory caption:** “I have noticed something; I have not established what it means.”

A bracket highlights an observation in the scene.

**Next question or action:** Share a report or seek a check. A bracket is not a confidence score or proof of correct identification.

### SHARE — Offer a report

![SHARE firmware-rendered panel](assets/SHARE.png)

**Explanatory caption:** “Another node may benefit from what I observed.”

SHARE normally shows REPORT. During a communication event, the footer can show TX plus the peer label.

**Next question or action:** A receiver can consider the report alongside its own observation. The current scripted flash does not itself deliver a real payload.

### CHECK — Seek corroboration

![CHECK firmware-rendered panel](assets/CHECK.png)

**Explanatory caption:** “I need to compare this report with independent evidence.”

CHECK and VERIFY identify a review state; an RX footer can temporarily replace VERIFY.

**Next question or action:** Continue observation if evidence is incomplete; record agreement or disagreement in an instrumented experiment. Do not equate receipt with agreement.

### DOUBT — Keep uncertainty visible

![DOUBT firmware-rendered panel](assets/DOUBT.png)

**Explanatory caption:** “The available reports do not yet agree.”

DOUBT, a contrasting reticle and the 2 CLAIMS caption show a conflict presentation.

**Next question or action:** Request another check, keep the observation unresolved, or resume the survey. Two claims can repeat the same source and are not necessarily independent.

### LOST — Observation no longer available

![LOST firmware-rendered panel](assets/LOST.png)

**Explanatory caption:** “I cannot currently maintain this observation.”

LOST is accompanied by SEARCH.

**Next question or action:** Revisit the observation task or record that the evidence is unavailable. It does not mean that the network link has failed.

### HOLD — Wait for coordination

![HOLD firmware-rendered panel](assets/HOLD.png)

**Explanatory caption:** “I am waiting for the next task decision.”

HOLD and HQ WAIT distinguish waiting from active observation.

**Next question or action:** Continue when the scenario supplies the next instruction. A waiting panel is not evidence that a model is currently thinking.

### ALERT — Announce a shared observation

![ALERT firmware-rendered panel](assets/ALERT.png)

**Explanatory caption:** “There is a symbolic beacon for the group to review.”

ALERT shows BEACON P1. In the coordination fixture, its source transmits to the other panels.

**Next question or action:** Move into the fixture's review sequence. P1 is a scripted label, not an inferred urgency or confidence value.

### PRIORITY — Display the selected task order

![PRIORITY firmware-rendered panel](assets/PRIORITY.png)

**Explanatory caption:** “The rehearsal is considering P1 first.”

PRIORITY displays P1 FIRST.

**Next question or action:** The fixture presents candidate volunteers. This display does not implement a learned priority calculation.

### CLAIM — Offer to inspect

![CLAIM firmware-rendered panel](assets/CLAIM.png)

**Explanatory caption:** “I am volunteering for this observation task.”

CLAIM displays CLAIM P1. Two predetermined participants send their claims separately to the source in the preview fixture.

**Next question or action:** Wait for the assignment presentation. A claim is an offer, not ownership or evidence that the node is best placed.

### ASSIGN — Show the observation owner

![ASSIGN firmware-rendered panel](assets/ASSIGN.png)

**Explanatory caption:** “I have the observation role for this rehearsal.”

ASSIGN displays OWNER and a node label.

**Next question or action:** The chosen observer continues observing. The fixture chooses the owner deterministically; no bidding optimisation is demonstrated.

### YIELD — Avoid duplicate ownership

![YIELD firmware-rendered panel](assets/YIELD.png)

**Explanatory caption:** “Another node owns this observation task.”

YIELD displays the same OWNER label as the assignment.

**Next question or action:** Other participants can return to their survey roles. This is a presentation of coordination, not proof of distributed consensus.

### R2B — Return to the base

![R2B firmware-rendered panel](assets/R2B.png)

**Explanatory caption:** “This rehearsal is moving into recovery.”

R2B and HOME identify the return presentation.

**Next question or action:** Proceed toward LAND. The example does not specify a real aircraft's reserve threshold or navigation policy.

### LAND — Finish simulated flight

![LAND firmware-rendered panel](assets/LAND.png)

**Explanatory caption:** “I am completing the return sequence.”

The camera/altitude presentation descends into the home view.

**Next question or action:** Show CHARGE or STANDBY according to the scripted outcome.

### CHARGE — Recharge presentation

![CHARGE firmware-rendered panel](assets/CHARGE.png)

**Explanatory caption:** “I am unavailable while the demonstration shows replenishment.”

CHARGE includes an animated battery indicator.

**Next question or action:** Return to standby when the sequence advances. The indicator is simulated, not a measured charging current.

### STANDBY — Ready for the next role

![STANDBY firmware-rendered panel](assets/STANDBY.png)

**Explanatory caption:** “I am waiting at the base.”

STANDBY presents the parked state.

**Next question or action:** Remain available for a subsequent authorised rehearsal.

### NOLINK — Stale view or missing link

![NOLINK firmware-rendered panel](assets/NOLINK.png)

**Explanatory caption:** “I do not have a fresh view to rely on.”

NOLINK freezes the camera presentation and shows an AGE caption.

**Next question or action:** Treat the represented information as stale. In this scripted mode, AGE is scene time rather than measured packet latency.

### EMPTY — Simulated energy exhausted

![EMPTY firmware-rendered panel](assets/EMPTY.png)

**Explanatory caption:** “The rehearsal has reached an energy failure state.”

The battery indicator falls and the view dims.

**Next question or action:** Record the simulated failure outcome. This is not a physical battery measurement or an instruction for aircraft recovery.

### CRASH — Simulated failure outcome

![CRASH firmware-rendered panel](assets/CRASH.png)

**Explanatory caption:** “This run has ended in a simulated failure.”

The view rolls toward the ground, then later shows signal loss.

**Next question or action:** Preserve the event trace for review. The thumbnail shows an early phase of the display sequence, not a photograph or real crash report.

<!-- STATE_ATLAS_END -->

## 6. How a message can contribute to a decision

The separate communication-learning exercise offers a controlled example. Each
listener has a private symbolic sector cue. During training it learns associations
between each sender's symbols and feedback. During held-out evaluation it decodes
available peer cues and combines them with its private cue to choose a sector.
The evaluation records choices and outcomes against separate director truth.

Changing the delivered content, withholding messages or changing the training
condition can reveal whether communication affected the result. This is receiver
learning with assigned sender vocabularies. It is not proof that the rendered
quadcopter state machine learned to fly or invented a language.

When linking that experiment to this guide, show an actual decision record:

| Field | Why it matters |
| --- | --- |
| Run ID, seed, scenario and scorer versions | Identifies the reproducible experiment |
| Node label and firmware/policy version | Identifies which agent actually made the decision |
| Execution location | Distinguishes controller simulation, native node execution and copied records |
| Simulation tick and clock quality | Establishes ordering without implying accurate wall-clock synchronisation |
| Private observation reference | Shows what was known before communication |
| Message ID, source, content reference and send/receive times | Links a report to the recipient's available evidence |
| Selected action and concise reason code | Explains the recorded decision without inventing hidden reasoning |
| Uncertainty, stale/missing data and disagreement | Preserves alternative explanations |
| Outcome and director-truth reference | Supports deterministic scoring after the run |

These are documentation requirements for evidence, not a claim that every field
is implemented in the current journal format. Mark missing fields as missing.

## 7. Showing that cooperation mattered

Use the same seed and private observations to compare delivered messages with
withheld or scrambled messages. Preserve unchanged decisions as well as changed
ones. A failed or null-result run belongs in the evidence alongside successful
examples. Treat independent runs/seeds, not sixteen nodes in one shared run, as
the replication units.

A useful visual explanation has five linked frames:

**Private observation → received report → recorded decision → scored outcome →
matched comparison without useful communication.**

The Muse node reviewers can assess those records, cite the supporting events and
propose a bounded change. The coordinator can compare proposals and choose the
next experiment. A proposal, successful build and deployed image are different
milestones; a gain requires a subsequent comparable evaluation. Model tier is
not a node intelligence score.

The following claims need more than an animation:

- “These nodes communicated”: actual send and receive records.
- “This message changed the decision”: linked observations/actions and a controlled
  comparison, not just a neighbouring flash.
- “The swarm improved”: repeated comparable outcomes, with uncertainty and costs.
- “This physical node learned”: evidence that the decision/model update executed
  on that node, not only on the controller or in a copied SD journal.

## 8. Regenerate and reuse the visuals

Requirements: Python through `uv`, a C++17 compiler named `clang++`, and FFmpeg.
The generator uses Python's standard library and local source files only.

```sh
uv run --no-project docs/scenarios/quadcopter-survey/build-guide.py --repo .
```

For a standalone copy, run `build-guide.py` with `--repo` pointing to the source
checkout. It compiles `render-panels.cpp` into a temporary directory, renders
native 64 × 64 PPM frames, converts them to 256 × 256 PNGs with nearest-neighbour
scaling, and creates three self-contained SVG diagrams and the HTML guide.
It does not open serial ports, contact the controller, run inference or start a
mission. It checks border colours at both flashes and both dark intervals.

The generator overwrites only its own generated PNG, SVG, HTML and manifest
outputs and the marked README atlas. `style.css`, `states.json`, the renderer driver and the prose outside the marked
README atlas are source files. To change the catalogue, update `states.json` and
regenerate; the HTML and marked README atlas are generated from it. The static HTML works offline;
filters and expandable explanations run locally in the browser.

For the public repository, include this entire directory. Figures embed their
thumbnail images, so the SVGs can also be shared independently. Keep native
pixels sharp when resizing; do not redraw them with an image-generation model.

## Source map

- [Firmware renderer](../../../firmware/node-platform/include/recon_render.h):
  pixels, captions, colours, pulse timing and column-first A1/B1/C1/D1 labels.
- [Scripted model](../../../firmware/shared/recon/model.h): states, goals and
  scenario-derived presentation events.
- [Preview messages](../../../previews/recon-hud/communication.mjs): pairing and
  broadcast fixtures.
- [Preview coordination](../../../previews/recon-hud/coordination.mjs): the
  12-second coordination illustration.
- [Communication-learning exercise](../../../tools/mission-host/coordination_lab.py):
  the separate symbolic receiver-learning experiment.
- Existing experiment explanation:
  controls, limitations and reported simulation comparisons.
- [Source hashes and rendering inputs](source-manifest.json): the exact source
  content used for these thumbnails, including uncommitted source changes.

Scope is non-weaponized survey, cooperative observation and recovery. This guide
is not a flight-control manual and does not document attack selection or
engagement logic.
