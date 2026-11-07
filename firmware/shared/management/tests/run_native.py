"""Compile production HTTP paths with in-process transport and real Mbed TLS.

No sockets, devices, credentials, package downloads, or firmware flashing.
Python must be run with uv. See docs/management-response-auth.md.
"""
import argparse
from pathlib import Path
import subprocess


def section(source: str, start: str, end: str) -> str:
    assert source.count(start) == 1, start
    begin = source.index(start)
    return source[begin:source.index(end, begin)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mbedtls-source", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    tests = Path(__file__).resolve().parent
    firmware = tests.parents[2]
    output = args.build_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    monitor = (firmware / "korvo-monitor/main/fleet.cpp").read_text()
    node = (firmware / "node-platform/src/maintenance.cpp").read_text()
    # These are unchanged production function bodies, including both endpoints'
    # cryptographic calls, header capture, request verification and health writes.
    (output / "monitor.inc").write_text(
        section(monitor, "string hex(", "void dispatch(")
        + section(monitor, "string sha256hex(", "bool fleet_init(")
    )
    (output / "node.inc").write_text(
        section(node, "static void hex(", "static void refresh_identity(")
        + '#include "management_response.h"\n'
        + section(node, "static bool authenticate(", "static esp_err_t control(")
    )
    flags = "-fsanitize=address,undefined -fno-omit-frame-pointer" if args.sanitize else ""
    subprocess.run([
        "cmake", "-S", str(tests), "-B", str(output),
        f"-DMBEDTLS_SOURCE_DIR={args.mbedtls_source.resolve()}",
        f"-DGENERATED_PRODUCTION_DIR={output}",
        f"-DCMAKE_C_FLAGS={flags}", f"-DCMAKE_CXX_FLAGS={flags}",
    ], check=True)
    subprocess.run(["cmake", "--build", str(output), "--parallel", "2"], check=True)
    subprocess.run(["ctest", "--test-dir", str(output), "--output-on-failure"], check=True)


if __name__ == "__main__":
    main()
