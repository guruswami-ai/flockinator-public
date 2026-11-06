# Flockinator LilyGo remote — live integration prototype

> **Status: LEGACY / RECOVERY-ONLY (deprecated, advisory).** The Korvo
> controller plus the host commissioner over authenticated Wi-Fi is the
> management route of record. This handheld prototype is retained only
> as an ESP-NOW recovery route for a node whose Wi-Fi is broken. Do not
> build new features on it; the notes below describe the retained
> prototype as it was, including historical release claims.

Current deployed release: **0.3.3-missions**. Open **Missions** for scenario,
goal, survey duration, repeat, Launch and Stop all. Touch alignment is now under
Diagnostics. Overview displays READY / OM / KIA / MIA / CHARGING with separate
link warnings, in the physical panel arrangement. See the remote guide
and verification.

This PlatformIO project runs the live management remote on the owner's **LilyGo T5 4.7-inch S3, V2.4, with glass capacitive touchscreen**. The MCU is an ESP32-S3 with 16 MB flash and 8 MB PSRAM; the identified console factory/STA MAC is **00:11:22:33:44:55** (example value in this public tree — before building for real hardware, set your own console's factory MAC in `ExpectedMac` in `src/live_link.cpp` and in `firmware/korvo-monitor/main/main.c`'s operator check, or identity verification will refuse every device). This prototype checks that console identity explicitly. It is USB-powered, with no battery or optional expansion header fitted. Neither the expansion header nor the optional touch-wake solder link is required.

The owner approved the live integration on 13 October 2026 in SPEC-management-console.md, SPEC-flock-network.md and SPEC-cluster-deployment.md. The current build version is defined in `include/console_model.h`; actual hardware observations and deployment results are recorded separately from these implemented capabilities.

## Live node status

The 960 × 540 overview contains sixteen independent A1–D4 positions. Only authenticated responses from the private label/MAC/key roster populate it. Version 0.3.3 shows READY, OM, KIA, MIA or CHARGING from node 0.8.1's explicit summary, rather than rapid animation labels. Missing/unsupported reports show `--`; after six seconds Overview marks telemetry Stale and suppresses the current status, and after 90 seconds it marks Offline. Detailed hardware health retains its 30-second stale threshold. Nodes are polled every two seconds, paced at 125 ms across the roster. Overview checks once per second and only refreshes changed pixels; other automatic pages check every five seconds. Unanswered polls get at most two retries at 500 ms intervals. The radio worker runs independently of e-paper refreshes.

From 0.2.9, changes within a page clear and redraw the smallest enclosing rectangle of changed pixels, aligned to four-pixel groups. The previous frame and a packed region buffer occupy an additional 518,400 bytes of PSRAM, allocated once. Startup, page changes, explicit **Refresh**, and the sleep-status screen retain a full clear. If regional buffers are unavailable the console falls back to full refresh. Vendor waveforms are unchanged, so the affected region still flashes; this is not a flash-free differential mode. Widely separated simultaneous changes share one enclosing rectangle. Optical ghosting and contrast need visual acceptance on the actual panel.

From 0.2.10, each fresh touch gesture triggers once until a release report. Stale reports are ignored and coordinates are copied before acknowledging the GT911 report. Diagnostics updates on entry or explicit Refresh; its own redraw counter no longer causes another automatic redraw. The Overview, node detail and Missions pages remain live.

Tap a node for its MAC, firmware version, receiver version, OTA state, last-seen age and deployment state. **Receiver present** and **deployment verified** are separate facts. Verification requires a fresh authenticated report of the expected application digest, a changed boot count and a valid OTA boot. A radio-start result, transfer acknowledgement or displayed progress is not sufficient.

For this prototype, provision the LilyGo and nodes onto the **same 2.4 GHz access point and radio channel**. Wi-Fi association supplies the shared channel; health and firmware delivery use ESP-NOW on that channel. Merely using the same SSID across different access points is insufficient if their channels differ. Channel discovery, channel hopping and AP-free commissioning are not implemented. The handheld is not a router for future brain/body inference traffic; nodes continue their own work while it sleeps or is absent.

## Controls

- **Overview:** the live 4 × 4 roster; tap a card to open its details.
- **Node details:** deploy the currently selected SD image to that node. This starts one node's transfer, not a sixteen-node batch. Availability requires a registered, freshly observed compatible receiver and a verified stored image.
- **Diagnostics:** handheld touch detection, SD mount/capacity, heap/PSRAM and previous refresh timing. Battery voltage and runtime remain unverified.
- **Missions:** choose a scripted scenario and goal, launch a run, stop all reached nodes, and check acknowledgements against live reports.
- **Alignment (inside Diagnostics):** five targets and mapped touch coordinates. Rotation remains subject to physical confirmation on the glass digitizer; the mapping is `(rawY, 539 - rawX)` with driver transforms disabled.
- **Refresh:** redraw the current screen.
- **Sleep:** retain an explicitly frozen-status image and enter deep sleep. Sleep is blocked during an image upload or deployment. A short physical-button press cycles overview → diagnostics → missions; hold for at least one second and release to request sleep. GPIO21 is the configured wake source. Physical sleep/wake behaviour still requires acceptance testing.

The image picker is currently supplied through USB: uploading an image selects it, and the selected filename is remembered across boots. There is no on-screen multi-image catalogue yet.

## SD image storage and deployment

The existing card mounts at 4 MHz with automatic formatting disabled. Firmware images are stored under `/flockinator/images/`; uploads first use an isolated temporary file. The console verifies the complete file digest, embedded ESP image digest and expected ESP32-S3/node application header before publishing the image. Existing named images are not overwritten. An interrupted upload times out and cleans up its own temporary file; unrelated card contents are preserved.

The host transfers images over identified USB JSON in chunks of at most 512 bytes. The console then reads the selected SD file and sends authenticated, acknowledged ESP-NOW chunks to the chosen node. The node writes its inactive **internal flash** OTA slot and validates the image before booting it. This path does not stage images on the node's SD card. On success, fresh post-boot health supplies the final verification; failures and missing verification remain visible.

Node SD staging, central log collection, bulk media distribution, concurrent multi-node deployment and BLE/acoustic transports are future capabilities. The current SD integration stores deployment images; it does not claim to be a central logging service. Live ESP-NOW deployment acceptance is recorded in deployment evidence, not inferred from this README or from a successful build.

## USB management

Use the [host console client](../../tools/node-commissioner/README.md) for normal operation. It identifies the console before provisioning, loads Wi-Fi credentials and node management keys privately, and avoids placing them in command arguments or reports. `setup` imports the host inventory's registered nodes; run it again as more nodes are commissioned. Conflicting label/MAC/key bindings are rejected.

The live firmware accepts newline-delimited JSON at 115200 baud. Every request requires `v: 1`, a unique `id` of at most 96 characters and exact `target: "00:11:22:33:44:55"`. Keep each line within 2047 bytes before its newline. Replies carry matching `request_id`/`id`, `base_mac` and `ok`; host code verifies these before accepting results. USB setup is a physical maintenance interface; the per-node keys authenticate subsequent radio traffic.

| `op` | Additional fields | Result/purpose |
| --- | --- | --- |
| `status` | None | Console boot ID, Wi-Fi/channel, SD state, node roster, image and transfer state |
| `wifi` | `ssid`, `password` | Persist Wi-Fi connection settings; supply only through the private host helper |
| `register` | `label`, `mac`, `key` | Persist a node's exact identity and 32-byte key encoded as hex |
| `image_begin` | `name`, `size`, `sha256` | Begin an image upload with the whole-file SHA-256 |
| `image_chunk` | `offset`, `data` | Append the next offset's hex-encoded bytes, at most 512 bytes |
| `image_end` | None | Verify and publish the stored image; return its embedded image digest |
| `deploy` | `label`, `name`, `image_sha256` | Start deployment of the expected embedded image digest to one node |

Example read-only request:

```json
{"v":1,"id":"console-status-1","target":"00:11:22:33:44:55","op":"status"}
```

The old single-character `h/d/a/r/i/s` serial commands are **not the live protocol**. The historical `tools/serial_check.py` sends those commands and must not be used to validate this firmware. The host `console deploy` command keeps one serial connection open while polling for completion; closing and reopening USB can reset the console. A host timeout means completion is unverified, not that the radio operation has necessarily stopped.

## Build and device handling

From the repository root:

```sh
$HOME run --project-dir firmware/management-console -e lilygo-s3
$HOME test --project-dir firmware/management-console -e native
uv run --project tools/node-commissioner python -m pytest tools/node-commissioner/tests -q
```

Dependencies remain pinned: espressif32 6.12.0; Arduino ESP32 2.0.17 (framework package 3.20017.241212+sha.dcc1105b); LilyGo-EPD47 commit `50224221fb81a8fcf9068532374b775af84a38d4`; SensorLib 0.3.1; Button2 2.3.2; ArduinoJson 7.4.3. A forced `math.h` include supplies a declaration required by the unmodified vendor driver. Build/library caches live under `~/.cache/flockinator-platformio/`; the pre-script removes verified AppleDouble companions only in project-owned source/include/test folders.

Identify the physical LilyGo and exact MAC before any upload. USB VID/PID `303A:1001` also identifies other Espressif devices and is not sufficient to select it. Close competing serial clients. The board uses the vendor's 16 MB partition layout; a full initial upload writes bootloader, partitions, OTA metadata and application. Preserve a verified original flash backup privately before replacing firmware; do not publish backups or credentials. SD contents are not formatted by an upload.

## Evidence and remaining acceptance

Live commissioning evidence contains the current integration observations. Cluster deployment evidence is the record for actual image transfers and post-boot results. Build/native/host tests alone do not establish live deployment, touch alignment, wake reliability or all-sixteen-node behaviour.

Earlier management-console evidence belongs to the 0.1 demo milestone. Its fixture dashboard, preview renders and single-character serial soak must remain labelled historical; they are not evidence of live telemetry or radio deployment. Demo fixtures retained in host test code never populate the runtime table.

Manual acceptance still covers all sixteen touch selections, alignment targets, responsive touch during radio work, retained sleep status, wake freshness and card-absent boot. Battery runtime is untested because no battery is fitted. Power down before changing cards. The vendor e-paper driver has no panel-presence result and contains allocation assertions; memory guards do not make every allocation failure recoverable.

The board definition retains the pinned LilyGo repository's GPL-3.0 licence in `third_party/LilyGo-EPD47-LICENSE`; other dependencies retain their own licences. Purchased CAD files are unrelated to this firmware.


## SD maintenance relay and reliable image staging (0.2.13)

The handheld can relay authenticated SD status, inspection and explicit format/test commands between the host USB connection and node firmware 0.5.1 using ESP-NOW. This works without node DHCP leases and does not format the handheld's own SD card. The serial operations are `sd_request` and `sd_result`, with per-transaction correlation and node-MAC checks; use the node commissioner's SD client instead of hand-crafting packets. This release does not add touchscreen erase controls.

Bulk image staging now exposes `image_status`: active upload name, size, SHA-256, offset and console boot ID. The host reads this after a missing acknowledgement and only retries a write when the ordered offset readback proves it was not stored. Session mismatch fails closed. Final whole-file and embedded-image hashes are still required before publication. The pinned HWCDC USB transport still has observed delayed/lost replies; this release adds tested recovery rather than claiming to eliminate the driver issue. A real 1,039,600-byte upload completed with 59 successful recovery queries; see `../../docs/validation/fleet/20261014T081730Z-console-upload-audit/README.md`.

0.2.12's diagnostic `Serial.flush()` change did not solve the fault and was removed. Display refresh and touch logic remain those validated in 0.2.10. Existing roster keys, Wi-Fi settings and SD media are retained across these updates.
