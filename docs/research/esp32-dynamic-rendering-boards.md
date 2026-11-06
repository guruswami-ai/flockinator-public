# ESP32 dynamic rendering: board and current-pipeline inventory

Research date: 2026-11-07. Read-only inventory of private repo `/Volumes/devops/flockinator` and public repo `/Users/kulira/projects/flockinator-public`. Node firmware verified identical for cited files (`display.cpp`, `sdkconfig.defaults` diff: same).

Question: can pregenerated, state-based animations become fully dynamic on-node rendering?

Short answer: most views already are fully dynamic. Only the avatar/face view plays back pregenerated frames. See §2.

## 1. Exact board, SoC, display facts

Every claim cites file path + line or config key.

### 1.1 Controller board and SoC (one per node, 16 nodes)

| Fact | Value | Source |
|---|---|---|
| Board | Waveshare ESP32-S3-RGB-Matrix N32R16 | `firmware/node-platform/boards/waveshare-n32r16.json:12` |
| Vendor URL | https://docs.waveshare.com/ESP32-S3-RGB-Matrix | `firmware/node-platform/boards/waveshare-n32r16.json:20-21` |
| MCU | `esp32s3`, core `esp32` | `firmware/node-platform/boards/waveshare-n32r16.json:4-5` |
| CPU clock | 240 MHz (`f_cpu: 240000000L`) | `firmware/node-platform/boards/waveshare-n32r16.json:5` |
| SoC variant | ESP32-S3-N32R16; module ESP32-S3-WROOM-2-N32R16V | private `docs/research/node-hardware.md:18,20` |
| CPU | Dual-core Xtensa LX7 up to 240 MHz | private `docs/research/node-hardware.md:18` |
| Internal SRAM | 512 KB | private `docs/research/node-hardware.md:18` |
| Flash | 32 MB | private `docs/research/node-hardware.md:18`; config below |
| PSRAM | 16 MB | private `docs/research/node-hardware.md:18` |
| Radio | 2.4 GHz Wi-Fi + BLE | private `docs/research/node-hardware.md:18`; `boards/waveshare-n32r16.json:22-25` |
| Fleet | 16 node controllers, one per panel | public `docs/hardware.md:11` |
| Peripherals | QMI8658 IMU, SHTC3, PCF85063 RTC, ES7210 mic ADC, ES8311 codec, 2 mics, speaker conn., TF/microSD, BOOT/RST, USB-C | private `docs/research/node-hardware.md:18` |

### 1.2 Flash / PSRAM configuration actually built

| Fact | Value | Source |
|---|---|---|
| IDF target | `CONFIG_IDF_TARGET="esp32s3"` | `firmware/node-platform/sdkconfig.defaults:1` |
| Flash | Octal/OPI, 80 MHz, 32 MB: `CONFIG_ESPTOOLPY_OCT_FLASH=y`, `FLASHMODE_OPI=y`, `FLASHFREQ_80M=y`, `FLASHSIZE_32MB=y` | `firmware/node-platform/sdkconfig.defaults:2-5` |
| Board flash_size | `32MB`; `maximum_size: 8388608` (8 MiB app cap) | `firmware/node-platform/boards/waveshare-n32r16.json:14-15` |
| Board max RAM field | 327680 B (PlatformIO SRAM figure; PSRAM additional) | `firmware/node-platform/boards/waveshare-n32r16.json:16` |
| PSRAM mode | `CONFIG_SPIRAM=y`, `CONFIG_SPIRAM_MODE_OCT=y` (QUAD not set) | `firmware/node-platform/sdkconfig.waveshare-s3:1967,1972-1973`; `sdkconfig.defaults:6-7` |
| PSRAM speed | 80 MHz (`CONFIG_SPIRAM_SPEED_80M=y`, `SPEED=80`) | `sdkconfig.waveshare-s3:1988,1991`; `sdkconfig.defaults:8` |
| PSRAM alloc | `CONFIG_SPIRAM_USE_MALLOC=y`, memtest, always-internal 16384 B, reserve 32768 B | `sdkconfig.waveshare-s3:2004-2011` |
| IDF version | ESP-IDF 5.5.4 | `sdkconfig.waveshare-s3:3` |
| Build env | PlatformIO `waveshare-s3`, board `waveshare-n32r16`, espidf, pioarduino 55.03.38 | `firmware/node-platform/platformio.ini` `[env:waveshare-s3]` |

Partitions (`firmware/node-platform/partitions.csv:1-7`): `nvs` 0x9000/0x6000, `otadata` 0xF000/0x2000, `phy_init` 0x11000/0x1000, `ota_0` 0x20000/0x800000 (8 MiB), `ota_1` 0x820000/0x800000 (8 MiB), `identity` 0x1020000/0x10000. Dual-slot OTA + rollback (`CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y`, `sdkconfig.defaults`). No filesystem partition; bulk media on microSD.

### 1.3 Display panel

| Fact | Value | Source |
|---|---|---|
| Panel | P2.5 64x64 RGB LED, 160x160 mm, one per node x16 | public `docs/hardware.md:12` |
| Resolution | 64 x 64 RGB pixels | private `docs/research/node-hardware.md:54`; `firmware/node-platform/src/display.cpp:118` |
| Interface | HUB75 parallel shift-register bus. No LCD controller IC (no ILI9341/ST7735, no SPI/RGB/QSPI LCD): ESP32-S3 bit-streams rows directly via `esphome__esp-hub75` | private `docs/research/node-hardware.md:54`; `display.cpp:22` (`#include "hub75.h"`) |
| Scan | 1/32 scan, HUB75 | private `docs/research/node-hardware.md:54` |
| Power | Ext. 5 V/4 A, ≤20 W/panel published full-rating (not operating load) | private `docs/research/node-hardware.md:54` |
| Brightness | 25% default, 50% ceiling | public `docs/hardware.md:12`; `display.cpp:120`, clamp `firmware/node-platform/include/node_model.h:7` |
| Pins (firmware) | `{4,5,6,7,15,16,18,8,3,42,9,40,2,41}` R1,G1,B1,R2,G2,B2,A,B,C,D,E,LAT,OE,CLK | `display.cpp:119`; vendor table private `docs/research/node-hardware.md:28-31` |
| Not node displays | Korvo-1 = standalone controller; LilyGo T5 4.7" = legacy/recovery only | public `docs/hardware.md:14-15` |

Driver config used (`display.cpp:117-123`): `panel_width=64, panel_height=64, double_buffer=true, output_clock_speed=HZ_10M, brightness=node::brightness(25)`. Defaults contrast: `managed_components/esphome__esp-hub75/include/hub75_types.h:160,163` 64x64, `:204` 20 MHz default clock, `:217` double_buffer=false default.

## 2. Current rendering pipeline

### 2.1 Frame production

- CPU framebuffer `node::Frame { uint16_t pixels[64*64]; }` RGB565 — `firmware/node-platform/include/pixel_ui.h:52-53`.
- `display_tick()` (`firmware/node-platform/src/display.cpp:129`), called from main loop (`firmware/node-platform/src/main.cpp:105`), renders one view into static `frame`, then full-frame blit + flip: `draw_pixels(0,0,64,64,frame.pixels, RGB565, RGB, false); flip_buffer();` at `display.cpp:161-162` (world/survey), `:170-171` (mission), `:180-181` (avatar), `:221-222` (diagnostics).
- No sprites, no hardware compositing, no partial updates. Double-buffered (`display.cpp:121`).
- Two static framebuffers: `frame`, `recon_scratch` (`display.cpp:28`) = 2 x 8192 B.
- Primitives: `Frame::pixel/text` 3x5 glyphs (`pixel_ui.h:56-67`); `recon::Painter` pixel/rect/Bresenham line/text/corners/square (`firmware/node-platform/include/recon_render.h:14-76`).

### 2.2 Cadence (code gates, not measurements)

| Path | Gate | Rate | Source |
|---|---|---|---|
| Normal | `now-last_frame<125` return | ≤8 fps; dropped counted if gap >250 ms | `display.cpp:151-152` |
| Patternflow trial (`FLOCK_PATTERNFLOW_TRIAL`) | `now-last_frame<33` | ≤~30 fps | `display.cpp:143` |

Firmware instruments live render time: last 256 durations, `render_p50_us/p95/max`, `last_render_us`, `rendered/dropped_frames` (`display.cpp:36,163,172,260-261,278-280`). No recorded values exist in either repo (§4).

### 2.3 Computed vs pregenerated

| View | Production | Pregen? | Source |
|---|---|---|---|
| Recon theatre `recon::render` | Procedural per-pixel: deterministic `scene(config,elapsed,index)`, per-pixel perspective ground (y 8..49 x 64), CAM/WH/BH/NV palettes, crosshair/target/HUD | No | `firmware/shared/recon/model.h:243-397`; `recon_render.h:85-273`, loop `:233-273` |
| World `world::render` | Ray-per-pixel terrain (y 8..49 x 64), authored/fixture or host pose, 3D peer markers | No | `firmware/node-platform/include/world_render.h:105-130`, loop `:109-117` |
| Survey `survey::render` | Delegates to `world::render` + text overlays; validated host packet input, not frames | No | `firmware/node-platform/include/survey_render.h:30-41` |
| Mission `mission_world::render` | World into `recon_scratch`, then `recon::render` with it as background (`background->pixels[y*64+x]`) — two full renders/frame | No | `firmware/node-platform/include/mission_world.h:27-39`; `recon_render.h:232` |
| Avatar/face | State→index, pregenerated 64x64 RGB565 frame copied verbatim + text overlays | **Yes — only pregenerated playback** | `display.cpp:174-181`; `firmware/node-platform/include/avatar_render.h:6-7` |
| Diagnostics | Procedural text/colour patterns | No | `display.cpp:183-222` |
| Patternflow trial env only | Generative Patternflow patterns per frame + ripple overlay | No | `display.cpp:142-150`; `firmware/node-platform/include/patternflow/adapter.h` (`PFCanvas::setPixel`→RGB565 `node::Frame`); `platformio.ini [env:patternflow-trial]` |

"State-based" ≠ frame-based for recon/world: animation is `scene(config, elapsed, nodeIndex)` (`model.h:243`) evaluated fresh each tick.

### 2.4 The one pregenerated asset: face pack

- Index mapping: `node::avatar_frame(state,now,seed,injury)` — `firmware/node-platform/include/display_state.h:26-38` (activity/attention/mood/vitality→index + timed glance cycle). State from host `display_state/profile/demo/random` (`display.cpp:77-113`), 7-step demo sequencer (`display.cpp:67-76`), or PRNG cycler 3–7 s/expression (`firmware/node-platform/include/random_expression.h`).
- Format: magic `FLKFACE1`, count @8, frame size 8192 asserted @12, frames @ `16+index*8192` — `firmware/node-platform/include/face_pack.h:7-10`; `firmware/node-platform/src/face_media.cpp:29-36`.
- Shipped pack: `firmware/node-platform/src/faces.pack` = 352272 B = 16 + 43 x 8192 (header parsed: count=43, frame_bytes=8192, verified 2026-11-07). Raw RGB565, uncompressed.
- Storage: embedded flash `_binary_faces_pack_start/end` (`face_media.cpp:13-14`); copied to microSD under SHA-256 dir, re-cached to PSRAM `heap_caps_malloc(n,MALLOC_CAP_SPIRAM)` (`face_media.cpp:42`), verified vs `FacesSha` (`firmware/node-platform/include/faces_meta.h:2`); status `sd_psram|bundled_flash` (`face_media.cpp:60-62`). Invalid pack → `nullptr`, overlays on black (`avatar_render.h:7`).

## 3. Frame sizes and memory budgets

| Item | Size | Derivation/source |
|---|---|---|
| 1 frame 64x64 RGB565 | 8192 B | 64*64*2; `face_pack.h:9`, `pixel_ui.h:53` |
| CPU framebuffers x2 | 16384 B static | `display.cpp:28` |
| Face pack 43 fr | 352272 B flash; +352272 B PSRAM if SD-cached | §2.4 |
| Hypothetical 60-fr set | 491520 B/set | 60x8192 arithmetic only |

Budgets: Internal SRAM 512 KB (private `node-hardware.md:18`); framebuffers 16 KiB + main stack 12288 B (`CONFIG_ESP_MAIN_TASK_STACK_SIZE`, `sdkconfig.defaults`) are small; HUB75 DMA double buffers extra (`MALLOC_CAP_DMA` allocs `managed_components/esphome__esp-hub75/src/platforms/gdma/gdma_dma.cpp:393,420`, exact bytes unknown §4). PSRAM 16 MB octal 80 MHz (§1.2) holds SD face cache + Patternflow buffers (`PFMem::alloc` `MALLOC_CAP_SPIRAM`, `patternflow/adapter.h`); sustained PSRAM bandwidth under display+audio+radio unverified (private `node-hardware.md:62`). CPU dual LX7 240 MHz; recon/world each ~2688–4096 float-trig pixel evals/frame (`recon_render.h:233`, `world_render.h:109`), mission does both + copy — proven envelope is the coded 8 fps gate; ~30 fps Patternflow is trial-env only (`display.cpp:143`). Flash 8 MiB/OTA slot; 344 KiB face pack currently in app image.

Implication: fully-dynamic question applies only to avatar. Recon/world/survey/mission/diagnostics already render from state each frame — no frames/sprites/GIF in shipped build. Dynamic avatar = procedural renderer into same `node::Frame` (existing `Painter`/per-pixel toolkit); face pack + SD/PSRAM caching (`face_media.cpp`) then removable. Headroom at ≤8 fps alongside Wi-Fi/audio/SD is unmeasured (§4).

## 4. Unknowns (not established by either repo)

1. Achieved render time/fps on hardware — instrumentation exists (`display.cpp:278-280`), no recorded p50/p95/max or dropped counts in either repo. All rates above are code gates.
2. Exact purchased panel driver IC + board revision — private `docs/research/node-hardware.md:60` requires validation; `:46` vendor example selects FM6126A, unconfirmed on purchased panels. Firmware leaves hub75 `shift_driver` GENERIC (`hub75_types.h:172`, not overridden `display.cpp:117-123`).
3. HUB75 DMA double-buffer bytes; usable heap/DMA/PSRAM under concurrent display+audio+radio+SD+inference (private `node-hardware.md:62`).
4. Sustained PSRAM bandwidth, 240 MHz thermal/power on purchased revision — flagged unverified, no benchmark in either repo.
5. Per-panel variant/serial registry — fleet P2.5 stated public `docs/hardware.md:12`, per-panel physical acceptance separate, none found.
6. No document named bill-of-materials/BOM in either repo; nearest: public `docs/hardware.md`, private `docs/inventory/`, `docs/research/node-hardware.md`.
7. Face-pack authoring provenance undocumented (format/hash/playback only); dynamic replacement must re-derive expressions from `display_state.h:26-38`.
8. Display controller IC: none — HUB75 panels are dumb shift-register panels; if a future panel differs, this inventory does not cover it. Korvo/future 7"/10.1" are separate operator displays (public `docs/hardware.md:14`).

## 5. Source index

Private `/Volumes/devops/flockinator`: `firmware/node-platform/src/display.cpp`; `include/pixel_ui.h`, `recon_render.h`, `world_render.h`, `survey_render.h`, `mission_world.h`, `avatar_render.h`, `display_state.h`, `face_pack.h`, `faces_meta.h`; `src/face_media.cpp`, `src/faces.pack`; `firmware/shared/recon/model.h`; `boards/waveshare-n32r16.json`, `sdkconfig.defaults`, `sdkconfig.waveshare-s3`, `partitions.csv`, `platformio.ini`; `docs/research/node-hardware.md`.

Public `/Users/kulira/projects/flockinator-public`: `docs/hardware.md:11-15`; same `firmware/node-platform` tree (identical for cited files).
