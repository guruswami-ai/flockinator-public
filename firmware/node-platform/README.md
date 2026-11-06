# Waveshare node diagnostic firmware

> Management route of record: Korvo controller plus host commissioner
> over authenticated Wi-Fi (per-node keys). LilyGo references in the
> release notes below are historical: that path is legacy/recovery-only
> (ESP-NOW recovery of a node whose Wi-Fi is broken).

Release **0.10.1** combines the existing automatic mission presentation with
shared terrain and relative peer positions. All sixteen nodes are deployed and
running the repeating mission. It renders locally; no host bridge is needed.
The browser adds a shared-world map. Evidence and limits are in
mission/world validation.
LilyGo firmware and its mission commands are unchanged. The following release
notes describe retained optional modes, not the currently selected presentation.

Release **0.10.0** adds authenticated host-survey snapshots with dynamic fictional
energy, destination distance, reserve labels and stale freeze. All sixteen nodes
are deployed; see `../../docs/validation/survey-deployment/README.md`. The host
and bridge must run for this mode; LilyGo integration is pending.

Release **0.9.0** added continuous local World view: shared seeded terrain,
authored per-node camera poses, neutral peer cues and live pose HUD. World view
starts on boot. Existing mission/avatar/diagnostic modes, Wi-Fi OTA, ESP-NOW
receivers, audio and sensor services are retained. Brightness remains 25%.
World peers are synthetic sightings, not live peer telemetry or inference.

See World view controls and hardware evidence
and the inventory for per-node deployment status.
The existing LilyGo can still launch the legacy mission renderer; its firmware
and UI were not changed by this release. Earlier version notes below describe
retained capabilities.

Version **0.5.1** adds explicit SD maintenance over authenticated Wi-Fi, USB and the LilyGo ESP-NOW relay. All sixteen nodes have been commissioned; current deployed versions and physical acceptance remain in the inventory. Persistent identity, independent 64×64 diagnostic pages, sensors, audio checks and two-slot OTA remain available.

Build and test:

```sh
$HOME run --project-dir firmware/node-platform --environment waveshare-s3
$HOME test --project-dir firmware/node-platform --environment native
```

The board configuration is for Waveshare ESP32-S3-N32R16: 32 MB octal flash and 16 MB octal PSRAM. Two 8 MB application slots and a separate identity NVS partition are defined in `partitions.csv`. Dependencies are pinned in `src/idf_component.yml` and `dependencies.lock`. `CONFIG_CODEC_I2C_BACKWARD_COMPATIBLE` must remain disabled: the firmware uses the new IDF I2C driver throughout.

The screen rotates through overview, sensors, peripherals, full-resolution pixel patterns, audio and radio pages. Short BOOT presses advance pages; holding BOOT for one second requests one quiet, finite tone. Brightness starts at 25% with a hard 50% ceiling. Panel and speaker operation require physical observation; neither is established by driver initialisation. The controller can run alone over USB.

SD mounts never autoformat. A successful FAT32 mount performs one isolated 512-byte read/write/delete test per boot, preserving unrelated files. Card enumeration is independent of mounting, so an incompatible filesystem still reports card identity and physical capacity. No microphone recording or live speaker feedback loop runs.

Explicit SD maintenance uses a fresh 120-second card-bound permit, a background worker, one MBR/FAT32 partition and a remount before testing. Quick mode compares 16 MiB. Full mode writes every available data cluster before the separate read pass, using address-dependent data across files of at most 1 GiB; it takes many hours. Reports distinguish physical, formatted and tested capacity. Successful tests remove their files. Failure leaves evidence/files for diagnosis; restart marks an unfinished job interrupted and never resumes erasure. OTA is rejected while a storage job holds the maintenance resource; health, sensors and panel output continue. See SD usage.

Maintenance uses private per-node HMAC keys, fresh boot nonces and one-use counters. Status and commands bind to the factory MAC. OTA writes only the inactive slot, verifies the complete image and digest, then validates the new boot after core services start. Wi-Fi and ESP-NOW use the same radio channel; a second real node is required for peer acceptance. See the [host client](../../tools/node-commissioner/README.md).

`rollback-test` is an intentionally failing recovery-test environment. **Never flash it over USB or distribute it as normal firmware.** Its only purpose is to prove rollback when installed in an inactive OTA slot with a previously validated application available. A1 recovered successfully in that test. Normal builds use `waveshare-s3`.

Verified: sixteen initial commissioning transactions, authenticated fleet health, Wi-Fi and LilyGo ESP-NOW application deployment, and real 32/64 GB FAT32 format/remount/quick-test canaries. Full capacity results, per-node physical acceptance and a long combined hardware soak remain separately tracked in the task record. Run native tests and firmware builds sequentially: PlatformIO auto-cleaning can remove the shared build directory if these run concurrently.
