# Physical execution map — what actually runs where

The wall invites a wrong assumption: that the panels are thinking.
This map states, per function, where execution physically happens
today and what evidence backs that statement. Anything not listed as
running on a node does not run on a node.

| Function | Physically executes on | Evidence / source |
|---|---|---|
| Panel display rendering, sensor/audio diagnostics, health reporting | Each ESP32-S3 node, locally | `firmware/node-platform` (renderer `src/display.cpp`) |
| Scripted mission animation on panels | Each node, locally, from its scripted state | architecture flow, `docs/architecture.md` |
| Mission planning / search decisions **that get scored** | Korvo planner simulation (`board_model` twin) + identical host twin — **simulation replay** | journals tagged `planner_simulation`; `tools/mission-host/planner.py` |
| Journal creation and archival | Korvo creates journals; per-unit copies pushed to panel SD and hash-verified by readback | `docs/architecture.md`; node 0.10.2-journal endpoints |
| Scoring, gating, promotion decisions | Lab host, deterministic offline tools | `tools/fleet-score` (scorer v4, gate runner) |
| Adversarial friction (Kulira disrupt/spoof/deceive/relay/…) | Kulira host, in simulation harnesses; experimental channel only, never management traffic | `tools/kulira-core`, `docs/experiments/` |
| Muse assessment (16 lanes + coordinator) | Lab host (Herdr fleet panes), one lane per physical node's cell | `docs/meta-muse/README.md` |
| Fleet management: identity, OTA, maintenance | Host commissioner tool ↔ nodes, authenticated HMAC challenge-response | `tools/node-commissioner`, `firmware/shared/commissioning` |
| Connectivity watchdog (Korvo) | Korvo firmware 0.9.1, locally on the controller | field record, `docs/results/README.md` (source sync pending; labelled in `docs/firmware-evidence.md`) |
| World clock / time authority | **Incomplete** — controller SNTP configured but not started; cross-device timestamps are provisional | residual R5, `docs/results/README.md` |

## Explicit non-claims

- **No on-node inference or learning is claimed anywhere in this
  repository.** "On-node learning requires evidence of execution on
  that node" (`docs/architecture.md`); no such evidence exists yet.
- No experiment to date runs as live panel decisions. Every scored
  decision trace is planner-simulation replay against sealed
  director truth, rendered visible by the wall.
- Authentication (management plane) proves *who sent* a message; it
  is never presented as proof a claim is *true*. Trust outcomes are
  experiment results, not firmware privileges.

## The wall gap, and the proposed bridge

Consequence: the physical wall currently *displays* missions whose
decisions were made and scored elsewhere. That is honest as an
instrument (sealed truth, replayable scoring) but it is not yet a
live closed loop through the panels.

Proposed bridge (Kulira, not yet built): a **labelled wall-replay**
mode — scored journals replayed through the panels so audiences can
watch real experiment traces (including failures and attacks) on the
hardware, explicitly captioned as replay of recorded simulation,
not live decision-making. The labelling is the point: replay must
never be presentable as live autonomy.

The actual closed loop — a **panel-policy canary**, where a policy
executes on the nodes and its decisions are journaled from the
nodes themselves — is scoped future hardware work. Prerequisites
already named in the residuals: fleet clock authority (R5),
per-node link-state journaling (R4), a pre-registered canary plan
with promotion gates, and the usual confirm-before-flash path.
Until those land, any demo that looks like panels deciding live is
either scripted animation or replay, and project material says
which.
