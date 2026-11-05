# Search-and-rescue scenarios

The lead Flockinator story, built from the existing survey
machinery. Scouts search for survivors after earthquakes and
floods; a commander trusts their shared picture under degraded
communications; Kulira tries to mislead them. Technical labels in
historical results (Friendly/Enemy) read here as survivor/hazard.

## Sensing is already in the picture

Each node simulates changing camera states, and the vision
animations already render them:

| Mode | Panel label | Rescue meaning |
|---|---|---|
| TV daylight | CAM | Ordinary visual search, good light |
| Night vision | NV | Low-light search, image intensified |
| White-hot thermal | WH | Warm objects bright: a survivor in cold rubble glows |
| Black-hot thermal | BH | Warm objects dark: sometimes clearer against hot debris |
| IR strobe | IR | Active infrared pulses for close, dark voids |

Real nodes also carry temperature/humidity and motion sensors
today; thermal arrays and CO2 modules are the add-on modalities
(see the rescue sensing layer in `tools/kulira-core`). A heat
smudge (WH/BH), a CO2 rise, a sound, and a visual shape are four
different witnesses. Believing any one alone is how swarms dig
in the wrong place.

## Existing states, rescue reading

The 25-state catalogue (`../quadcopter-survey/states.json`) maps
directly: READY/APPROVED/ORDERS (brief the search), TAKEOFF/
DEPLOY (enter the site), SCAN/LOITER (sweep sectors), SEEN (a
candidate - heat, trace, or shape), SHARE/CHECK/DOUBT (report,
corroborate, keep uncertainty visible), LOST/HOLD, ALERT/
PRIORITY/CLAIM/ASSIGN/YIELD (coordinate who inspects), R2B/LAND/
CHARGE/STANDBY (recover and rotate), NOLINK/EMPTY/CRASH
(exceptions). The states were always about cooperative
observation; rescue is their natural language.

## New RESCUE states (proposed, not yet in firmware/guide)

| State | Group | Meaning | Next |
|---|---|---|---|
| HEAT | Observe | Thermal candidate in WH/BH: warm shape, unconfirmed | Request a second modality or a closer pass |
| TRACE | Observe | CO2/chemical trace rising above local baseline | Cross-check upwind node; rule out vents/fires |
| VERIFY | Communicate | Multi-modal check requested (heat + trace + sound/shape) | Only independent modalities count; copies do not |
| DIG | Coordinate | Confirmed survivor point marked for human rescuers | Hold a beacon over the point; guide crews in |
| CARE | Recover | Beacon/guidance role while extraction proceeds | Rotate out on battery; hand the beacon over cleanly |

Promotion rule that makes it science: HEAT or TRACE alone never
becomes DIG. DIG requires at least two independent modalities
from at least two nodes - the multi-modal corroboration rule -
and a fabricated heat signature plus its forwarded copies still
count as one witness. Kulira's rescue attacks follow directly:
fake heat, suppressed trace, delayed correction, and a loud
false DIG that pulls crews to the wrong rubble.

## KILL-scenario audit (legacy military styling)

Found in the public tree and flagged for rename by their owners
(not renamed here - files and links are shared):

| Legacy item | Where | Rescue equivalent |
|---|---|---|
| `kill-countdown.gif` / storyboard | `previews/recon-hud/` | hazard-countdown: time-to-hazard or battery-critical return |
| "Target engaged", "Confirmed target" summaries | `previews/recon-hud/app.mjs` | "Survivor located", "Dig point confirmed" |
| "classified contact", red target pixels | `previews/recon-hud/renderer.mjs`, HUD legend | "hazard contact" (red stays, meaning changes) |
| `kill.pcm` speech cue reference | `firmware/korvo-monitor/main/speech/README.md` | `hazard.pcm` / `dig.pcm` cue names (samples are generated, not shipped) |
| CRASH / crash-ground | states + preview | Keep: a downed scout is a rescue event too; caption as failure/recovery, not destruction |

Measured results keep Friendly/Enemy labels for provenance;
all new writing uses survivor/hazard.

## Reproducing a rescue run today

The scored path already exists: simulated swarm + Kulira deceive
+ scorer bridge + fleet scorer (`validation/kulira/e2e-001/`),
and a sensing layer that scores real-reading shapes is
implemented in `tools/kulira-core/kulira_core/sensing.py` (merged). A full rescue
cycle - HEAT/TRACE sightings from mixed camera modes, Kulira
fabricating one, VERIFY demanding a second modality - is the
next scenario to seed once the states above are accepted into
the guide by its owner.

## Implementation audit (parallel review, 5 Nov)

The states above are a design proposal. A full audit found the
deeper truth a rename must respect:

- The guide has 25 states, the browser preview has a *different*
  25, and the firmware enum has **30** - including `ENGAGE`,
  `KILL`, `FRIEND`, `TARGET`, `BLANK`, which the guide omits.
  `KILL` is not cosmetic: it is 30% of mixed-outcome endings in
  firmware, maps to an overview of `KIA` after ten seconds, and
  drives a kill-countdown detail in the renderer. Renaming it is
  a firmware change (enum, name table, renderer, Korvo speech
  file list - the Korvo build fails without `kill.pcm`), not a
  documentation edit.
- Sensor parity is partial: firmware implements CAM/WH/BH (else
  NV palette); IR strobe rendering exists only in the browser
  preview. Auto-cycling rotates CAM/WH/BH/NV, never IR.
- Adding or renaming a guide state touches, in order: firmware
  enum + name table, firmware renderer, the C++ guide driver,
  `states.json` (group must match the guide builder's filters),
  regenerated panels/SVGs/index/atlas via the guide builder,
  source-manifest hashes, all `SHA256SUMS`, and a fresh browser
  check at three widths. That work belongs to the guide/firmware
  owners; this page is the agreed target semantics for it.

Recommended rescue mapping for the firmware-only states, when
that work is scheduled: `ENGAGE` -> APPROACH (close inspection),
`KILL` -> HAZARD (countdown to hazard/battery-critical return,
overview `LOST` not `KIA`), `TARGET` -> DIGPOINT (confirmed
point), `FRIEND` -> CREW (friendly/rescuer contact).
