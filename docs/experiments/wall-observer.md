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
- **Video must be zoomed out to ~0.6x** (ultrawide). At 1.0x the
  16:9 video crops the wall to a central band; the keyboard zoom
  keys do nothing, but the on-screen slider works: tap the preview,
  drag the right-edge zoom thumb to the bottom. The tool does this
  before every recording because the setting does not persist
  across a CAMERA->VIDEO switch. Verified live: at 0.6x the
  recorded frame (1080x1920) contains all 16 panels, text legible
  in every cell - see `validation/wall-observer/demo-001/sample-video-frame.jpg`
  (extracted from a silent, audio-stripped zoom recording).
  Still bursts remain the higher-resolution record.
- **Video ships silent or not at all.** Household/lab audio is not
  publishable data. The stored video has its audio track stripped
  with ffmpeg at capture time and the manifest records
  `audio_stripped` / `publishable`; the phone's camera microphone
  permission is also revoked on the rig. An unstripped video is
  marked not publishable.

## Calibration result (same-state noise floor)

Two bursts of the unchanged all-`READY` wall, phases `beginning` and
`end`, 3 frames each (trial `wall-observer-demo-001`; summary in
`validation/wall-observer/demo-001/` - frames are retained privately,
so this calibration is not independently re-verifiable from the repo):

- mean per-cell RGB change **1.45**, max **4.03**, 0 of 16 cells over
  delta 25; the 8 s video stored silent-only (`audio_stripped: true`).

That is the visual noise floor. A real state change in a cell must
beat it by an order of magnitude before we claim the wall changed —
the same pre-registered discipline as the scored experiments.

## Mission slate (checksum frame)

Every published sequence carries a slate at its start and end, so a
clip separated from its manifest still identifies itself
(`kulira_core/slate.py`, format `flockinator-slate/1`):

- Human text: `MISSION <id>`, UTC start, `FLOCK-<16 hex>` checksum.
- One QR payload (compact JSON, v1, additive-only fields):
  mission, UTC, checksum, telemetry-hash prefix. Decoders must run
  `validate_qr_payload` and reject anything else.
- The checksum is derived - sha256 over mission id, start UTC,
  telemetry hash and the sorted frame hashes - so any holder of the
  data can recompute it. Slates are generated into the dataset
  bundle (`web/slate.png`, `web/slate-start.mp4`, `web/slate-end.mp4`)
  by `kulira dataset build`; verified by an independent QR decode.

Tile distribution (coordinator companion, implemented here):
`kulira wall tiles --image <256x256 graphic> --out <dir>` splits any
wall graphic into 16 addressed tiles (`flockinator-tiles/1`
manifest: node, row/col, offset, per-tile sha256, and the horizontal
flip the rear-facing camera requires, recorded not assumed). A
node can verify its tile against the manifest before displaying it.
Proven end to end: a slate QR tiled, reassembled as the camera sees
it, and decoded back to the identical checksum.

Panel-side spec (firmware owner, tracked in the slate issue): at
mission start and end, hold a slate on the wall for at least 3 s -
mission text across the top tiles, the date beneath it, and ONE QR
spanning all 16 tiles. The wall is a 256x256 canvas (16 tiles of
64x64), so a QR of version 8 or below (49x49 modules plus quiet
zone) keeps modules near 4 panel pixels and roughly 20 camera
pixels in a 1080-wide capture. Per-tile QR codes are not viable at
64x64; per-tile critical data (for example firmware version) belongs
in a text line on that tile, which our captures already read
reliably.

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
