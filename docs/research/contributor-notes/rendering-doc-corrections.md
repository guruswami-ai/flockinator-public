<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Reviewed by supervisor before use; not yet adopted. Adapt host/framing details to Korvo + flockwire before implementation. -->

# Flockinator: 64x64 HUB75 corrections

**Panels:** 1x 64x64 RGB565 = `64*64*2 = 8,192 B`. Double = 16,384 B.
**Bandwidth full-frame:** 8fps = 65.5 KB/s, 30fps = 246 KB/s, 60fps = 492 KB/s. Trivial.
**Render cost:** 4,096 px vs 57,600 px at 240x240 = **14.06x fewer pixels.** 1-4 cyc/px scalar fill = 4k-16k cycles = **0.017-0.068 ms @240MHz.** Whole sprite/vector scene <1ms.

No correction needed: **no GPU / blitter / PPA / JPEG on S3.** All pixels CPU-made. PIE/SIMD only if hand-coded. That stands.

## What to strike / re-scope

1.  **Verdict: "30fps comfortable, 50-60 reachable at 240x240/320x240"**
    *Re-scope:* At 64x64 render is never the bind. 30fps is not a stretch goal, it's idle. Defensible headline below.

2.  **§1 Budget rule: "0.25-1ms to fill 240x240, bus is binding"**
    *Correct to:* 0.02-0.07ms to fill 64x64 from SRAM. Bus is **not** binding. Logic, Wi-Fi, HUB75 scan-refresh contention bind first.

3.  **§3 PSRAM table + "RGB requires octal PSRAM >=80MHz"**
    *Strike for this build:* 8/16KB lives in internal SRAM = ~3.2% of 512KB. No PSRAM FB, no 225-300KiB double-buffer problem, no quad-vs-octal issue. 240x240/320x240/480x480/800x480 rows irrelevant. Keep one line: keep FB + sprites in SRAM, never PSRAM.

4.  **§4 Panel ceilings: SPI 80/40MHz, QSPI, I80, RGB PCLK table**
    *Strike entirely - wrong interface.* HUB75 has no SPI/QSPI/I80 GRAM panel. It has **no GRAM**, like RGB but worse:
    - Continuous multiplex scan: A-E row addr + CLK + LAT + OE, 1/32 scan for 64x64, shift-clock ~10-20MHz.
    - DMA streams bitplanes continuously for brightness PWM/BCM even on static image.
    - Limit is **refresh-rate vs brightness vs flicker**, not "86fps SPI ceiling." Do not quote 86/65/43/33fps numbers.
    - Render-fps != LED-refresh-Hz != OE-PWM rate. Don't conflate.

5.  **§5 `esp_lcd` SPI / `esp_lcd_panel_rgb` `.num_fbs=2`, bounce-buffer**
    *Strike:* HUB75 does not use that path. Typical lib uses I2S/LCD parallel DMA + linked-list + SRAM double-buffer driving shift chain. Double-buffer still yes, but 8KB SRAM buffers, not PSRAM FB + bounce-buffer.

6.  **§6 LVGL Techpedia: 48fps @320x240 SPI, 55fps @360x360 QSPI, 47fps @480x480, 25fps @800x480**
    *Not transferable.* That's widget-benchmark on GRAM/RGB LCDs. Says nothing about 64x64 HUB75 scan + custom sprite renderer. Expect far higher for lean renderer, and LVGL is wrong tool here: HUD text / widgets unreadable at 64px, use 3x5 bitmap font + icons.

7.  **§7 Estimate table + "mode-7 risky at 60fps, cut ground to half-res"**
    *Over-pessimistic by ~14x:* Per-pixel warp over 4,096px @30fps = 122k px/s, @60fps = 245k px/s. Scalar C with LUT in SRAM handles 60fps easily. Full-screen alpha/rotate of large bitmaps still the only real breaker, but "large" = 64px. Top-down sprites/vectors: no constraint.

8.  **§8 Hard limits 2-4: SRAM 512KB, PSRAM 160MB/s, SPI 65/86fps caps**
    *Re-scope to non-issues:* 16KB double buffer fits anywhere. PSRAM contention ~0.5MB/s negligible. SPI caps don't exist. Real limits: a) HUB75 DMA + OE timing + chaining load if 1x S3 drives >1 panel, b) Wi-Fi stealing CPU/cache causing scan flicker, pin render/scan to core, c) JPEG decode tens-of-ms still blows a 33ms budget - keep assets raw/indexed.

9.  **8fps gate vs 30fps trial**
    *Clarify:* 8fps is sim-tick / experiment gate, **not** S3 render limit. 30fps trial path is hardware-credible. Don't present 8fps as display capability.

## Defensible headline

> **64x64 RGB565 sprite/vector: 30fps locked sustainable on one S3 core with SRAM double-buffer + DMA HUB75 scan, 60fps+ render headroom for lean scenes.**

CPU render ~0.1-1ms/frame leaves ~32ms budget at 30fps for sim/telemetry/Wi-Fi. Cap sim at 8Hz if pre-registered, render/interpolate display at 30Hz decoupled.
