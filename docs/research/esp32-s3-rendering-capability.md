# ESP32-S3 real-time 2D rendering capability — flight-sim view

> Question: what can an ESP32-S3 sustain for a small top-down / pseudo-3D flight-simulator view, and what hardware acceleration actually exists?
> Method: Espressif primary sources first (datasheet, TRM, ESP-IDF / ESP-IoT-Solution / ESP-BSP docs). Third-party numbers are labelled as such.
> **Measured** = vendor-published benchmark. **Estimate** = arithmetic from published clocks/bus widths, or this note's projection. Do not mix them.

## Verdict

- There is **no GPU, no 2D blitter, no pixel-processing accelerator (PPA), and no hardware JPEG codec on ESP32-S3**. All drawing — fill, line, sprite blit, alpha blend, rotation, scaling, polygon rasterisation — is CPU software. Contrast ESP32-P4, which Espressif equips with a PPA, 2D-DMA and JPEG codec; none of that is in the S3 TRM peripheral list.
- What hardware help exists is **(a)** GDMA moving finished pixels to the panel while the CPU draws the next buffer, and **(b)** 128-bit Xtensa PIE/SIMD vector instructions usable for bulk pixel math if you write or link code that uses them (ESP-DL / ESP-NN do; a naive C renderer does not automatically).
- For a **240x240 or 320x240 RGB565** scene of sprites + vectors on a fast panel interface, **30 fps is comfortably sustainable and 50-60 fps is reachable** with a custom renderer (internal-SRAM framebuffer, DMA double-buffering, one core pinned to rendering). LVGL widget scenes measure lower (see section 6). Full-screen alpha-blended / rotated / scaled art at 60 fps is **not** sustainable.

## 1. CPU (datasheet)

| Item | Value | Source |
|---|---|---|
| Core | Dual-core 32-bit Xtensa LX7, up to 240 MHz, single-precision FPU | ESP32-S3 series datasheet; ESP32-S3-WROOM-1 datasheet [1][2] |
| Internal SRAM | 512 KB (plus 16 KB RTC SRAM) | [2] |
| ULP | RISC-V ULP coprocessor (irrelevant to rendering) | [1] |

Espressif does **not** publish a DMIPS/CoreMark figure for the S3 in the datasheet, so none is quoted here. Budget rule (estimate): at 240 MHz you have 240 M cycles/s/core; a software RGB565 fill/blit loop costs roughly 1-4 cycles/pixel depending on source (SRAM vs PSRAM, blending vs copy), i.e. one core fills a 240x240 frame (57,600 px) in ~0.25-1 ms from SRAM. Rendering is therefore rarely the binding constraint at these sizes — **bus transfer and PSRAM contention are** (sections 3-4).

## 2. Vector / SIMD instructions (TRM)

- The S3 adds **Processor Instruction Extensions (PIE)**: 128-bit vector registers (bank of eight 128-bit QR registers), SIMD operations on 8/16/32-bit elements (multiply, add, subtract, accumulate, shift, compare), and an address unit reading 8-128-bit aligned data. TRM chapter 1 is devoted to it. [3][4]
- Espressif positions PIE for neural-network / DSP math (ESP-DL, ESP-NN), not as a graphics pipeline: there are no texture, raster, or blend units behind it. [4]
- Relevance to 2D: hand-written PIE can accelerate bulk ops (copies, colour conversion, alpha math, JPEG colour conversion). Third-party JPEGDEC reports ~40-50% gain on YCbCr-to-RGB/dequantisation from PIE SIMD (third-party, not Espressif). [5] Espressif's `esp_new_jpeg` is a **software** decoder (the S3 has no JPEG hardware); budget JPEG decode as CPU work, tens of ms for small frames, and do not plan on MJPEG full-screen video plus a game loop.
- Practical implication: unless your renderer deliberately uses ESP-NN/PIE intrinsics or assembly, assume **scalar** performance. LVGL's stock software renderer is scalar C with optimised memcpy/memset paths.

## 3. Memory: PSRAM types, speeds, bandwidth

| Item | Value | Class |
|---|---|---|
| In-package PSRAM options | 2 MB Quad SPI; 8 MB Octal SPI (R8); 16 MB Octal (R16V on some modules) | Datasheet [1][2] |
| Octal PSRAM clock | 80 MHz DDR (ESP-IDF default max for S3; 120 MHz DDR is an experimental ESP-IDF >=5.1 option for R8 parts) | ESP-IDF flash/PSRAM config; ESP-FAQ [6][7] |
| Quad PSRAM clock | up to 80 MHz SDR (4-bit) | [6] |
| Theoretical peak, octal DDR 80 MHz | 8 bit x 80 MHz x 2 edges = **160 MB/s** | Estimate (arithmetic) |
| Theoretical peak, quad 80 MHz | 4 bit x 80 MHz = **40 MB/s** | Estimate |
| Measured sequential PSRAM read | ~84 MB/s reported on Espressif's own forum for octal 80 MHz DDR with long cache lines (about half of peak; cache-line size matters) | Forum measurement, **not** a datasheet guarantee [8] |

Hard consequences:

- **RGB panels require octal PSRAM >=80 MHz.** Espressif's FAQ states this verbatim; quad PSRAM cannot feed a continuously-scanned RGB panel plus the CPU. [7]
- PSRAM is **shared**: CPU rendering, cache fills, and LCD GDMA all draw on the same tens-of-MB/s. A framebuffer in PSRAM is read by the DMA every refresh while the CPU writes it — expect effective bandwidth well below the sequential-read figure. Espressif's LVGL guide warns PSRAM framebuffers yield worse FPS than internal-SRAM buffers. [9]
- Internal SRAM (512 KB total, before RTOS/heap/Wi-Fi take their share) is the fast path and is where small-panel framebuffers should live.

### Framebuffer cost (exact arithmetic, RGB565 = 2 B/px)

| Resolution | 1 framebuffer | Double buffer | Fits internal SRAM? |
|---|---|---|---|
| 240x240 | 115,200 B (112.5 KiB) | 230,400 B (225 KiB) | Single comfortably; double tight but feasible |
| 320x240 | 153,600 B (150 KiB) | 307,200 B (300 KiB) | Single yes; double leaves little SRAM — prefer PSRAM or strip buffers |
| 480x480 | 460,800 B (450 KiB) | 921,600 B | No — PSRAM required |
| 800x480 | 768,000 B (750 KiB) | 1,536,000 B | No — PSRAM required (Espressif recommends 2.3 MB PSRAM config incl. LVGL buffers [10]) |

Bandwidth for full-screen updates (exact): 240x240@60 fps = 6.9 MB/s; 320x240@60 fps = 9.2 MB/s; 800x480@30 fps = 23 MB/s. Compare with bus ceilings below before blaming the CPU.

## 4. Panel interfaces and full-screen FPS ceilings

The S3 LCD peripheral supports SPI, QSPI (via SPI), I80 (8080), and parallel RGB (8-16-bit), with RGB565/YUV conversion in the LCD/CAM peripheral. [11] Ceilings are **estimates** from published clocks (frame bits / bus rate, ignoring command/blanking overhead, typically -5 to -15%):

| Interface | Published clock | Raw rate | 240x240 ceiling | 320x240 ceiling |
|---|---|---|---|---|
| SPI (IOMUX pins) | 80 MHz max (40 MHz via GPIO matrix) [12] | 10 MB/s | ~86 fps | ~65 fps |
| SPI @ 40 MHz | 40 MHz | 5 MB/s | ~43 fps | ~33 fps |
| QSPI | 80 MHz x 4 bit [11] | 40 MB/s | panel-limited (typically <=60 fps) | panel-limited |
| I80 16-bit | ~20 MHz IO in Espressif examples [9] | ~40 MB/s | panel-limited | panel-limited |
| RGB 16-bit | continuous scan-out; e.g. 21 MHz PCLK gives 41 fps interface rate at 800x480 [13] | set by PCLK/porch | panel-limited; cost is PSRAM scan-out bandwidth | same |

Structural difference: **SPI/QSPI/I80 panels have their own GRAM** — you pay only for pixels you send (partial updates possible), panel refreshes itself. **RGB panels have no GRAM** — the S3 streams the whole framebuffer continuously via GDMA, so PSRAM bandwidth is consumed even for a static screen, and tearing must be managed explicitly (section 5).

## 5. DMA and double-buffering (ESP-IDF documented)

- GDMA: 5 TX + 5 RX general-purpose channels; LCD/CAM, SPI2/3, I2S, AES, SHA, ADC, RMT have DMA. [1][11] GDMA **copies**; it does not fill with colour, blend, scale, rotate, or composite.
- SPI/QSPI/I80 path (`esp_lcd`): CPU/LVGL renders into a draw buffer, DMA transmits it; double draw buffers let the CPU render buffer N+1 while DMA sends buffer N. Standard tear-free small-panel pipeline; needs no full framebuffer.
- RGB path (`esp_lcd_panel_rgb`): ESP-IDF documents **double framebuffer in PSRAM** (`.num_fbs = 2`, simplest anti-tearing), **single PSRAM framebuffer + internal-SRAM bounce buffer** (`bounce_buffer_size_px`), and bounce-buffer-only (no FB). [11] All exist because PSRAM-only scan-out underruns when Wi-Fi/CPU contend for the bus.
- No mode changes the fact that the **CPU produces every pixel**.

## 6. LVGL performance — Espressif measured numbers

LVGL widget benchmark (`lv_demo_benchmark`), not sprite games; treat as a **lower bound** for a lean custom renderer and an **upper bound** for a widget-heavy UI.

Espressif ESP-Techpedia, LVGL v9.4.0 via `esp_lvgl_adapter` (measured): [10]

| Platform | Interface | Resolution | Benchmark |
|---|---|---|---|
| ESP32-S3 | SPI | 320x240 RGB565 | **48 fps** |
| ESP32-S3 | QSPI | 360x360 RGB565 | **55 fps** |
| ESP32-S3 | RGB | 480x480 RGB565 | **47 fps** |
| ESP32-S3 | RGB | 800x480 RGB565 | **25 fps** |

Espressif ESP-BSP `esp_lvgl_port` performance guide (measured, LVGL8/9): buffer size/double-buffering is "by far the most significant setting"; >25% of screen in the draw buffer gains little, <10% is severely slower; 240 MHz CPU, Performance optimisation, QIO/octal flash, and IRAM-resident LVGL (`CONFIG_LV_ATTRIBUTE_FAST_MEM_USE_IRAM=y`) each add measurable fps; PSRAM-resident buffers are slower than SRAM. [9] Waveshare's republication of Espressif's data for its 4.3-inch 800x480 RGB board quotes **26 fps average (LVGL benchmark, single core, ESP-IDF v5.3)** against a 41 fps interface rate — consistent with the table above. [13]

Arduino libraries (TFT_eSPI, Arduino_GFX) publish no Espressif-controlled benchmarks; the ESP-IDF numbers above already bound the same hardware, so they were not needed.

## 7. Estimate for the flight-sim view (projection)

Assumptions: custom renderer (not LVGL widgets), RGB565, framebuffer/draw buffers in **internal SRAM**, DMA double-buffering, render task pinned to one 240 MHz core, second core for input/telemetry/Wi-Fi, scene = scrolling/warped background + ~20-60 vector/sprite objects + HUD text, no full-screen alpha or rotation of large bitmaps.

| Configuration | Sustainable full-redraw fps (estimate) | Binding limit |
|---|---|---|
| 240x240, SPI @ 80 MHz (IOMUX) | **40-60** | SPI bus (86 fps raw ceiling), then render cost |
| 240x240, SPI @ 40 MHz | **25-40** | SPI bus (43 fps raw ceiling) |
| 240x240, QSPI @ 80 MHz | **50-60** (panel cap) | Render cost / panel |
| 320x240, SPI @ 80 MHz | **35-55** | SPI bus (65 fps raw ceiling) |
| 320x240, QSPI or I80 | **45-60** (panel cap) | Render cost |
| 320x240, RGB + octal PSRAM | **40-60** | PSRAM contention; use bounce buffer |
| LVGL widget UI instead of custom renderer | ~**48** at 320x240 SPI (measured [10]); 25-45 in a real app | CPU widget rendering |

**Headline estimate: plan on 30 fps locked, design for 60 fps headroom, at 240x240.** Top-down (tile/sprite scroll, vector overlays) fits easily. Pseudo-3D (mode-7-style ground warp or raycast floor) is a per-pixel CPU transform over up to 57,600 px/frame: feasible at 240x240@30 fps in scalar C if the inner loop is a precomputed scanline/texture lookup in SRAM, risky at 60 fps, and the first thing to cut (render ground at half resolution, upscale by copy) if profiling says otherwise. Rotate/scale of large sprites and full-screen alpha blending are the classic budget-breakers — PIE SIMD can help a hand-written blend; nothing accelerates it for free.

## 8. Hard limits

1. **No GPU / 2D blitter / PPA / JPEG hardware.** Every pixel is CPU-made; DMA only moves finished pixels. (P4 has these; S3 does not.) [3][11]
2. **512 KB internal SRAM total.** One 320x240 FB fits; double-buffered 480x480+ framebuffers are PSRAM-only, with the bandwidth/tearing behaviour of sections 3/5. [2][11]
3. **PSRAM ~160 MB/s theoretical peak (octal DDR 80 MHz), ~half measured sequentially, shared** between CPU, cache, and LCD DMA. RGB scan-out eats it continuously; quad PSRAM (40 MB/s peak) cannot feed RGB per Espressif. [6][7][8]
4. **SPI panels cap full-screen updates at ~65 fps (320x240) / ~86 fps (240x240) at the 80 MHz IOMUX limit**, ~half at the common 40 MHz GPIO-matrix clock — before overhead. [12]
5. **Wi-Fi/BT share the chip.** Radio activity steals CPU, cache, and PSRAM bandwidth; budget for worst-case contention (bounce buffer, core pinning) if telemetry streams during flight.
6. **LVGL is a UI toolkit, not a game renderer.** Measured 25-55 fps at these sizes is for widgets; a sprite/vector scene should use a custom renderer over `esp_lcd` + GDMA, optionally LVGL only for menus/HUD.

## Sources

[1] Espressif, ESP32-S3 Series Datasheet — https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf
[2] Espressif, ESP32-S3-WROOM-1 Datasheet — https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf
[3] Espressif, ESP32-S3 Technical Reference Manual, ch.1 PIE (128-bit SIMD) — https://www.espressif.com/sites/default/files/documentation/esp32-s3_technical_reference_manual_en.pdf
[4] Espressif Developer Portal, Edge-AI with ESP32-S3 (128-bit SIMD, PIE) — https://developer.espressif.com/workshops/edge-ai-with-esp32-s3/introduction/
[5] JPEGDEC SIMD notes (third-party) — https://deepwiki.com/bitbank2/JPEGDEC/5.3-simd-optimizations
[6] ESP-IDF, Flash and PSRAM configuration (ESP32-S3) — https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/flash_psram_config.html
[7] ESP-FAQ, RGB PSRAM requirement / 120 MHz octal DDR — https://docs.espressif.com/projects/esp-faq/en/latest/software-framework/peripherals/lcd.html
[8] ESP32 Forum, PSRAM throughput measurement (~84 MB/s, octal 80 MHz DDR) — https://www.esp32.com/viewtopic.php?p=103811
[9] Espressif ESP-BSP, esp_lvgl_port LCD and LVGL Performance — https://github.com/espressif/esp-bsp/blob/master/components/esp_lvgl_port/docs/performance.md
[10] Espressif ESP-Techpedia, LCD Application Note overview (LVGL v9.4 benchmark table) — https://docs.espressif.com/projects/esp-techpedia/en/latest/esp-friends/advanced-development/lcd-application-note/overview.html
[11] ESP-IDF, LCD peripheral guide (ESP32-S3; RGB double-FB / bounce buffer) — https://docs.espressif.com/projects/esp-idf/en/v5.0/esp32s3/api-reference/peripherals/lcd.html
[12] ESP-IDF, SPI master guide (80 MHz IOMUX vs 40 MHz GPIO matrix) — https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/spi_master.html
[13] Waveshare ESP32-S3-Touch-LCD-4.3B wiki (republishes Espressif LVGL data: 26 fps avg, 41 fps interface @ 21 MHz PCLK) — https://www.waveshare.com/wiki/ESP32-S3-Touch-LCD-4.3B

*Measured vs estimate: section 6 and the forum figure in section 3 are measured; section 4 ceilings and section 7 are arithmetic/projections from published clocks and must be re-measured on the target panel before committing to 60 fps.*
