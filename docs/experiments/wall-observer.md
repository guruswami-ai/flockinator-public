# Wall observer: the microscope lens

Flockinator is a microscope for emergent behaviour. This is the lens
humans look through: a timestamped camera record of the 16 panels,
tied to the mission telemetry, so a reviewer can compare what the
wall *showed* at the beginning, during training, and at the end of a
mission — not only what the journals scored. Statistical improvement
is necessary; it is not sufficient. The wall must visibly change,
cell by cell, and this tool measures by how much.

## Rig

- Google Pixel 9a (GrapheneOS), USB ADB from the Drishdi host,
  centrally mounted facing the panels (it sees them from behind;
  frames are mirror-flipped in analysis).
- `kulira wall capture` (in `tools/kulira-core`) drives the phone.
  Stills in CAMERA (auto) mode; video in VIDEO mode; a hash-chained
  `manifest.jsonl` (same chain as the Kulira attack log) records
  every frame with UTC + host-monotonic timestamps, the measured
  phone-minus-host clock offset at start and end, the mission id,
  and the phase label (`beginning` / `training` / `end`, or any
  label). `--telemetry <file>` hash-links a journal/telemetry file
  into the chain.
- `kulira wall verify --session <dir>` re-checks the chain and every
  frame sha256. `kulira wall report --session <dir> --out <dir>`
  builds `report.html` + `stats.json`: per-cell 4x4 state grids per
  phase, first-vs-last heatmaps, a per-cell RGB-change chart, and
  headline numbers. Every coloured value is also printed as a number.

## Measured camera rules (2026-11-06)

- **CAMERA (auto) only for stills.** NIGHT mode stacks frames and
  beats against the panel multiplex scan, producing thick black
  bands that swallow panel text. NIGHT is refused by the tool.
- **Flicker fallback:** bursts of auto frames. Averaging 3 frames cut
  measured banding 3.5x (row-profile high-frequency std 16 -> 4.6).
- **Video is 16:9 and crops the wall vertically** (still FOV is the
  full 4x4). The zoom keys do not change this. Use native video for
  the central band, and still bursts when the whole wall must be in
  frame; a timelapse assembled from still bursts is the publishable
  full-wall motion record.
- **Video ships silent or not at all.** Household/lab audio is not
  publishable data. The stored video has its audio track stripped
  with ffmpeg at capture time and the manifest records
  `audio_stripped` / `publishable`; the phone's camera microphone
  permission is also revoked on the rig. An unstripped video is
  marked not publishable.

## Calibration result (same-state noise floor)

Two bursts of the unchanged all-`READY` wall, phases `beginning` and
`end`, 3 frames each (trial `wall-observer-demo-001`, evidence in
`validation/wall-observer/demo-001/`):

- mean per-cell RGB change **1.45**, max **4.03**, 0 of 16 cells over
  delta 25; the 8 s video stored silent-only (`audio_stripped: true`).

That is the visual noise floor. A real state change in a cell must
beat it by an order of magnitude before we claim the wall changed —
the same pre-registered discipline as the scored experiments.

## Publishing rules

Publishable by construction: simulated SIM panel states only; no raw
device serial (model + truncated sha256 tag only), no lab network,
no audio. Before publishing any new frame set: re-check at full
resolution for legible screens/people (the failure mode of the first
hero photo), confirm `verify` passes, and confirm every video in the
set has `publishable: true`.

## Next

1. Run it against the next scored mission with phase marks at the
   mission's own beginning / training / end boundaries (--telemetry
   hash-linked to the run journals).
2. Per-cell state classification (colour + text template against the
   known guide states) on top of the grids this report already
   computes; score camera reads against journal ground truth.
