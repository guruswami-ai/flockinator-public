# Firmware build & test evidence (summary)

This page summarizes the firmware iteration record. It exists because
this repository's public history is a squashed, allowlisted snapshot
of a private working project: per-release build bundles, flash logs,
and validation notes live in the private tree (they contain device
inventory) and cannot be browsed here. Every count below is quoted
from those private records with its source named; where a number
could be re-verified from this public tree, the command is given.
No device identities, addresses, or keys appear on this page.

## Panel-node firmware (ESP32-S3 ×16, `firmware/node-platform`)

Release bundles are kept per version (`firmware/node-platform/releases/`
in the private tree), each with build/validation notes. The bundles
were consolidated into the private baseline on 2026-11-04, so
directory timestamps reflect consolidation, not original build
dates; the chain below is ordered by version, not claimed dates.

| Version | Purpose (from bundle names/notes) |
|---|---|
| 0.2.0–0.4.2 bringup | Board bring-up iterations; 0.4.3 adds SD inspection |
| 0.5.0 / 0.5.1 SD maintenance | Authenticated SD maintenance over Wi-Fi/USB/ESP-NOW relay; all 16 nodes commissioned |
| 0.6.0 avatar · 0.7.0 random expressions | Display/personality layers |
| 0.8.0 / 0.8.1 recon HUD · 0.9.0 world view | Mission visualisation |
| 0.10.0 survey · 0.10.1 mission-world | Survey mission presentation (deployed mission line) |
| 0.10.2-journal | Mission-journal HTTP endpoints; hash-verified journal copies on node SD so journals survive controller outages |
| 0.11.0 / 0.11.1 / 0.12.0 Patternflow trials | Display-trial line (acoustic/pattern experiments); per private bundle notes, deployed fleet-wide as trials with authenticated rollback to 0.10.1 (field record, not public-tree verifiable) |

Negative-test bundles are kept alongside releases and are part of
the evidence, not clutter: `invalid-checksum-0.4.2`,
`invalid-checksum-canary-0.4.2`, `rollback-test-0.3.2`,
`rollback-test-0.4.2` — OTA rejection and two-slot rollback were
exercised with deliberately bad images before the mission line
depended on them.

Test evidence quoted from bundle validation notes:

- **0.5.1 validation** (private bundle
  `releases/0.5.1-sd-maintenance/VALIDATION.md`): 102 host tests +
  14 node native (Unity) tests + 25 management-console native tests
  = **141**, plus shared wire assertions and an HMAC regression;
  both firmware builds succeeded. The same note records the
  on-hardware results as field observations: all 16 nodes reported
  the expected image and valid OTA state; all 16 SD cards passed
  FAT32 format/remount and a 16 MiB write/read comparison.
- **0.11.x trials** (private bundle READMEs
  `releases/0.11.0-patternflow-trial/`, `0.11.1-patternflow-playlist/`):
  43 node native tests passed (suite grew from 14 to 43 across the
  line); host renderer passed ASan/UBSan.
- **Management console** (public-tree verifiable): release
  **0.3.3-missions** (`firmware/management-console/include/console_model.h`),
  30 `RUN_TEST` cases across 3 Unity suites
  (`firmware/management-console/test/`).
- **Current tree (re-countable here):** 11 Unity suites under
  `firmware/node-platform/test/`; 97 pytest functions under
  `tools/node-commissioner/tests/` in this public snapshot
  (107 in the private tree); 13 tests under
  `tools/mission-host/test_*.py` (13/13 passing in the private
  2026-11-05 run; needs pyserial).

## Korvo controller firmware (ESP32-S31, `firmware/korvo-monitor`)

ESP-IDF project; built on the lab host, flashed over serial with
esptool write-hash verification, previous binary staged before each
flash (single factory partition, so rollback = serial reflash of
the staged binary).

**Provenance labelling:** the public `firmware/korvo-monitor` tree
in this repository is at **0.9.0** — it does not yet contain the
0.9.1 watchdog or `/api/health` code. Every 0.9.1 figure in this
section (binary size, sha256, 300 s / 120 s tiers, episode tally)
is therefore a **private-source quotation** from the lab release
store and field logs, unverified from this public tree. Publishing
the 0.9.1 source sync is follow-up work. Binary sizes below are
from the private release-store listing of 2026-11-05.

| Version | Binary (bytes) | What changed |
|---|---:|---|
| 0.7.0 | 1,480,448 | Monitor UI + speech events |
| 0.8.0 | 2,210,880 | Lab host: fleet sweep, web commander |
| 0.9.0 | 2,546,608 | Planner twin (board model), journals to SD |
| 0.9.1 | 2,550,576 · sha256 `b26c651c…8087649` | Connectivity watchdog + `/api/health` counters (2026-11-05) |

0.9.1 exists because of a field fault found the same day: the
controller repeatedly entered an "associated-but-deaf" Wi-Fi state
(associated, IP held, data path blackholed both ways, no disconnect
event; heap/brownout/panic/app-hang excluded from the controller
serial log, private, ≈68k lines at fault-classification time). The
watchdog converts that unbounded outage into a bounded one:
300 s of fleet-sweep silence → forced reconnect → 120 s grace →
logged restart (≤3/hour). Field tally as counted in
[`docs/results/README.md`](results/README.md) (2026-11-05, from
serial-log watchdog lines cross-checked against `/api/health`
counters): **12 episodes, 11 cleared at the reconnect tier
(~303–329 s silence, service back in ~2 s), 1 ended by operator
reboot; the restart tier has never fired**. The soak is continuing,
so this count is a dated snapshot that will drift — the results
README is the canonical public count. (A named design gap: any
single panel success clears escalation — residual R9 in
[`docs/results/README.md`](results/README.md)). The wedge trigger
remains unknown; the firmware contains no hard-coded SSID, password,
IP, or BSSID (verified in source and in the shipped binary's
strings; provisioning is NVS + DHCP).

## Commands (as recorded in the private build notes)

```sh
# Panel nodes — build + native Unity suites (PlatformIO).
# Default env waveshare-s3 builds the 0.10.1-mission-world line.
# Release variants are conditional-compilation envs in platformio.ini:
#   journal-trial     (-DFLOCK_MISSION_JOURNAL=1)   -> 0.10.2-journal
#   patternflow-trial (-DFLOCK_PATTERNFLOW_TRIAL=1) -> 0.11.x/0.12.0 trials
#   rollback-test     (-DFLOCK_TEST_REJECT_BOOT=1)  -> recovery-test image, never USB-flash
pio run  --project-dir firmware/node-platform --environment waveshare-s3
pio run  --project-dir firmware/node-platform --environment journal-trial
pio test --project-dir firmware/node-platform --environment native

# Commissioner / host tooling tests (mission-host has no pyproject;
# run pytest against the directory with a pyserial-capable env)
uv run --project tools/node-commissioner python -m pytest tools/node-commissioner/tests -q
python3 -m pytest tools/mission-host -q

# Korvo controller (ESP-IDF with the S31 dev-kit SDK, preview target;
# see firmware/korvo-monitor/README.md). Flash via esptool, hash-verified.
export KORVO_SDK_PATH="$HOME/esp/esp-dev-kits-s31"
idf.py --preview build
```

## Honest limits of this summary

- Counts dated to their bundle notes; suites have grown since
  (native 14 → 43; commissioner 102 → 107 test functions private,
  97 in this snapshot). Current
  counts above were re-counted from the trees, not re-run end-to-end
  for this page, except where a 2026-11-05 pass is stated.
- Firmware builds are **not bit-reproducible** (embedded timestamps;
  some early builds predate clean-tree discipline). Deployed-source
  provenance is recorded per bundle, but a judge cannot rebuild a
  bit-identical 0.9.1 from source today; the sha256 above identifies
  the exact binary that was flashed and soaked.
- Which exact build each physical node runs today lives in the
  private inventory, not here.
