# Independent owner credential setup

The node commissioner can create a private controller store entirely from your
own verified node identities and Wi-Fi. No original owner inventory, vault,
credential-reference manifest, or `op` executable is needed for initialization
or subsequent reads of a complete local store. This guide covers host credential
preparation; it establishes no hardware acceptance or new experimental result.

Run these steps on your authorized POSIX control host. Do not initialize real
credentials on a development or review host whose policy prohibits secret files.
Use a directory outside the source repository, owned by your user and inaccessible
to other users. The store is plaintext protected by filesystem permissions;
protect its backups as credentials too.

## Prepare and review your roster

Create a JSON file outside the repository with this schema. The two entries
below are **synthetic examples**, not identities to provision:

```json
{
  "version": 1,
  "nodes": [
    {"label": "A1", "base_mac": "02:00:00:00:00:01"},
    {"label": "A2", "base_mac": "02:00:00:00:00:02"}
  ]
}
```

Replace every entry with a physical node identity you have independently
verified. `base_mac` means the node's factory base MAC, not an access-point,
USB-port, or derived interface identifier. The command checks syntax and
uniqueness; it cannot establish that the MAC belongs to the physical board.
Keep the real roster private and review its expected node count separately.

The schema is exact: no key values or extra fields. Labels must start with a
letter or digit, use only letters, digits, `_` or `-`, and be at most 32
characters. Labels must be unique ignoring case. MACs use six colon-separated
hexadecimal pairs; lowercase is normalized to uppercase. Duplicate, all-zero,
broadcast and multicast identities are rejected. Locally administered unicast
addresses are accepted without imposing a vendor prefix. The count must match
`--expected-nodes`; the input safety bound is 512 nodes and 128 KiB, not a fixed
deployment size.

The credential roster is independent of the commissioning inventory. Its labels
are validated but are not added to the version-1 credential store, which maps
keys to MACs. Retain your reviewed roster separately. Existing firmware and the
`provision` command still use the A1–D4 label scheme; credential initialization
does not generalize firmware labels or rewrite inventory. Use `--inventory` to
select your own private commissioning CSV as described below. Routine commands
can also use an explicit verified `--mac` with `--port` or `--address` instead of
resolving an inventory label.

## Initialize a new store

Set `FLOCK_NODE_ROSTER` to your private roster path and `FLOCK_NODE_COUNT` to the
reviewed count. Neither variable contains Wi-Fi credentials or keys. From the
repository root:

```sh
export FLOCK_CREDENTIAL_STORE="$HOME/.local/share/flockinator/controller-secrets/credentials.json"
uv run --project tools/node-commissioner python -m node_commissioner credentials init \
  --store "$FLOCK_CREDENTIAL_STORE" --roster "$FLOCK_NODE_ROSTER" \
  --expected-nodes "$FLOCK_NODE_COUNT" --dry-run
```

Dry-run checks the roster and existing destination path components, then prints
only the count and validation outcome. It does not read Wi-Fi, generate keys,
create directories, or invoke a vault. It cannot prove later write access or
validate a password that has not yet been entered.

Run the same command without `--dry-run` when ready. Enter the SSID, password,
and password confirmation at the hidden prompts. Terminal echo suppression is
required; unavailable protected input aborts rather than falling back to echoed
input. SSIDs must be 1–32 UTF-8 bytes and passwords 8–63 UTF-8 bytes; control
characters are rejected. Open networks and 64-digit raw PSKs are not supported.

The command generates an independent cryptographically random 32-byte key for
each node and refuses a duplicate generated key. It validates all records before
writing, creates missing directories with mode 0700, and atomically publishes a
complete version-1 file with mode 0600. It rejects symlink destination components,
parent traversal (`..`), unsafe ancestors, and any existing destination including
a file, directory, or dangling symlink. Use the real filesystem path when a
platform's convenience path is a symlink. Existing permissions are never
silently repaired, and a concurrent creator cannot be overwritten.

Success reports only the count. It prints no SSID, password, keys, labels, MACs,
roster, or destination path. Export the same `FLOCK_CREDENTIAL_STORE` in later
shells before commissioner commands; passing `--store` during initialization
does not persist a shell setting. The default path above also works without the
variable. The standalone `python -m node_commissioner.credentials init` entry
point accepts the same options.

For automation, add `--wifi-stdin` and supply a single JSON object with exactly
the string fields `ssid` and `password` through a trusted pipe or a user-owned
private regular-file descriptor. Input is limited to 4096 UTF-8 bytes and must
end at EOF. A terminal, a shared-readable file, malformed JSON or duplicate
fields are rejected. This mode intentionally omits interactive confirmation.
Do not put credentials in shell arguments, environment variables, shell history,
here-documents, traced commands, or logged producer output. Prefer hidden prompts
unless you already have a protected credential producer. This repository
provides no sample containing real Wi-Fi values.

## Use your store for commissioning

Prepare a private CSV inventory with at least `label,factory_base_mac,status`
columns and the same labels and verified factory MACs as your roster. For the
synthetic two-node example only, its shape is:

```csv
label,factory_base_mac,status
A1,02:00:00:00:00:01,unprovisioned
A2,02:00:00:00:00:02,unprovisioned
```

Set `FLOCK_NODE_INVENTORY` to that private CSV and `FLOCK_EVIDENCE_ROOT` to a
private evidence directory. Keep `FLOCK_CREDENTIAL_STORE` set to the initialized
store. Once you have separately selected a reviewed complete initial-install
manifest and identified the physical board and port, the commissioning command
uses all three private locations explicitly:

```sh
uv run --project tools/node-commissioner python -m node_commissioner provision \
  --label A1 --mac "$FLOCKINATOR_NODE_MAC" --port "$FLOCKINATOR_NODE_PORT" \
  --manifest "$FLOCKINATOR_MANIFEST" --inventory "$FLOCK_NODE_INVENTORY" \
  --evidence-root "$FLOCK_EVIDENCE_ROOT"
```

This is a hardware-changing command, unlike credential initialization. Follow
the commissioner backup and release checks before executing it. It reuses the
saved key for the exact MAC, validates your private inventory binding, and updates
that CSV after successful provisioning. Public example inventory bindings are
not modified. `--inventory` also selects label resolution for routine commands;
`test` and `accept` support `--evidence-root` too. Without these explicit options,
the historical repository inventory and evidence defaults remain in effect.
Firmware artifacts and physical acceptance are separate requirements; initializing
credentials does not supply a release or prove a working board.

## Preserve existing keys

Initialization is creation only: there is no overwrite, merge, or rotation flag.
Rerunning it against an existing destination fails before asking for Wi-Fi or
generating keys. The legacy `import-vault` command remains an explicit alternative
for importing your existing keys. Never initialize a new store to restore access
to nodes that already have keys; securely restore or copy their matching store.

Routine local reads accept the version-1 format. An invalid or insecure store,
or a missing node within an existing store, fails without a vault fallback.
Provisioning's `management_key(create=True)` reuses the saved key; it never
generates a replacement implicitly. Adding nodes or rotating keys is outside
this creation-only workflow and needs a separate reviewed migration.

A failure before publication leaves no partial destination. An interruption or
filesystem error after publication can leave a complete store: inspect the
destination privately before retrying, and do not delete it just to make a retry
succeed. Interrupted temporary files, if any, remain private. Initialization
does not contact nodes, configure Wi-Fi on devices, flash firmware, rewrite
scientific artifacts, or establish acceptance; those remain separate steps in
the [commissioner workflow](../tools/node-commissioner/README.md).
