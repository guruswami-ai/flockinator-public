"""Synthetic credentials only: no vault, hardware, or real credential initialization."""
import io
import json
import os
from pathlib import Path
import stat
import warnings

import pytest

from node_commissioner import credentials as creds
from node_commissioner import __main__ as cli

MACS = ("02:00:00:00:00:01", "02:00:00:00:00:02")
WIFI = {"ssid": "synthetic-test-network", "password": "synthetic-password"}


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("FLOCK_CREDENTIAL_STORE", str(tmp_path / "private" / "credentials.json"))
    monkeypatch.setenv("FLOCK_CREDENTIAL_REFERENCES", str(tmp_path / "absent-references.json"))
    monkeypatch.setenv("PATH", str(tmp_path / "no-op-executable"))
    def absent_op(*args, **kwargs):
        pytest.fail("Fresh-owner credentials must not invoke any subprocess or vault")
    monkeypatch.setattr(creds.subprocess, "run", absent_op)
    counter = iter(range(1, 1000))
    def synthetic_key(size):
        assert size == 32
        return next(counter).to_bytes(32, "big").hex()
    monkeypatch.setattr(creds.secrets, "token_hex", synthetic_key)


@pytest.fixture
def roster(tmp_path):
    path = tmp_path / "roster.json"
    path.write_text(json.dumps({"version": 1, "nodes": [
        {"label": f"bench-{i}", "base_mac": mac} for i, mac in enumerate(MACS)]}))
    return path


@pytest.fixture
def prompts(monkeypatch):
    answers = iter([WIFI["ssid"], WIFI["password"], WIFI["password"]])
    monkeypatch.setattr(creds.getpass, "getpass", lambda prompt: next(answers))


def records():
    return {"wifi.json": dict(WIFI), "nodes/02-00-00-00-00-01.json":
            {"base_mac": MACS[0], "key": "ab" * 32}}


def test_fresh_owner_round_trip_version_one_and_no_implicit_rotation(roster, prompts):
    path = creds.store_path()
    assert creds.initialize_local_store(roster, 2, path) == 2
    raw = path.read_bytes()
    value = json.loads(raw)
    assert value["version"] == 1
    assert len(value["credentials"]) == 3
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert creds.load_wifi() == WIFI
    first, second = [creds.management_key(mac, create=True) for mac in MACS]
    assert len(first) == len(second) == 32 and first != second
    assert creds.management_key(MACS[0], create=True) == first
    with pytest.raises(ValueError, match="missing"):
        creds.management_key("02:00:00:00:00:03", create=True)
    assert path.read_bytes() == raw
    with pytest.raises(ValueError, match="already exists"):
        creds.initialize_local_store(roster, 2, path)
    assert path.read_bytes() == raw


def test_existing_version_one_records_remain_readable():
    creds.write_local_store(records())
    assert creds.load_wifi() == WIFI
    assert creds.management_key(MACS[0]) == bytes.fromhex("ab" * 32)


@pytest.mark.parametrize("entrypoint,prefix", [(creds.main, []), (cli.main, ["credentials"])])
def test_command_creates_only_explicit_destination_and_redacts(entrypoint, prefix, roster, prompts, tmp_path, capsys):
    path = tmp_path / "chosen" / "credentials.json"
    entrypoint(prefix + ["init", "--roster", str(roster), "--expected-nodes", "2", "--store", str(path)])
    output = capsys.readouterr()
    assert "2 independent node keys" in output.out
    assert output.err == ""
    for value in (*MACS, *WIFI.values(), str(path), str(roster), "bench-0",
                  (1).to_bytes(32, "big").hex()):
        assert value not in output.out
    assert not creds.store_path().exists()


def test_dry_run_is_pure_and_never_reads_wifi_or_generates_keys(roster, monkeypatch, capsys):
    def unexpected(*a, **kw):
        pytest.fail("dry run touched Wi-Fi or randomness")
    monkeypatch.setattr(creds, "_read_wifi", unexpected)
    monkeypatch.setattr(creds.secrets, "token_hex", unexpected)
    path = creds.store_path()
    cli.main(["credentials", "init", "--roster", str(roster), "--expected-nodes", "2",
              "--store", str(path), "--dry-run", "--wifi-stdin"])
    assert "Validated 2 node identities" in capsys.readouterr().out
    assert not path.parent.exists()


@pytest.mark.parametrize("count", [0, -1, 1, 3, 513, True])
def test_expected_count_is_explicit_and_checked(roster, count):
    with pytest.raises(ValueError):
        creds.initialize_local_store(roster, count, creds.store_path())
    assert not creds.store_path().parent.exists()


def test_count_not_tied_to_owner_fleet(roster):
    nodes = [{"label": f"test-{i}", "base_mac": f"02:00:00:00:01:{i:02X}"} for i in range(19)]
    roster.write_text(json.dumps({"version": 1, "nodes": nodes}))
    assert len(creds.load_roster(roster, 19)) == 19


@pytest.mark.parametrize("change", [
    {"base_mac": "00:00:00:00:00:00"}, {"base_mac": "FF:FF:FF:FF:FF:FF"},
    {"base_mac": "01:00:00:00:00:01"}, {"base_mac": "02-00-00-00-00-01"},
    {"base_mac": " 02:00:00:00:00:01"}, {"base_mac": None},
    {"base_mac": MACS[1]}, {"label": "BENCH-1"}, {"label": "../../escape"},
    {"label": ""}, {"key": "unexpected-secret"},
])
def test_roster_identity_validation(roster, change):
    value = json.loads(roster.read_text())
    value["nodes"][0].update(change)
    roster.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="Invalid node roster") as error:
        creds.load_roster(roster, 2)
    assert "unexpected-secret" not in str(error.value)


@pytest.mark.parametrize("content", [
    '{"version":1,"version":1,"nodes":[]}', '{"version":true,"nodes":[]}',
    '[]', '{"version":1,"nodes":{}}', 'malformed-private-content',
    '{"version":1,"nodes":[],"extra":true}', 'x' * (creds.MAX_STORE_BYTES + 1),
    '[' * 2000,
])
def test_malformed_roster_is_sanitized(roster, content):
    roster.write_text(content)
    with pytest.raises(ValueError, match="Invalid node roster"):
        creds.load_roster(roster, 2)


def test_mac_normalization_and_collision(roster):
    value = {"version": 1, "nodes": [{"label": "one", "base_mac": "02:aa:bb:cc:dd:ee"}]}
    roster.write_text(json.dumps(value))
    assert creds.load_roster(roster, 1) == ("02:AA:BB:CC:DD:EE",)
    value["nodes"].append({"label": "two", "base_mac": "02:AA:BB:CC:DD:EE"})
    roster.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        creds.load_roster(roster, 2)


@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "dangling"])
def test_destination_never_overwritten_or_prompted(roster, tmp_path, kind, monkeypatch):
    path = creds.store_path()
    path.parent.mkdir(mode=0o700)
    other = tmp_path / "sentinel"
    other.write_bytes(b"sentinel")
    if kind == "file":
        path.write_bytes(b"original")
    elif kind == "directory":
        path.mkdir()
    else:
        path.symlink_to(other if kind == "symlink" else tmp_path / "absent")
    def unexpected(*a, **kw): pytest.fail("Prompted despite occupied destination")
    monkeypatch.setattr(creds, "_read_wifi", unexpected)
    with pytest.raises(ValueError, match="already exists"):
        creds.initialize_local_store(roster, 2, path)
    assert other.read_bytes() == b"sentinel"
    if kind == "file":
        assert path.read_bytes() == b"original"


@pytest.mark.parametrize("at_parent", [True, False])
def test_symlink_in_destination_path_is_rejected(tmp_path, at_parent):
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    path = alias / "credentials.json" if at_parent else alias / "nested" / "credentials.json"
    with pytest.raises(ValueError):
        creds.write_local_store(records(), path)
    assert list(real.iterdir()) == []


def test_unsafe_parent_and_ancestor_permissions_rejected(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir(mode=0o777)
    shared.chmod(0o777)
    private = shared / "private"
    private.mkdir(mode=0o700)
    for path in (shared / "credentials.json", private / "credentials.json"):
        with pytest.raises(ValueError):
            creds.write_local_store(records(), path)
        assert not path.exists()


def test_wrong_owner_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(creds.os, "getuid", lambda: os.stat(tmp_path).st_uid + 1000)
    with pytest.raises(ValueError):
        creds.write_local_store(records())


def test_relative_spaces_tilde_paths_and_new_parent_permissions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    old_umask = os.umask(0)
    try:
        creds.write_local_store(records(), Path("new parent/nested/credentials.json"))
    finally:
        os.umask(old_umask)
    assert stat.S_IMODE(Path("new parent").stat().st_mode) == 0o700
    assert stat.S_IMODE(Path("new parent/nested").stat().st_mode) == 0o700
    monkeypatch.setenv("HOME", str(tmp_path))
    creds.write_local_store(records(), Path("~/tilde/credentials.json"))
    assert (tmp_path / "tilde/credentials.json").exists()
    with pytest.raises(ValueError, match="parent traversal"):
        creds.write_local_store(records(), Path("new parent/../escape.json"))


def test_racing_creator_cannot_be_overwritten(monkeypatch):
    path = creds.store_path()
    link = os.link
    def race(src, dst, **kwargs):
        path.write_bytes(b"winning-store")
        return link(src, dst, **kwargs)
    monkeypatch.setattr(creds.os, "link", race)
    with pytest.raises(ValueError, match="no overwrite"):
        creds.write_local_store(records())
    assert path.read_bytes() == b"winning-store"
    assert list(path.parent.iterdir()) == [path]


def test_parent_swap_does_not_redirect_publication_or_cleanup(tmp_path, monkeypatch):
    path = creds.store_path()
    other = tmp_path / "other"
    other.mkdir(mode=0o700)
    pinned = tmp_path / "pinned"
    link = os.link
    def swap(src, dst, **kwargs):
        path.parent.rename(pinned)
        path.parent.symlink_to(other, target_is_directory=True)
        return link(src, dst, **kwargs)
    monkeypatch.setattr(creds.os, "link", swap)
    creds.write_local_store(records())
    assert list(other.iterdir()) == []
    assert [p.name for p in pinned.iterdir()] == ["credentials.json"]
    with pytest.raises(ValueError, match="insecure"):
        creds.load_wifi()


@pytest.mark.parametrize("operation", ["fsync", "link", "fchmod"])
def test_write_failure_leaves_no_partial_store_or_temp(monkeypatch, operation):
    def fail(*a, **kw): raise OSError("synthetic-secret-path")
    monkeypatch.setattr(creds.os, operation, fail)
    with pytest.raises(ValueError) as error:
        creds.write_local_store(records())
    assert "synthetic-secret-path" not in str(error.value)
    assert list(creds.store_path().parent.iterdir()) == []


def test_rng_collision_fails_before_writing(roster, prompts, monkeypatch):
    monkeypatch.setattr(creds.secrets, "token_hex", lambda size: "ab" * 32)
    with pytest.raises(ValueError, match="generation failed"):
        creds.initialize_local_store(roster, 2, creds.store_path())
    assert not creds.store_path().parent.exists()


@pytest.mark.parametrize("kind", ["bad_json", "duplicate", "insecure_file", "fifo", "symlink"])
def test_bad_local_store_never_falls_back_to_vault(kind, tmp_path):
    path = creds.store_path()
    path.parent.mkdir(mode=0o700)
    if kind == "fifo":
        os.mkfifo(path, mode=0o600)
    elif kind == "symlink":
        path.symlink_to(tmp_path / "absent")
    else:
        path.write_text('{"version":1,"version":1,"credentials":{}}' if kind == "duplicate" else "private-invalid-json")
        path.chmod(0o644 if kind == "insecure_file" else 0o600)
    with pytest.raises(ValueError, match="insecure"):
        creds.load_wifi()


@pytest.mark.parametrize("value", [
    {"ssid": "", "password": "synthetic-password"},
    {"ssid": "é" * 17, "password": "synthetic-password"},
    {"ssid": "test", "password": "short"},
    {"ssid": "test", "password": "é" * 32},
    {"ssid": "test\x00hidden", "password": "synthetic-password"},
    {"ssid": "test", "password": "secret\nnewline"},
    {"ssid": "test", "password": 12345678},
    {"ssid": "test", "password": "synthetic-password", "key": "extra"},
])
def test_wifi_validation(value):
    with pytest.raises(ValueError):
        creds._validate_record("wifi.json", value)


def test_wifi_utf8_byte_boundaries():
    wifi = {"ssid": "é" * 16, "password": "é" * 4}
    assert creds._validate_record("wifi.json", wifi) == wifi


def test_getpass_echo_fallback_aborts_without_prompting_again(monkeypatch):
    calls = []
    def fallback(prompt):
        calls.append(prompt)
        warnings.warn("echo fallback", creds.getpass.GetPassWarning)
        pytest.fail("echo fallback was not stopped")
    monkeypatch.setattr(creds.getpass, "getpass", fallback)
    with pytest.raises(ValueError, match="protected input"):
        creds._read_wifi()
    assert len(calls) == 1


def test_mismatched_password_fails_without_echoing(monkeypatch):
    answers = iter([WIFI["ssid"], WIFI["password"], "different-synthetic-password"])
    monkeypatch.setattr(creds.getpass, "getpass", lambda prompt: next(answers))
    with pytest.raises(ValueError) as error:
        creds._read_wifi()
    assert WIFI["password"] not in str(error.value)


def test_trusted_stdin_pipe(monkeypatch):
    read, write = os.pipe()
    os.write(write, json.dumps(WIFI).encode())
    os.close(write)
    with os.fdopen(read) as stream:
        monkeypatch.setattr(creds.sys, "stdin", stream)
        assert creds._read_wifi(stdin=True) == WIFI


@pytest.mark.parametrize("raw,mode,ok", [
    (json.dumps(WIFI), 0o600, True), (json.dumps(WIFI), 0o644, False),
    ('{"ssid":"test","password":"synthetic-password","password":"duplicate"}', 0o600, False),
    ("synthetic-private-malformed-json", 0o600, False), ("x" * 4097, 0o600, False),
])
def test_stdin_file_permissions_bounds_and_errors(tmp_path, monkeypatch, raw, mode, ok):
    path = tmp_path / "synthetic-wifi.json"
    path.write_text(raw)
    path.chmod(mode)
    with path.open() as stream:
        monkeypatch.setattr(creds.sys, "stdin", stream)
        if ok:
            assert creds._read_wifi(stdin=True) == WIFI
        else:
            with pytest.raises(ValueError) as error:
                creds._read_wifi(stdin=True)
            assert WIFI["password"] not in str(error.value)


def test_stdin_tty_rejected(monkeypatch):
    class Terminal(io.StringIO):
        def isatty(self): return True
        def read(self, *args): pytest.fail("Read from echoed terminal")
    monkeypatch.setattr(creds.sys, "stdin", Terminal())
    with pytest.raises(ValueError, match="protected input"):
        creds._read_wifi(stdin=True)


def test_cli_wifi_errors_are_redacted(roster, monkeypatch, capsys):
    answers = iter([WIFI["ssid"], "short", "short"])
    monkeypatch.setattr(creds.getpass, "getpass", lambda prompt: next(answers))
    with pytest.raises(SystemExit) as error:
        cli.main(["credentials", "init", "--store", str(creds.store_path()),
                  "--roster", str(roster), "--expected-nodes", "2"])
    assert error.value.code == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "Traceback" not in output.err and "short" not in output.err
    assert WIFI["ssid"] not in output.err and MACS[0] not in output.err
    assert not creds.store_path().parent.exists()


def test_import_remains_explicit_and_compatible(tmp_path, monkeypatch):
    manifest = tmp_path / "refs.json"
    fixture = records()
    manifest.write_text(json.dumps({"entries": [{"relative_path": name} for name in fixture]}))
    monkeypatch.setenv("FLOCK_CREDENTIAL_REFERENCES", str(manifest))
    monkeypatch.setattr(creds, "_vault_credential", lambda name: fixture[name])
    assert creds.import_vault() == 2
    assert creds.load_wifi() == WIFI
    with pytest.raises(ValueError, match="already exists"):
        creds.import_vault()


def test_directory_sync_failure_preserves_complete_published_store(monkeypatch):
    fsync = os.fsync
    def fail_directory(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("synthetic failure after publication")
        fsync(fd)
    monkeypatch.setattr(creds.os, "fsync", fail_directory)
    with pytest.raises(ValueError, match="could not be confirmed"):
        creds.write_local_store(records())
    assert creds.load_wifi() == WIFI
    assert list(creds.store_path().parent.iterdir()) == [creds.store_path()]
    with pytest.raises(ValueError, match="already exists"):
        creds.write_local_store(records())


@pytest.mark.parametrize("kind", ["symlink", "fifo", "missing", "directory"])
def test_roster_requires_regular_file_without_following_symlink(roster, tmp_path, kind):
    path = tmp_path / "invalid-roster"
    if kind == "symlink":
        path.symlink_to(roster)
    elif kind == "fifo":
        os.mkfifo(path)
    elif kind == "directory":
        path.mkdir()
    with pytest.raises(ValueError, match="Invalid node roster"):
        creds.load_roster(path, 2)


def test_storage_bound_supports_maximum_roster(roster, prompts):
    roster.write_text(json.dumps({"version": 1, "nodes": [
        {"label": f"test-{i}", "base_mac": f"02:00:00:00:{i // 256:02X}:{i % 256:02X}"}
        for i in range(creds.MAX_NODES)]}))
    assert creds.initialize_local_store(roster, creds.MAX_NODES, creds.store_path()) == creds.MAX_NODES
    assert creds.store_path().stat().st_size <= creds.MAX_STORE_BYTES
    saved = creds._read_local(creds.store_path())
    assert len(saved) == creds.MAX_NODES + 1
    assert len({record["key"] for name, record in saved.items() if name != "wifi.json"}) == creds.MAX_NODES


def test_cli_initialization_from_stdin(roster, monkeypatch, capsys):
    read, write = os.pipe()
    os.write(write, json.dumps(WIFI).encode())
    os.close(write)
    with os.fdopen(read) as stream:
        monkeypatch.setattr(creds.sys, "stdin", stream)
        creds.main(["init", "--store", str(creds.store_path()), "--roster", str(roster),
                    "--expected-nodes", "2", "--wifi-stdin"])
    output = capsys.readouterr()
    assert "2 independent node keys" in output.out and output.err == ""
    assert WIFI["password"] not in output.out and MACS[0] not in output.out
    assert creds.load_wifi() == WIFI


def test_initialized_credentials_reach_private_inventory_provisioning(roster, prompts, tmp_path, monkeypatch, capsys):
    roster.write_text(json.dumps({"version": 1, "nodes": [
        {"label": f"A{i + 1}", "base_mac": mac} for i, mac in enumerate(MACS)]}))
    creds.initialize_local_store(roster, 2, creds.store_path())
    inventory = tmp_path / "own-inventory.csv"
    inventory.write_text(f"label,factory_base_mac,status\nA1,{MACS[0]},unprovisioned\n")
    evidence = tmp_path / "private-evidence"
    monkeypatch.setattr(cli, "ROOT", tmp_path / "no-repository-inventory")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    package = object()
    monkeypatch.setattr(cli, "load_initial_package", lambda path: package)
    calls = {}
    class Backend:
        def __init__(self, **kwargs): calls["backend"] = kwargs
        def close(self): calls["closed"] = True
    class Transaction:
        def __init__(self, **kwargs): calls["transaction"] = kwargs
        def run(self): return {"synthetic": True}
    monkeypatch.setattr(cli, "EsptoolBackend", Backend)
    monkeypatch.setattr(cli, "Provisioning", Transaction)
    cli.main(["provision", "--label", "A1", "--mac", MACS[0], "--port", "synthetic-port",
              "--manifest", str(tmp_path / "synthetic-manifest.json"),
              "--inventory", str(inventory), "--evidence-root", str(evidence)])
    capsys.readouterr()
    assert calls["closed"]
    transaction = calls["transaction"]
    assert transaction["inventory"] == inventory
    assert transaction["evidence_root"] == evidence
    assert transaction["wifi"] == WIFI
    assert transaction["key"] == creds.management_key(MACS[0])
    assert transaction["mac"] == MACS[0]
    assert transaction["package"] is package
    assert not evidence.exists()  # Fake backend/transaction: no physical provisioning.


def test_private_inventory_resolves_own_label_without_repository(tmp_path, monkeypatch):
    from argparse import Namespace
    inventory = tmp_path / "own-inventory.csv"
    inventory.write_text(f"label,factory_base_mac,status\nA1,{MACS[0]},unprovisioned\n")
    monkeypatch.setattr(cli, "ROOT", tmp_path / "no-repository-inventory")
    args = Namespace(label="A1", mac=None, address="192.0.2.1", port=None, inventory=inventory)
    cli.resolve_target(args)
    assert args.mac == MACS[0]
    args.mac = MACS[1]
    with pytest.raises(ValueError, match="conflicts"):
        cli.resolve_target(args)


def test_resolved_temp_alias_and_default_physical_home_store(tmp_path, monkeypatch):
    # Models macOS /var -> /private/var without trusting symlinks during writes.
    physical = tmp_path / "physical"
    physical.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(physical, target_is_directory=True)
    monkeypatch.delenv("FLOCK_CREDENTIAL_STORE")
    monkeypatch.setattr(creds, "LOCAL_STORE", physical / "home" / "private" / "credentials.json")
    creds.write_local_store(records())
    assert creds.load_wifi() == WIFI
    creds.write_local_store(records(), (alias / "temp-store" / "credentials.json").resolve())
    assert (physical / "temp-store" / "credentials.json").is_file()
