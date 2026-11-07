# Flockinator survey HUD — animated visual preview

All imagery is procedural and synthetic, rendered into a 64×64 RGBA buffer and displayed with nearest-neighbour scaling. No external assets, network services or installed dependencies are required by the page.

Latest browser revision (**visual study 17**): choose **World view** in the Scene
menu. All sixteen cameras now render shared seeded terrain from continuous pose
snapshots, independently of animation labels. The original Mission loop remains
the default and is unchanged.

World controls: select a node, interrupt/resume its updates, or trigger an impact
from its current displayed pose. Pause freezes the entire preview clock; Restart
restores the authored paths and seed. Sensor and HUD palettes remain selectable.
The native-pixel option shows the actual 64×64 resolution.

The world fixture publishes at 2 Hz; presentation interpolates 500 ms behind it.
A 1.5-second receipt gap freezes and marks the node STALE, clearing its sightings.
Resume blends for 750 ms with a RESYNC label. Invalid or out-of-order data cannot
replace the last valid state. History is capped at four snapshots per node and
performance samples at 256 batches. The page reuses its sixteen frame buffers.

Peer IDs are neutral cyan sightings. Dashed edge cues indicate off-screen peers;
R prefixes a rear sighting. Up to three labels appear in stable ID order, with
an omitted count. White/black pixels are fixed neutral landmarks. These are
explicit fixture reports, not inferred classifications. Positions and altitude
use fictional units. D-- / NR-:-- / BAT? mean no corresponding value was supplied.
IR currently uses the NV terrain palette with an IR header; no IR sensor model
or strobe detection is implemented in World view.

Impact is an authored effect, not dynamics: two seconds to ground, one second
stationary dirt, five seconds of static, then stationary dirt until Restart.
These are source times; the sampled display follows the interpolation delay.
Camera position/orientation at entry comes from the selected displayed view.

Implementation: `world-view.mjs` (pure validation/projection/pixels),
`world-playback.mjs` (bounded sampling/effects), `world-fixture.mjs` (local data)
and `app.mjs` (controls/render scheduling). Snapshot coordinates are +X east,
+Y north, +Z up; heading clockwise from +Y, pitch positive up, roll rotates camera
right toward up. There is no external snapshot endpoint in this milestone.

Manual preview from the repository root (Python standard library only):

```sh
uv run --no-project python previews/recon-hud/serve.py
# open http://127.0.0.1:8766/ in a browser
```

Check the Scene menu, node selection, pause/restart and stale/resync controls
described above. Starting the server is not an automated test run. The original
preview test suite and browser harnesses are not bundled in this public subset,
so this README does not claim a current passing test count.

The browser milestone itself did not change firmware. A subsequent port was
recorded as firmware 0.9.0; its device deployment evidence is private and is
not bundled here. Browser behaviour does not establish device acceptance.

Previous browser revision (**visual study 16**): CRASH tumbles down into textured
dirt, then holds a stationary ground-only image until SIGNAL LOST starts at
three seconds. No horizon or reticle remains after impact. The HUD stays upright
and the lower detail changes from TUMBLE to GROUND. All ten variants and sensor
modes retain this ending. Browser only; firmware remains unchanged.


State catalogue and scenario detail: [docs/scenarios/quadcopter-survey](../../docs/scenarios/quadcopter-survey/README.md). This preview is a scripted visualisation, not live telemetry or inference.

The guide is a curated subset, not the entire renderer enum. See the
[state compatibility map](../../docs/state-compatibility.md) for legacy aliases,
sensor rendering limits and source-version boundaries.
