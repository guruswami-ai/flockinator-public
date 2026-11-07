"""Explicit fresh-owner initialization and optional one-time vault import."""
from contextlib import contextmanager
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import stat
import sys
import uuid
import warnings

REFERENCES = Path(__file__).with_name("credential-references.json")


def _vault_credential(relative: str) -> dict:
    path = Path(os.environ.get("FLOCK_CREDENTIAL_REFERENCES", REFERENCES))
    try:
        manifest = json.loads(path.read_text())
        matches = [e for e in manifest["entries"] if e["relative_path"] == relative]
        if len(matches) != 1:
            raise ValueError()
        reference = matches[0]["credential_json_ref"]
        # The references use stable vault/item IDs, with no resolved secrets.
        if not re.fullmatch(r"op://[a-z0-9]{26}/[a-z0-9]{26}/credential_json", reference):
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError("Missing or invalid credential reference; check FLOCK_CREDENTIAL_REFERENCES") from None
    try:
        result = subprocess.run(["op", "read", reference], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError("1Password unavailable; verify CLI access to Infra") from None
    if result.returncode:
        raise ValueError("1Password read failed; verify CLI access to Infra")
    try:
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Invalid credential JSON in 1Password") from None
    return value


LOCAL_STORE = Path.home()/".local/share/flockinator/controller-secrets/credentials.json"
MAX_STORE_BYTES = 131072
MAX_NODES = 512  # Input/storage bound, independent of any deployment's fleet size.


def store_path() -> Path:
    return Path(os.environ.get("FLOCK_CREDENTIAL_STORE", LOCAL_STORE)).expanduser()


def _private_stat(info, directory=False):
    required = stat.S_ISDIR if directory else stat.S_ISREG
    if not required(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("Controller credential store must be user-owned and private (directory 0700, file 0600)")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


@contextmanager
def _store_parent(path, *, create=False, allow_missing=False):
    """Pin every directory without following symlinks, including ancestors."""
    path = Path(path).expanduser()
    if ".." in path.parts or path.name in ("", ".", ".."):
        raise ValueError("Choose a credential file path without parent traversal")
    path = path.absolute()
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parent.parts[1:]:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    if allow_missing:
                        yield None
                        return
                    raise
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass  # Another creator must still pass open/stat validation.
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            info = os.fstat(fd)
            # Permit root-owned sticky /tmp, but no other shared writable ancestor.
            sticky_root = info.st_uid == 0 and info.st_mode & stat.S_ISVTX
            if info.st_uid not in (0, os.getuid()) or (info.st_mode & 0o022 and not sticky_root):
                raise ValueError("Credential path has an unsafe ancestor directory")
        _private_stat(os.fstat(fd), directory=True)
        yield fd
    finally:
        os.close(fd)


def _exists_at(fd, name):
    try:
        os.stat(name, dir_fd=fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


def _check_destination(path):
    try:
        with _store_parent(path, allow_missing=True) as fd:
            if fd is not None and _exists_at(fd, path.name):
                raise ValueError("Local controller store already exists; it will not be overwritten")
    except OSError:
        raise ValueError("Invalid or insecure controller credential destination") from None


def _validate_record(relative, value):
    if relative == "wifi.json":
        if (not isinstance(value, dict) or set(value) != {"ssid", "password"}
                or not all(isinstance(v, str) for v in value.values())
                or not 1 <= len(value["ssid"].encode()) <= 32
                or not 8 <= len(value["password"].encode()) <= 63
                or any(ord(c) < 32 or ord(c) == 127 for v in value.values() for c in v)):
            raise ValueError("Invalid Wi-Fi credential schema")
    else:
        match = re.fullmatch(r"nodes/([0-9A-F]{2}(?:-[0-9A-F]{2}){5})\.json", relative)
        if (not match or not isinstance(value, dict) or set(value) != {"base_mac", "key"}
                or value["base_mac"] != match[1].replace("-", ":")
                or not isinstance(value["key"], str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value["key"])):
            raise ValueError("Invalid management credential or board identity")
    return value


def _read_local(path):
    try:
        with _store_parent(path) as parent:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(fd, encoding="utf-8") as source:
                _private_stat(os.fstat(source.fileno()))
                if os.fstat(source.fileno()).st_size > MAX_STORE_BYTES:
                    raise ValueError("Oversized controller credential store")
                raw = source.read(MAX_STORE_BYTES + 1)
                if len(raw.encode()) > MAX_STORE_BYTES:
                    raise ValueError("Oversized controller credential store")
                value = json.loads(raw, object_pairs_hook=_unique_object)
        if not isinstance(value, dict) or set(value) != {"version", "credentials"} or type(value["version"]) is not int or value["version"] != 1 or not isinstance(value["credentials"], dict):
            raise ValueError("Invalid controller credential store")
        for relative, record in value["credentials"].items():
            _validate_record(relative, record)
        return value["credentials"]
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        raise ValueError("Invalid or insecure local controller credential store; repair it explicitly (no vault fallback)") from None


def _credential(relative: str) -> dict:
    path = store_path()
    try:
        with _store_parent(path, allow_missing=True) as parent:
            exists = parent is not None and _exists_at(parent, path.name)
    except (OSError, ValueError):
        raise ValueError("Invalid or insecure local controller credential store; no vault fallback") from None
    if exists:
        records = _read_local(path)
        if relative not in records:
            raise ValueError("Credential missing from local controller store; review the store and roster explicitly")
        return records[relative]
    return _vault_credential(relative)


def write_local_store(records: dict, path: Path | None = None) -> None:
    if not isinstance(records, dict) or not records:
        raise ValueError("Expected credential records")
    for relative, value in records.items():
        _validate_record(relative, value)
    payload = json.dumps({"version": 1, "credentials": records}).encode("utf-8")
    if len(payload) > MAX_STORE_BYTES:
        raise ValueError("Oversized controller credential store")
    path = Path(path).expanduser() if path is not None else store_path()
    _check_destination(path)
    try:
        with _store_parent(path, create=True) as parent:
            if _exists_at(parent, path.name):
                raise ValueError("Local controller store already exists; it will not be overwritten")
            temp = ".credentials-" + uuid.uuid4().hex
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent)
            try:
                with os.fdopen(fd, "wb") as target:
                    os.fchmod(target.fileno(), 0o600)
                    target.write(payload)
                    target.flush()
                    os.fsync(target.fileno())
                # Link atomically publishes the complete file and cannot replace anything.
                os.link(temp, path.name, src_dir_fd=parent, dst_dir_fd=parent,
                        follow_symlinks=False)
            finally:
                os.unlink(temp, dir_fd=parent)
            os.fsync(parent)
    except OSError:
        raise ValueError("Controller store creation could not be confirmed; inspect the destination before retrying (no overwrite)") from None


def load_roster(path: Path, expected_nodes: int) -> tuple[str, ...]:
    """Load only the operator's explicit identity roster; never use owner inventory."""
    if type(expected_nodes) is not int or not 1 <= expected_nodes <= MAX_NODES:
        raise ValueError(f"Expected node count must be between 1 and {MAX_NODES}")
    try:
        fd = os.open(Path(path).expanduser(), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, encoding="utf-8") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_STORE_BYTES:
                raise ValueError()
            raw = source.read(MAX_STORE_BYTES + 1)
            if len(raw.encode()) > MAX_STORE_BYTES:
                raise ValueError()
            value = json.loads(raw, object_pairs_hook=_unique_object)
        if (not isinstance(value, dict) or set(value) != {"version", "nodes"}
                or type(value["version"]) is not int or value["version"] != 1
                or not isinstance(value["nodes"], list) or len(value["nodes"]) != expected_nodes):
            raise ValueError()
        labels, macs = set(), []
        for node in value["nodes"]:
            if (not isinstance(node, dict) or set(node) != {"label", "base_mac"}
                    or not isinstance(node["label"], str)
                    or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", node["label"])
                    or not isinstance(node["base_mac"], str)):
                raise ValueError()
            mac = node["base_mac"].upper()
            if (not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", mac)
                    or mac == "00:00:00:00:00:00" or int(mac[:2], 16) & 1
                    or mac in macs or node["label"].casefold() in labels):
                raise ValueError()
            labels.add(node["label"].casefold())
            macs.append(mac)
        return tuple(macs)
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        raise ValueError("Invalid node roster: require unique labels and unicast identities matching the expected node count") from None


def _read_wifi(*, stdin=False):
    try:
        if stdin:
            if sys.stdin.isatty():
                raise ValueError()
            info = os.fstat(sys.stdin.fileno())
            if stat.S_ISREG(info.st_mode):
                _private_stat(info)
            elif not (stat.S_ISFIFO(info.st_mode) or stat.S_ISSOCK(info.st_mode)):
                raise ValueError()
            raw = sys.stdin.read(4097)
            if len(raw.encode()) > 4096:
                raise ValueError()
            wifi = json.loads(raw, object_pairs_hook=_unique_object)
        else:
            # getpass normally falls back to echoed input without a TTY. Fail closed.
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                ssid = getpass.getpass("Wi-Fi SSID (hidden): ")
                password = getpass.getpass("Wi-Fi password (hidden): ")
                if password != getpass.getpass("Confirm Wi-Fi password (hidden): "):
                    raise ValueError()
            wifi = {"ssid": ssid, "password": password}
        return _validate_record("wifi.json", wifi)
    except (OSError, ValueError, TypeError, EOFError, getpass.GetPassWarning, RecursionError):
        raise ValueError("Invalid Wi-Fi input or protected input unavailable; use hidden prompts or trusted non-terminal --wifi-stdin JSON") from None


def initialize_local_store(roster: Path, expected_nodes: int, path: Path, *,
                           wifi_stdin=False, dry_run=False) -> int:
    macs = load_roster(roster, expected_nodes)
    path = Path(path).expanduser()
    _check_destination(path)
    if dry_run:
        return len(macs)
    records = {"wifi.json": _read_wifi(stdin=wifi_stdin)}
    keys = set()
    for mac in macs:
        key = secrets.token_hex(32)
        if key in keys or not re.fullmatch(r"[0-9a-f]{64}", key):
            raise ValueError("Management key generation failed; no store was created")
        keys.add(key)
        records["nodes/" + mac.replace(":", "-") + ".json"] = {"base_mac": mac, "key": key}
    write_local_store(records, path)
    return len(macs)


def import_vault() -> int:
    _check_destination(store_path())
    try:
        manifest = json.loads(Path(os.environ.get("FLOCK_CREDENTIAL_REFERENCES", REFERENCES)).read_text())
        relatives = [entry["relative_path"] for entry in manifest["entries"]]
        if not relatives or len(relatives) != len(set(relatives)):
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError("Invalid credential reference manifest") from None
    records = {}
    for relative in relatives:
        records[relative] = _validate_record(relative, _vault_credential(relative))
    write_local_store(records)
    return len(records)


def save_wifi() -> None:
    raise ValueError("save-wifi is disabled; use credentials init for a new store or import-vault for existing keys")


def load_wifi() -> dict:
    value = _credential("wifi.json")
    if (set(value) != {"ssid", "password"}
            or not all(isinstance(v, str) for v in value.values())
            or not 1 <= len(value["ssid"].encode()) <= 32
            or not 8 <= len(value["password"].encode()) <= 63):
        raise ValueError("Invalid Wi-Fi credential schema")
    return value


def management_key(mac: str, create: bool = False) -> bytes:
    from .protocol import valid_mac
    if not valid_mac(mac):
        raise ValueError("Invalid factory MAC")
    # Provisioning may request create=True; always reuse the identity-bound controller/vault
    # record. Missing records require explicit credential creation, never rotation.
    value = _credential("nodes/" + mac.replace(":", "-") + ".json")
    if (set(value) != {"base_mac", "key"} or value["base_mac"] != mac
            or not isinstance(value["key"], str)
            or not re.fullmatch(r"[0-9a-fA-F]{64}", value["key"])):
        raise ValueError("Invalid management credential or board identity")
    return bytes.fromhex(value["key"])


def add_credential_arguments(parser):
    sub = parser.add_subparsers(dest="credential_command", required=True)
    init = sub.add_parser("init", help="Create a new private store using your own Wi-Fi and node roster")
    init.add_argument("--store", type=Path, required=True, help="Explicit new credential file path")
    init.add_argument("--roster", type=Path, required=True, help="Version-1 JSON identity roster")
    init.add_argument("--expected-nodes", type=int, required=True, help="Independently reviewed node count")
    init.add_argument("--wifi-stdin", action="store_true", help="Read Wi-Fi JSON from a trusted pipe or private file descriptor")
    init.add_argument("--dry-run", action="store_true", help="Check roster/destination without reading Wi-Fi, generating keys or writing")
    sub.add_parser("import-vault", help="Explicitly import existing vault records without rotating keys")


def run_credential_command(args, parser):
    try:
        if args.credential_command == "init":
            count = initialize_local_store(args.roster, args.expected_nodes, args.store,
                                           wifi_stdin=args.wifi_stdin, dry_run=args.dry_run)
            if args.dry_run:
                print(f"Validated {count} node identities and an unused destination; no Wi-Fi read, keys generated or files written.")
            else:
                print(f"Created a private version-1 store with Wi-Fi and {count} independent node keys; no existing credentials changed.")
        else:
            count = import_vault()
            print(f"Imported {count} credential records into the private local controller store.")
    except ValueError as error:
        parser.exit(1, str(error) + "\n")
    except (OSError, EOFError, KeyboardInterrupt):
        parser.exit(1, "Credential operation interrupted or unavailable; inspect the destination before retrying.\n")


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Controller credential storage")
    add_credential_arguments(parser)
    run_credential_command(parser.parse_args(argv), parser)


if __name__ == "__main__":
    main()
