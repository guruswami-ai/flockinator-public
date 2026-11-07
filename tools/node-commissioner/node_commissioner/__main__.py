"""Flockinator USB and authenticated Wi-Fi commissioning client."""
import argparse
import csv
import json
import time
from pathlib import Path
from serial.tools import list_ports
from .serial_link import SerialLink
from .protocol import valid_mac, validate_status
from .credentials import (save_wifi, load_wifi, management_key,
                          add_credential_arguments, run_credential_command)
from .network import NetworkClient
from .image import verify_image
from .evidence import save_run
from .provisioning import Artifact, Package, Provisioning
from .provisioning_backend import EsptoolBackend

ROOT = Path(__file__).resolve().parents[3]


def inventory_path(args):
    selected = getattr(args, "inventory", None)
    return selected.expanduser() if selected is not None else ROOT / "docs/inventory/nodes.csv"


def evidence_root(args):
    selected = getattr(args, "evidence_root", None)
    return selected.expanduser() if selected is not None else ROOT / "docs/validation/nodes"


def resolve_target(args):
    if args.label:
        with inventory_path(args).open(newline="") as file:
            rows = [r for r in csv.DictReader(file) if r["label"] == args.label]
        if len(rows) != 1:
            raise ValueError("Unknown node label")
        known = rows[0]["factory_base_mac"]
        if args.mac and known and args.mac != known:
            raise ValueError("MAC conflicts with the node inventory")
        args.mac = args.mac or known
    if not args.mac:
        raise ValueError("Supply an identified --mac or a registered --label")
    if not args.address and not args.port:
        ports = [p.device for p in list_ports.comports() if p.serial_number and p.serial_number.upper() == args.mac]
        if len(ports) != 1:
            raise ValueError("No unique matching USB device; supply --port or --address")
        args.port = ports[0]


def load_initial_package(manifest: Path) -> Package:
    """Load either established release manifest format with fixed safe offsets."""
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 1024 * 1024:
        raise ValueError("Expected a regular release manifest no larger than 1 MB")
    value = json.loads(manifest.read_text())
    if not isinstance(value, dict) or not isinstance(value.get("version"), str):
        raise ValueError("Invalid release manifest")
    status = str(value.get("status", "")).upper()
    kind = str(value.get("package_type", "")).upper()
    if any(word in status + " " + kind for word in ("REJECTED", "DO_NOT_FLASH_USB", "ROLLBACK-TEST", "ROLLBACK TEST")):
        raise ValueError("Rejected/recovery-test releases cannot be initially commissioned")
    if value.get("target_family", "WS32") != "WS32":
        raise ValueError("Release targets another hardware family")
    images = value.get("images", {})
    hashes = value.get("artifacts_sha256", {})
    if not isinstance(images, dict) or not isinstance(hashes, dict):
        raise ValueError("Invalid release artifact records")
    offsets = {"bootloader.bin": 0, "partitions.bin": 0x8000,
               "ota_data_initial.bin": 0xF000, "firmware.bin": 0x20000}
    artifacts = []
    for name, offset in offsets.items():
        record = images.get(name, {})
        if not isinstance(record, dict):
            raise ValueError("Invalid release image record")
        digest = hashes.get(name) or record.get("file_sha256")
        if not isinstance(digest, str):
            raise ValueError(f"Initial installation requires a trusted digest for {name}")
        if name in hashes and "file_sha256" in record and hashes[name] != record["file_sha256"]:
            raise ValueError("Conflicting release artifact digests")
        path = manifest.parent / name
        artifacts.append(Artifact(path, offset, digest))
        if "bytes" in record and path.stat().st_size != record["bytes"]:
            raise ValueError("Release artifact size mismatch")
    application = images.get("firmware.bin", {})
    expected = value.get("esp_image_sha256") or application.get("esp_image_sha256")
    if not isinstance(expected, str):
        raise ValueError("Missing application runtime digest")
    package = Package(value["version"], expected, tuple(artifacts))
    package.validate()
    app = artifacts[-1]
    if value.get("file_sha256", app.sha256) != app.sha256:
        raise ValueError("Conflicting application file digest")
    if value.get("file_bytes", app.path.stat().st_size) != app.path.stat().st_size:
        raise ValueError("Application size mismatch")
    if verify_image(app.path, app.sha256) != package.app_image_sha256:
        raise ValueError("Release runtime digest does not match application")
    return package


def provision_target(args) -> dict:
    if not valid_mac(args.mac):
        raise ValueError("Supply the exact factory MAC as six hexadecimal pairs")
    inventory = inventory_path(args)
    with inventory.open(newline="") as source:
        rows = list(csv.DictReader(source))
    matches = [row for row in rows if row.get("label") == args.label]
    if (len(matches) != 1 or len({row.get("label") for row in rows}) != len(rows)
            or matches[0].get("factory_base_mac") not in ("", args.mac)
            or any(row.get("label") != args.label and row.get("factory_base_mac") == args.mac for row in rows)):
        raise ValueError("Unknown/duplicate inventory label or conflicting factory MAC")
    package = load_initial_package(args.manifest)
    private = Path.home() / ".local/share/flockinator"
    mac_directory = args.mac.replace(":", "-")
    transaction = args.transaction or private / "commissioning" / mac_directory / f"{args.label}-initial"
    wifi, key = load_wifi(), management_key(args.mac, create=True)
    backend = EsptoolBackend(port=args.port, mac=args.mac, package=package,
                             private_directory=transaction / "tool-logs")
    try:
        print(json.dumps(dict(transaction=str(transaction), label=args.label, base_mac=args.mac)), flush=True)
        return Provisioning(backend=backend, inventory=inventory, transaction=transaction,
            backup_root=private / "backups/nodes" / mac_directory,
            evidence_root=evidence_root(args), label=args.label, mac=args.mac,
            package=package, wifi=wifi, key=key, skip_backup=args.skip_backup).run()
    finally:
        backend.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    add_credential_arguments(sub.add_parser("credentials", help="Initialize or import private controller credentials"))
    sub.add_parser("list"); sub.add_parser("save-wifi")
    provision = sub.add_parser("provision", help="Resumable initial flash, provisioning and inventory")
    provision.add_argument("--label", required=True, choices=[f"{row}{column}" for row in "ABCD" for column in range(1, 5)])
    provision.add_argument("--mac", required=True, type=str.upper)
    provision.add_argument("--port", required=True)
    provision.add_argument("--manifest", required=True, type=Path)
    provision.add_argument("--inventory", type=Path, help="Your private CSV inventory; defaults to repository inventory")
    provision.add_argument("--evidence-root", type=Path, help="Your private evidence directory; defaults to repository validation directory")
    provision.add_argument("--transaction", type=Path, help="Private journal directory; reuse the same directory to resume")
    provision.add_argument("--skip-backup", action="store_true",
                           help="Record owner-authorized waiver of original-flash backup; retained on resume")
    for name in ("status", "assign", "reboot", "wifi", "pair-key", "tone", "next-page", "test", "update", "accept"):
        p = sub.add_parser(name)
        p.add_argument("--port"); p.add_argument("--mac"); p.add_argument("--address")
        p.add_argument("--label", required=name in ("assign", "test", "accept"))
        p.add_argument("--inventory", type=Path, help="Your private CSV inventory for label resolution")
        p.add_argument("--output", type=Path)
        if name == "test":
            p.add_argument("--evidence-root", type=Path, help="Your private evidence directory")
            p.add_argument("--suite", choices=["hardware"], default="hardware")
            p.add_argument("--seconds", type=int, default=10)
        if name == "update":
            p.add_argument("--image", type=Path, required=True)
            p.add_argument("--sha256", required=True)
        if name == "accept":
            p.add_argument("--evidence-root", type=Path, help="Your private evidence directory")
            p.add_argument("--check", choices=["panel", "speaker", "microphone_channels", "button", "motion"], required=True)
            p.add_argument("--result", choices=["pass", "fail"], required=True)
    args = parser.parse_args(argv)
    if args.command == "credentials":
        run_credential_command(args, parser)
        return
    if args.command == "provision":
        print(json.dumps(provision_target(args), indent=2))
        return
    if args.command == "save-wifi":
        save_wifi(); return
    if args.command == "list":
        print(json.dumps([dict(port=p.device, vid=p.vid, pid=p.pid, usb_serial=p.serial_number, description=p.description) for p in list_ports.comports()], indent=2)); return
    resolve_target(args)
    if args.address and args.command in ("assign", "wifi", "pair-key", "reboot"):
        raise ValueError("This operation requires the identified USB connection")
    link = None
    client = NetworkClient(args.address, args.mac, management_key(args.mac)) if args.address else None
    if not client:
        link = SerialLink(args.port, args.mac)
    def status():
        value = client.request("GET", "/v1/status") if client else link.request(timeout=15)
        return validate_status(value, args.mac, args.label if args.command != "assign" else None)
    try:
        current = status()
        if args.command == "assign":
            current = link.request("provision", label=args.label)
            validate_status(current, args.mac, args.label)
        elif args.command == "wifi":
            current = link.request("wifi", **load_wifi())
        elif args.command == "pair-key":
            current = link.request("set_key", key=management_key(args.mac, create=True).hex())
        elif args.command in ("tone", "next-page"):
            op = args.command.replace("-", "_")
            if client:
                current = client.request("POST", "/v1/control", op.encode())
            else:
                current = link.request(op)
        elif args.command == "reboot":
            current = link.request("reboot")
        elif args.command == "update":
            if not client:
                raise ValueError("Update requires --address; initial flash is a separate transaction")
            digest = verify_image(args.image, args.sha256)
            before_update = current
            accepted = client.request("POST", "/v1/update", args.image.read_bytes(), timeout=50)
            if not accepted.get("ok"):
                raise ValueError("Update rejected")
            for attempt in range(20):
                time.sleep(2)
                try:
                    current = status()
                    if (current.get("app_sha256") == digest
                            and type(current.get("boot_count")) is int
                            and current["boot_count"] > before_update["boot_count"]
                            and current.get("running_partition") in ("ota_0", "ota_1")
                            and current["running_partition"] != before_update.get("running_partition")
                            and current.get("ota_state") == 2
                            and current.get("commissioning_link", {}).get("receiver_version") == 1):
                        break
                except (OSError, ValueError):
                    continue
            else:
                raise RuntimeError("Update accepted but fresh boot, active slot, digest and receiver were not verified")
        elif args.command == "test":
            if not 1 <= args.seconds <= 3600:
                raise ValueError("Test duration must be 1–3600 seconds")
            deadline = time.monotonic() + args.seconds
            first = current
            while time.monotonic() < deadline:
                time.sleep(2)
                current = status()
                if current["boot_count"] != first["boot_count"] or current["app_sha256"] != first["app_sha256"]:
                    raise RuntimeError("Unexpected restart/build change during test")
                save_run(evidence_root(args), args.label, args.mac, current, "wifi" if client else "usb")
        if args.command == "accept":
            path = save_run(evidence_root(args), args.label, args.mac, current, "operator")
            acceptance = dict(label=args.label, base_mac=args.mac, app_sha256=current["app_sha256"], check=args.check, result=args.result, source="explicit_operator_command")
            with path.with_name("manual-acceptance.json").open("x") as file:
                json.dump(acceptance, file, indent=2)
            print(f"Manual acceptance saved: {path.parent}")
        rendered = json.dumps(current, indent=2) + "\n"
        if args.output:
            with args.output.open("x") as out:
                out.write(rendered)
        print(rendered, end="")
    finally:
        if link:
            link.close()


if __name__ == "__main__":
    main()
