#!/bin/bash
set -euo pipefail
root=/build/corrected
cd "$root"
shasum -a 256 source-dac313f.tar > source-archive.sha256
export PATH="$root/build-tools/bin:/opt/homebrew/bin:$HOME/.local/bin:$PATH"
export IDF_PYTHON_ENV_PATH="$HOME/.espressif/python_env/idf6.1_py3.12_env"
source "$HOME/esp/esp-idf-s31/export.sh" > "$root/export.log" 2>&1
export KORVO_SDK_PATH="$HOME/esp/esp-dev-kits-s31"
{
  date -u
  git -C "$IDF_PATH" rev-parse HEAD
  git -C "$KORVO_SDK_PATH" rev-parse HEAD
  cmake --version
  ninja --version
  riscv32-esp-elf-gcc --version
  idf.py --version
} > "$root/toolchain.txt" 2>&1
cd "$root/source"
find firmware/korvo-monitor firmware/node-platform/include -type f -exec shasum -a 256 {} \; | LC_ALL=C sort > "$root/source-files.sha256"
cd firmware/korvo-monitor
set +e
idf.py --preview set-target esp32s31 > "$root/set-target.log" 2>&1
result=$?
printf '%s\n' "$result" > "$root/set-target.exit"
if [ "$result" -ne 0 ]; then exit "$result"; fi
idf.py --preview build > "$root/build.log" 2>&1
result=$?
printf '%s\n' "$result" > "$root/build.exit"
shasum -a 256 sdkconfig sdkconfig.defaults dependencies.lock > "$root/config.sha256"
if [ "$result" -eq 0 ]; then
  shasum -a 256 build/flockinator_korvo_monitor.elf build/flockinator_korvo_monitor.bin > "$root/artifacts.sha256"
fi
exit "$result"
