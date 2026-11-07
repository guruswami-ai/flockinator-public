# Display states and source-version compatibility

Source audit at public revision `5f102de` (2026-11-07). These are presentation
contracts, not evidence of hardware deployment or independent node reasoning.
Historical captures retain the vocabulary of their recorded revision.

## The three catalogues are different

| Surface | Source | States and scope |
|---|---|---|
| Node and handheld shared model | [model.h](../firmware/shared/recon/model.h) | 30 states; numeric order is part of the status protocol |
| Illustrated guide | [states.json](scenarios/quadcopter-survey/states.json) | 25 selected explanatory states; omits EVENT, MARK, FRIEND, TARGET and BLANK |
| Browser mission preview | [renderer.mjs](../previews/recon-hud/renderer.mjs) | 25 legacy renderer keys; includes ENGAGE and ZOOM (displayed as EVENT and MARK), omits APPROVED, ORDERS, TAKEOFF, BLANK and READY from this exported list |

The browser can separately render preparation states used by its timeline. Its
exported list is not a firmware enum or a promise of state-for-state parity.
The guide thumbnails use the C++ renderer, but its conceptual decision tree is
not the complete executable transition graph.

## Existing vocabulary and interpretation

| Current shared-model value | Legacy label | Interpretation / limit |
|---|---|---|
| State 6: EVENT | ENGAGE | Scripted close-inspection/event presentation; no actuator command |
| State 8: MARK | KILL; browser internal ZOOM | Authored terminal presentation. Renaming the label did not turn it into a successful rescue |
| State 22: FRIEND | FRIEND | Scripted contact classification; a CREW interpretation remains narrative |
| State 23: TARGET | TARGET | Scripted classified point; does not establish a verified survivor/DIGPOINT |
| Overview 1: OM | OM | On mission in the simulated timeline |
| Overview 2: DOWN | KIA | Simulated unavailable/failure outcome |
| Overview 3: LOST | MIA | Simulated missing-link or energy outcome; distinguish from state 7 LOST, which means the observation was lost |

The follow-up adapter repair accepts current EVENT/MARK reports and historical
ENGAGE/KILL aliases in slots 6/8. Host-generated state names use EVENT/MARK. The
browser retains ENGAGE/ZOOM internally for timeline compatibility but displays
EVENT/MARK. Numeric slots and scripted endings are unchanged.

The mixed-outcome timeline selects MARK for three of ten hash buckets, before
reserve/phase handling; its overview becomes DOWN after ten seconds. That is a
scripted branch, not an empirical 30% failure rate. Broad rescue renaming must
address the transition, ending, renderer and captions together. HEAT, TRACE,
VERIFY, DIG and CARE remain proposed additions, not current enum values.

## Sensor labels are not sensors

The shared firmware enum contains CAM, WH, BH, NV **and IR**. Automatic mission
cycling uses the first four. The mission renderer has explicit CAM/WH/BH palette
branches; other values use its night-style palette, with no dedicated IR strobe
rendering. The separate firmware World renderer also accepts IR and labels it,
without establishing an IR sensor model. The browser mission renderer has an
IR cue effect; browser World view uses the NV terrain palette with an IR header.
None of these graphics establish physical thermal, night-vision or IR sensing.

## Source version versus installed version

The [node CMake file](../firmware/node-platform/CMakeLists.txt) selects `0.10.1`
for the ordinary build, `0.10.2-journal` for `journal-trial`, and
`0.12.0-patternflow-ripples` for `patternflow-trial`. The
[Korvo CMake file](../firmware/korvo-monitor/CMakeLists.txt) declares `0.9.0`.
These are independent targets. A README version, successful build, browser
preview or historical acceptance report cannot determine what runs on a panel;
use a fresh authenticated status record tied to the installed image digest.

## Changing the catalogue

Preserve numeric compatibility or explicitly version a changed protocol. Update
the model/name table, renderer and any host mappings, then the guide driver and
catalogue. Run the [guide regeneration workflow](scenarios/quadcopter-survey/README.md#8-regenerate-and-reuse-the-visuals),
which recreates panels, SVGs, HTML, atlas and manifests. Check hashes and browser
layouts after regeneration. A documentation synonym alone neither changes the
firmware policy nor validates its hardware presentation.
