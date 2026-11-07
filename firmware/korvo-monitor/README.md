# Korvo monitor bring-up

ESP32-S31 Korvo touchscreen fleet monitor and standalone web host, version 0.9.0. Shows a square
4×4 physical panel overview with row/column coordinates, status counts and a
selected-panel inspector. Tap a panel for firmware, reported uptime, free RAM and
reading age. The selected panel has a white outline; colours always have text labels. The provisioned controller hosts the web interface, learning lab, tabletop planner,
scripted fleet controls and SD exercise archives. the browser host only needs a browser.
The USB bridge described in bridge instructions
is retained for recovery to older firmware. The version is defined in [CMakeLists.txt](CMakeLists.txt); it does not establish
the running version or physical acceptance of any controller.

## Standalone operation — 0.9.0

Open the address shown on the controller's Learning lab screen. Its address is deployment-specific. Fleet missions are at `/`, the
tabletop editor at `/planner`, and the communication experiment at `/lab`.
Fleet and planner writes ask for the six-digit operator PIN shown on the Korvo.
The PIN changes after reboot. Scripted starts have a one-minute countdown to
allow all sixteen authenticated commands and their readbacks to complete.

The Korvo owns the simulation clocks and world state. Closing every browser does
not stop a run. Mission settings and the planner persist in NVS. The learning
experiment checkpoints every eight rounds and reconstructs its seeded memory on
restart. Network time restores absolute mission timing after reboot. When network
time is unavailable, an authenticated web action can set the clock from the
browser. ESP-IDF's [SNTP service](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_netif_programming.html)
starts after the station acquires its address.

Planner archives live under `/sdcard/flockinator/runs`. Each contains sixteen or
fewer unit JSONL journals plus separate director truth, with ZIP download from the
editor. Delivery to physical panels is asynchronous. A receipt appears only after
the Korvo reads the panel's SD copy back and compares every byte. Health polling
gets a complete sweep between deliveries. Retain receipts with their corresponding source journals.

Identity-bound management keys are provisioned over verified USB and reside in
controller NVS, never firmware images or browser assets. They retain maintenance
privileges. Do not run a desktop poller or USB bridge concurrently with standalone
control, because panel authentication challenges are shared.

These remain simulated agents and board-game energy units. The learning lab runs
on the Korvo; panel journal receipts prove storage, not learning on each panel.
Training larger external models and compiling replacement firmware still require
a development computer. The panel build variants are documented in the
[node README](../node-platform/README.md); a controller source version cannot
establish the deployed panel versions.

USB roster/Wi-Fi provisioning uses the [host helpers](../../tools/korvo-monitor/README.md).
The public helper/controller identities are placeholders and must be bound to
verified hardware before provisioning. Supply credentials privately through stdin;
helper output may include an operator PIN and must not be published.

The portable model checks run from the repository root.

```sh
c++ -std=c++17 -Wall -Wextra -Werror firmware/korvo-monitor/tests/lab_model_test.cpp firmware/korvo-monitor/main/lab_model.cpp -o /tmp/korvo-lab-test
/tmp/korvo-lab-test
cc -c firmware/korvo-monitor/main/vendor/blake2s-ref.c -o /tmp/korvo-blake.o
c++ -std=c++17 -fsanitize=address,undefined -g -I firmware/korvo-monitor/main firmware/korvo-monitor/tests/board_model_parity.cpp firmware/korvo-monitor/main/board_model.cpp firmware/korvo-monitor/main/lab_model.cpp /tmp/korvo-blake.o -o /tmp/korvo-board-parity
uv run firmware/korvo-monitor/tests/compare_boards.py /tmp/korvo-board-parity
```

Board target: 16 MiB flash, 16 MiB PSRAM, 800 × 480 RGB display and
GT1151-family touch controller. Confirm the actual board before installation;
this public source carries no factory-backup or erase authorization.

## Build

This target requires ESP-IDF 6.1, not the existing S3 PlatformIO environments.
Upstream sources used:

- ESP-IDF release/v6.1: `9a97f6c54ec638111ce55cd36581b3c192f15207`
- esp-dev-kits: `bd4d4ac18657e73583af3d7c0b0a23c3cddf3735`

The unmodified Korvo BSP comes from the pinned esp-dev-kits checkout. Its component
manifest resolves display, touch and other board dependencies. The application
starts speaker output; camera and microphone capture are not started.

Run the following from this directory in a fresh public checkout. The committed
`sdkconfig.defaults` selects the S31, custom partition table, 16 MiB QIO flash,
PSRAM, fonts and scheduler settings. Explicit target selection also avoids reusing
an ESP32 configuration from an earlier failed build.

```sh
export IDF_PYTHON_ENV_PATH="$HOME/.espressif/python_env/idf6.1_py3.12_env"
source "$HOME/esp/esp-idf-s31/export.sh"
export KORVO_SDK_PATH="$HOME/esp/esp-dev-kits-s31"
idf.py --preview set-target esp32s31
idf.py --preview build
```

The default build needs no PCM assets. It plays event tones when no corresponding
speech sample exists on SD. To embed your own speech, generate all ten samples and
enable **Korvo monitor → Embed operator-supplied speech samples** in
`idf.py --preview menuconfig`; see [speech setup](main/speech/README.md).

Installation is a separate hardware acceptance step:

```sh
idf.py --preview -p "$FLOCKINATOR_KORVO_PORT" flash
idf.py --preview -p "$FLOCKINATOR_KORVO_PORT" monitor
```

Run from this directory. Set `FLOCKINATOR_KORVO_PORT` to the positively
identified controller before flash/monitor commands. For a new machine, check out the pinned sources and use
`uv run --python 3.12 tools/idf_tools.py install --targets esp32s31` and
`uv run --python 3.12 tools/idf_tools.py install-python-env` inside ESP-IDF.
The latter manages ESP-IDF's own runtime. CMake and Ninja must also be available.

## Acceptance

Build, flash and observe a stable heartbeat without resets. On the physical screen,
confirm readable text, increasing uptime, and a touch counter that increments once
per tap. Serial startup alone cannot verify visible rendering or touch accuracy.

Fleet telemetry uses authenticated host status reads and a bounded USB protocol.
Readings expire after 20 seconds; LIVE denotes a fresh response, not all-hardware health.

### Network-mounted workspace

For this SMB workspace, use a local build copy to avoid slow metadata operations:

```sh
mkdir -p "$HOME/.cache/flockinator-korvo/source/firmware"
rsync -a --exclude build --exclude managed_components --exclude '._*' ../korvo-monitor "$HOME/.cache/flockinator-korvo/source/firmware/"
mkdir -p "$HOME/.cache/flockinator-korvo/source/firmware/node-platform"
rsync -a ../node-platform/include "$HOME/.cache/flockinator-korvo/source/firmware/node-platform/"
rsync -a ../shared "$HOME/.cache/flockinator-korvo/source/firmware/"
cd "$HOME/.cache/flockinator-korvo/source/firmware/korvo-monitor"
idf.py --preview set-target esp32s31
idf.py --preview build
```

Keep source edits in the repository and repeat the sync before each build. Sync the
resolved `dependencies.lock` back if dependency resolution changes it. Build artifacts
remain in the local cache; the repository is the source of truth.


Version history (0.1-0.8 bring-up, mission cues, speech samples) is in this repository's git history. Speech samples are generated, not shipped - see `main/speech/README.md`. Current release: 0.9.0 standalone (fleet controls, planner, learning lab; panels on their node firmware).
