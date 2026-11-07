# Node commissioner

Controller bring-up client for the approved node specification. The current release supports USB identity assignment, private Wi-Fi/key provisioning, authenticated Wi-Fi status, display paging, a short tone, evidence capture and application OTA. The `provision` command provides a resumable backup/flash/configuration/inventory transaction. Explicit SD inspection/reset/testing is available via authenticated Wi-Fi or the legacy LilyGo ESP-NOW relay (recovery-only); see below.

Wi-Fi operations now require [management response authentication v1](../../docs/management-response-auth.md)
from the node, including the initial challenge reply. Legacy unsigned nodes fail
closed. Upgrade nodes through a separately trusted procedure before using this
host release; an unsigned update acknowledgement alone cannot establish success.
Keys and request signatures do not need rotation for this protocol change.
The response proof authenticates the exchange, not sensor truth, confidentiality
or physical acceptance.

Run from the repository root. Supply your own verified identity, address,
release artifacts and private inventory; these examples do not authorize a
deployment or certify any existing fleet.

```sh
uv run --project tools/node-commissioner python -m node_commissioner list
uv run --project tools/node-commissioner python -m node_commissioner status --label A1 --address "$FLOCKINATOR_NODE_ADDRESS"
uv run --project tools/node-commissioner python -m node_commissioner next-page --label A1 --address "$FLOCKINATOR_NODE_ADDRESS"
uv run --project tools/node-commissioner python -m node_commissioner tone --label A1 --address "$FLOCKINATOR_NODE_ADDRESS"
uv run --project tools/node-commissioner python -m node_commissioner test --label A1 --address "$FLOCKINATOR_NODE_ADDRESS" --seconds 120
```

Set `FLOCKINATOR_NODE_ADDRESS` from the identified node's current DHCP address. Omitting `--address` selects a USB device only when its serial matches the recorded factory MAC uniquely. `--port` is available explicitly, but status still verifies the actual board identity. Opening the USB port can reset this board; use Wi-Fi for uninterrupted observation.

For a newly identified controller, use `provision` with its physically assigned label, exact factory MAC, explicit USB port and the selected initial-install release manifest:

```sh
uv run --project tools/node-commissioner python -m node_commissioner provision \
  --label A2 --mac "$FLOCKINATOR_NODE_MAC" --port "$FLOCKINATOR_NODE_PORT" \
  --manifest "$FLOCKINATOR_MANIFEST" --inventory "$FLOCK_NODE_INVENTORY" \
  --evidence-root "$FLOCK_EVIDENCE_ROOT"
```

Set those variables from the identified controller and reviewed release before running. `FLOCK_NODE_INVENTORY` selects your private CSV with at least `label,factory_base_mac,status` columns, and `FLOCK_EVIDENCE_ROOT` selects your private evidence directory. Use the same verified identities as your credential roster; the [independent setup guide](../../docs/independent-fleet-setup.md) includes a synthetic schema example. Omitting these options retains the historical repository inventory and validation paths, whose example bindings are not your own board identities. Commands that resolve labels also accept `--inventory`; `test` and `accept` accept `--evidence-root` for private evidence. `list` shows USB descriptors; the transaction independently verifies the ROM factory MAC, chip, flash capacity and protection state. A complete initial-install manifest must include trusted hashes for `bootloader.bin`, `partitions.bin`, `ota_data_initial.bin` and `firmware.bin`, plus the firmware version and embedded application digest. These have fixed offsets `0`, `0x8000`, `0xF000` and `0x20000`. Application-only releases cannot be used for initial installation. Explicitly rejected and rollback-test packages are blocked; selecting a candidate manifest does not make it a fleet-approved release.

Unless `--skip-backup` is supplied or already recorded in that transaction, the command preserves a unique private full-flash backup and verifies it against the device before writing. It then verifies the shared firmware, saves the label, private Wi-Fi configuration and per-node management key, reboots, checks actual identity/build/core health and records `commissioned_for_installation`. Panel, speaker, SD-card and peer acceptance remain separate, so an unattached peripheral does not block installation. No card is formatted, no whole-flash erase is issued and no eFuses are changed.

If interrupted, leave the same controller connected and rerun the **same command with the same manifest**. The default journal is `~/.local/share/flockinator/commissioning/<MAC>/<label>-initial/`; its path is printed before work starts. Resume checks the device again and refuses changed package bytes, identity or management key. Backups and completed stage records are never overwritten. Use `--transaction <private-directory>` only for a deliberately separate commissioning run, then retain that same path for retries. For later application changes use `update`, rather than repeating initial installation.

The lower-level USB commands `assign`, `wifi`, `pair-key` and `reboot` remain available. `assign` changes only the firmware label; it does not execute the full commissioning transaction.

Wi-Fi and identity-bound management keys are read from the private controller store at `~/.local/share/flockinator/controller-secrets/credentials.json`. Set `FLOCK_CREDENTIAL_STORE` to choose another private file. A new owner can initialize this store using their own Wi-Fi and verified node roster, with no existing owner inventory, credential references, or 1Password installation.

On your authorized control host, prepare a private version-1 JSON roster containing `nodes` with unique `label` and `base_mac` fields. Set `FLOCK_NODE_ROSTER` to its path and `FLOCK_NODE_COUNT` to your independently reviewed node count. See the [independent fleet setup guide](../../docs/independent-fleet-setup.md) for the exact schema and protected input options. Check the roster and unused destination first:

```sh
export FLOCK_CREDENTIAL_STORE="$HOME/.local/share/flockinator/controller-secrets/credentials.json"
uv run --project tools/node-commissioner python -m node_commissioner credentials init \
  --store "$FLOCK_CREDENTIAL_STORE" --roster "$FLOCK_NODE_ROSTER" \
  --expected-nodes "$FLOCK_NODE_COUNT" --dry-run
```

Then run the same command **without `--dry-run`** to enter the SSID and password at hidden prompts (including password confirmation) and generate one independent random 256-bit management key per identity. Wi-Fi and key values never appear in command arguments or output. Dry-run reads no Wi-Fi, generates no keys, and writes nothing. Initialization refuses any existing destination, including a broken symlink; there is no overwrite or rotation flag. `management_key(create=True)` continues to reuse an existing identity-bound key and fails for missing local records.

For existing keys held in your own vault, the separate one-time importer remains available on an authorized control host (may require one 1Password unlock):

```sh
uv run --project tools/node-commissioner python -m node_commissioner.credentials import-vault
```

Both creation paths validate records before atomically publishing a complete version-1 store, create private 0700 directories and a 0600 file, and never replace an existing store. Use a user-owned private destination outside the repository with no symlink path components or shared writable ancestors; existing directory permissions are checked, not changed. These filesystem safeguards require a POSIX host with directory descriptors and hard links. The store contains actual shared management secrets and Wi-Fi credentials and must not be committed or included in ordinary source backups. The local file is the default once present; invalid, insecure or missing local records fail explicitly without silently prompting through the vault. Before a local store exists, the legacy vault provider remains available through a separately supplied reference manifest (`FLOCK_CREDENTIAL_REFERENCES` overrides its path); fresh-owner initialization does not use that provider.

For another authorized control host managing already provisioned nodes, securely copy the private directory with its owner-only permissions, or import the same existing keys there. Creating a new store generates different keys and cannot recover access to already keyed nodes. Initialization only prepares host credentials: it does not inspect, flash or provision hardware, change inventory, or update a handheld. `save-wifi` remains disabled; credential changes must be explicit. Raw flash backups remain separate private recovery material. Application OTA preserves the identity partition; a full erase does not.

Example application update after selecting an independently verified image:

```sh
uv run --project tools/node-commissioner python -m node_commissioner update \
  --label A1 --address "$FLOCKINATOR_NODE_ADDRESS" \
  --image "$FLOCKINATOR_IMAGE" --sha256 "$FLOCKINATOR_FILE_SHA256"
```

Set the image path and expected whole-file digest from the reviewed release;
private release binaries are not bundled in this public subset.

The supplied hash covers the whole file; runtime status reports the embedded ESP image digest, which is different. The client verifies both image integrity and the expected post-boot digest. SHA-256 alone is not publisher authentication: HMAC authorises the transfer using the private per-node key. HTTP payloads are not encrypted. This is local-network maintenance, not an internet-exposed service or a TLS deployment system.

Only record manual acceptance after observing that exact node:

```sh
uv run --project tools/node-commissioner python -m node_commissioner accept \
  --label A1 --address "$FLOCKINATOR_NODE_ADDRESS" --check panel --result pass
```

Checks also include `speaker`, `microphone_channels`, `button` and `motion`. These create separate operator records tied to the running build; automatic codec/driver success never supplies manual acceptance. `test` saves immutable snapshots and detects restart/build changes; it does not automatically declare every peripheral passed.

Validation:

```sh
uv run --project tools/node-commissioner python -m pytest tools/node-commissioner/tests -q
```

## LilyGo remote management (legacy / recovery-only)

Deprecated (advisory): the active management route is this commissioner
over authenticated Wi-Fi, driven from the Korvo solution. The LilyGo
console client below is retained only for ESP-NOW recovery of a node
whose Wi-Fi is broken.

The separate `node_commissioner.console` client uses a placeholder factory/STA
MAC in this public tree. Bind it consistently to the verified LilyGo identity
before hardware use. Set `FLOCKINATOR_LILYGO_PORT` to its verified USB port, distinct from a Waveshare node. Global options such as `--port`, `--mac` and `--output` go **before** the subcommand:

```sh
uv run --project tools/node-commissioner python -m node_commissioner.console \
  --port "$FLOCKINATOR_LILYGO_PORT" status
uv run --project tools/node-commissioner python -m node_commissioner.console \
  --port "$FLOCKINATOR_LILYGO_PORT" setup
```

`setup` privately loads the existing Wi-Fi file and the inventory's per-node keys, provisions Wi-Fi and registers known labels/MACs with the handheld. It does not fabricate entries for uncommissioned nodes. Repeat it after commissioning another node. Conflicting bindings are rejected. The current prototype requires console and nodes on the same 2.4 GHz access point/channel; health/deployment traffic uses ESP-NOW on that channel.

To store a reviewed node application on the console's SD card:

```sh
uv run --project tools/node-commissioner python -m node_commissioner.console \
  --port "$FLOCKINATOR_LILYGO_PORT" image \
  --image "$FLOCKINATOR_IMAGE" --sha256 "$FLOCKINATOR_FILE_SHA256" \
  --name "$FLOCKINATOR_IMAGE_NAME"
```

Choose a unique name of at most 63 characters containing letters, digits, `.`, `_` or `-`, beginning with a letter or digit. Existing images are not overwritten. The file is published under `/flockinator/images/` only after verification. The reported `image_sha256` is the embedded runtime digest; use that different digest for deployment:

```sh
uv run --project tools/node-commissioner python -m node_commissioner.console \
  --port "$FLOCKINATOR_LILYGO_PORT" deploy \
  --label A1 --name "$FLOCKINATOR_IMAGE_NAME" \
  --image-sha256 "$FLOCKINATOR_IMAGE_SHA256" --timeout 900
```

This starts one node's ESP-NOW transfer and keeps the same serial connection open while reporting progress. Success requires a fresh authenticated report from the same target, a changed boot count, the expected image digest and valid OTA state. Command acceptance or completed byte transfer alone is not success. If the host times out or disconnects, the controller operation may still be running; inspect status before attempting another deployment. Do not open a competing serial monitor or repeatedly reconnect USB during transfer, because reopening the port can reset the handheld.

The current implementation is an integration prototype. Actual transfer and recovery acceptance are tracked in private cluster-deployment records, which are not bundled in this public subset; these usage examples do not establish that the hardware tests passed. The [console README](../../firmware/management-console/README.md) describes touch controls, freshness states, SD storage and the live JSON protocol. Its historical single-character serial soak tool does not apply to live firmware.


## SD maintenance

Firmware node 0.5.1 and console 0.2.11 support remote card maintenance, including nodes without DHCP. Identify the node and its current card before erasing. Each destructive run needs explicit authorization for that identified card. Nothing formats automatically on boot, inspection or timeout.

```sh
# Read-only inspection and a short-lived card-bound permit:
uv run --project tools/node-commissioner python -m node_commissioner.sd --label B1 --address "$FLOCKINATOR_NODE_ADDRESS" --output /tmp/b1-inspection
# Explicit entire-card MBR/FAT32 reset plus 16 MiB write/read comparison:
uv run --project tools/node-commissioner python -m node_commissioner.sd --label B1 --address "$FLOCKINATOR_NODE_ADDRESS" --format quick --erase --output /tmp/b1-quick
# The same operation through the identified handheld, without a node IP:
uv run --project tools/node-commissioner python -m node_commissioner.sd --label D1 --console-port "$FLOCKINATOR_LILYGO_PORT" --format quick --erase --output /tmp/d1-quick
```

Use a new evidence directory each time. `--format full --erase` recreates the filesystem and writes all available data clusters before reading/validating every byte. This is a destructive new job, **not** a status command. Test files are capped at 1 GiB. Quick success does not verify full capacity or remaining flash endurance. Measured throughput includes the configured SD interface and background-worker scheduling; it is not a card speed-class benchmark.

The job continues on the node after the host's `--wait` observation period (default 180 seconds). For status, use `--status` with the same node/transport and a new evidence directory. This only sends a read request and does not replace the current test or permit. Do not prepare another job merely to poll. OTA is unavailable on that node while SD maintenance is active. Power loss/restart interrupts the test and is recorded; no automatic destructive retry occurs. A full pass can take many hours, depending on card capacity and measured throughput. Keep the panels powered until completion.

The worker rechecks card identity before formatting and remounting, records destructive intent/results in internal NVS, and reports failures separately from no-response/unknown presence. Filesystem reset is not forensic secure erasure. Replacement cards require a new identified run and retain separate results.


Console 0.2.13 exposes `image_status` for bulk-upload recovery. If a chunk reply is lost, the host checks the same console boot, upload name, size, SHA-256 and stored offset. It retries a chunk only when that ordered readback proves the chunk was not stored. A changed session or unexpected offset stops the operation. Final whole-file and ESP-image checksums remain mandatory before publication/deployment. The pinned Arduino HWCDC transport can still delay/drop replies; recovery is not a claim that the underlying USB issue is eliminated.

### Verified Wi-Fi reinstall

The `update` command verifies a greater boot counter, alternate OTA slot, expected embedded digest, valid OTA state and retained receiver support before reporting success. This applies when reinstalling the identical binary too: a matching hash from the pre-update boot is insufficient. A timeout leaves completion unverified; inspect the target before retrying. An update reboots the node automatically. Standalone remote reboot is not exposed by the current Wi-Fi/ESP-NOW command interfaces.
