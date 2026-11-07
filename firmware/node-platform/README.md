# Waveshare node diagnostic firmware

> Management route of record: Korvo controller plus host commissioner
> over authenticated Wi-Fi (per-node keys). LilyGo references in the
> release notes below are historical: that path is legacy/recovery-only
> (ESP-NOW recovery of a node whose Wi-Fi is broken).

The release notes below describe historical capabilities. Private inventory
and deployment records are not included in this public subset; these notes
do not establish the version or acceptance status of a reader's hardware.
See the [build guide](../../docs/build.md) for public build entry points.

## Source variants

The checked-in [CMake selection](CMakeLists.txt) defines three builds; these
are source versions, not assertions about what is deployed:

| PlatformIO environment | Application version | Purpose |
|---|---|---|
| `waveshare-s3` | `0.10.1` | Scripted mission/world presentation |
| `journal-trial` | `0.10.2-journal` | Mission journal variant |
| `patternflow-trial` | `0.12.0-patternflow-ripples` | Patternflow display trial |

The source retains optional host-survey snapshots, local World view, diagnostic
pages, audio/sensor services, authenticated maintenance and SD checks. World
peers and mission sightings are synthetic. Host-survey mode requires its host
and bridge; local scripted presentation does not. See the
[state compatibility map](../../docs/state-compatibility.md) for the guide,
browser and firmware vocabularies. Earlier release/deployment narratives remain
in Git history; actual per-node versions need fresh authenticated status.

Build and test from the repository root, with PlatformIO's `pio` on PATH.
Run these jobs sequentially:

```sh
pio run --project-dir firmware/node-platform --environment waveshare-s3
pio test --project-dir firmware/node-platform --environment native
```

The board configuration is for Waveshare ESP32-S3-N32R16: 32 MB octal flash and 16 MB octal PSRAM. Two 8 MB application slots and a separate identity NVS partition are defined in `partitions.csv`. Dependencies are pinned in `src/idf_component.yml` and `dependencies.lock`. `CONFIG_CODEC_I2C_BACKWARD_COMPATIBLE` must remain disabled: the firmware uses the new IDF I2C driver throughout.

The screen rotates through overview, sensors, peripherals, full-resolution pixel patterns, audio and radio pages. Short BOOT presses advance pages; holding BOOT for one second requests one quiet, finite tone. Brightness starts at 25% with a hard 50% ceiling. Panel and speaker operation require physical observation; neither is established by driver initialisation. The controller can run alone over USB.

SD mounts never autoformat. A successful FAT32 mount performs one isolated 512-byte read/write/delete test per boot, preserving unrelated files. Card enumeration is independent of mounting, so an incompatible filesystem still reports card identity and physical capacity. No microphone recording or live speaker feedback loop runs.

Explicit SD maintenance uses a fresh 120-second card-bound permit, a background worker, one MBR/FAT32 partition and a remount before testing. Quick mode compares 16 MiB. Full mode writes every available data cluster before the separate read pass, using address-dependent data across files of at most 1 GiB; it takes many hours. Reports distinguish physical, formatted and tested capacity. Successful tests remove their files. Failure leaves evidence/files for diagnosis; restart marks an unfinished job interrupted and never resumes erasure. OTA is rejected while a storage job holds the maintenance resource; health, sensors and panel output continue. See [SD usage](../../tools/node-commissioner/README.md#sd-maintenance).

Maintenance uses private per-node HMAC keys, fresh boot nonces and one-use counters. Status and commands bind to the factory MAC. OTA writes only the inactive slot, verifies the complete image and digest, then validates the new boot after core services start. Wi-Fi and ESP-NOW use the same radio channel; a second real node is required for peer acceptance. See the [host client](../../tools/node-commissioner/README.md).

`rollback-test` is an intentionally failing recovery-test environment. **Never flash it over USB or distribute it as normal firmware.** Its only purpose is to prove rollback when installed in an inactive OTA slot with a previously validated application available. Normal builds use `waveshare-s3`.

Public native tests and builds verify source-level behaviour only. Device
commissioning, OTA rollback, card capacity, panel/speaker acceptance and combined
hardware soak require separately retained observations for the exact build.
Run native tests and firmware builds sequentially: PlatformIO auto-cleaning can
remove the shared build directory if these run concurrently.
