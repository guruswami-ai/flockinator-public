# Hardware and finished models

Everything in the public subset needed to build the physical swarm. Only finished models are
published; design iterations and fit studies are summarised as the
parameters below, not shipped as trees of drafts.

## Components

| Part | Used for |
|---|---|
| Waveshare ESP32-S3-RGB-Matrix (N32R16) x16 | Node controllers (32 MB flash, 16 MB PSRAM) |
| P2.5 64x64 RGB LED panel, 160x160 mm x16 | One display per node; 25% brightness default, 50% ceiling |
| microSD card per node (FAT32) | Node memory, media, journals, staged images |
| ESP32-S31 Korvo-1 | Standalone controller: display/touch, web host, learning lab |
| LilyGo T5 4.7-inch ESP32-S3 (V2.4) | Handheld management remote and image store |
| Perimeter speakers + printed carriers | Per-node audio out (see `cad/perimeter-speakers/`) |
| Onboard mics, SHTC3, QMI8658 IMU, PCF85063 RTC | Per-node sensing (temp/humidity, motion, time) |
| MEAN WELL LRS-350-5 (5 V) + rear enclosure | Panel/controller power; measure demand at the brightness ceiling before sizing branches |
| Bambu PLA (white/black, Basic/Matte) | Printed diffusers, carriers, mounts - validate a full 64x64 sample before production |

Node identity (label A1-D4 bound to hardware) is provisioned per device
and kept private; builders provision their own fleet with
`tools/node-commissioner/`.

## Optional expansion

Vision, LiDAR/ToF, mmWave, thermal, IR/UV/lux and ultrasonic modules are
available as I2C-class peripheral devices in the lab; fitting one or more to a
node for a specific experiment is the proposed step. Interface and resource
requirements depend on the specific module.
Verify exposed pins, voltage, bus addresses, timing, power and driver support
against the exact board and its existing display, audio and SD allocations before
fitting a device. Record installed hardware and calibration per experiment.

## Finished models (`cad/`)

| Model | What it is |
|---|---|
| `Flockinator-grid-fit.FCStd`, `Flockinator-compact-fit.FCStd` | 4x4 grid layout studies: 250 mm and 199.8 mm pitch candidates, 160 mm panels |
| `acrylic-node-concept/` | Current panel-face/acrylic appearance direction |
| `conductor-7inch/terminal-fresh-v6/`, `conductor-7inch/sensor-deck-v7/` | Finished controller terminal and sensor-deck models |
| `perimeter-speakers/border-v3/` | Finished speaker border/carrier release |
| `panel-hole-review/` | Measured panel mounting-hole dimensions (hardware parameters) |

Build scripts beside each model regenerate it in FreeCAD. Figures,
checks, and parameters in those folders are the measured results the
models encode.

## Key dimensions (measured)

- Panel face 160x160 mm; grid candidates above; speaker guide
  92x36 mm / D5.6 posts, 1.9 mm lugs (owner fit-tested).
- Panel power is 5 V via the keyed panel header (also powers the
  controller); USB-C retained for programming, not permanent install.
