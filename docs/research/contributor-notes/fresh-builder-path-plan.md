<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Fresh-fleet path plan — for cloners with no vault access

**Goal:** `clone -> init -> 17 synthetic IDs` (16x panel + 1x controller) with zero owner secrets.

### 1. Local generation
- Add `docs/fleet-setup.md`: fresh-fleet is the default for cloners.
- Generate locally, tool-agnostic: Ed25519 keypair per node + fleet CA cert, via stdlib crypto. No vault binary, no network, no copy-from-owner.

### 2. File layout + permissions
```
.fleet/
  fleet.json         # fleet-id, created-at, synthetic=true  (0644)
  nodes.csv          # id, role, pubkey  — no secrets (0644)
  private/           # 0700
    controller.key   # 0600
    panel-00.key ... panel-15.key  # 0600 each
```
- Enforce on write: `mkdir -p private (0700)`, keys `0600`, fail if umask looser.
- Add `.fleet/private/` to `.gitignore`.

### 3. CLI to add
- `fleet-keys init --nodes 17 --out .fleet` — creates fleet-id, 1x `controller` + 16x `panel-XX`, idempotent, refuses to overwrite without `--force`.
- `fleet-keys add-node --role panel --out .fleet` — appends `panel-16`, updates `nodes.csv`.
- `fleet-keys list --count --out .fleet` — prints count only, e.g. `17`. No key material to stdout/logs. Add `--json` for `nodes.csv` validation.

### 4. Safety rules
- Never commit keys: pre-commit check + CI `git ls-files | grep .fleet/private` must be empty.
- Synthetic test fleet only: `fleet.json: {"synthetic": true}`, CLI prints `TEST FLEET - NOT FOR PRODUCTION` on `init`.
- Separate from owner fleet: different `fleet-id` prefix `test-`, docs forbid importing test keys to prod.

### 5. Acceptance tests — no vault present
Run in clean container with `vault` NOT on `PATH`:
```sh
! command -v vault
fleet-keys init --nodes 17 --out .fleet
test $(fleet-keys list --count) = "17"
stat -c %a .fleet/private/*.key | grep -qv 600 && exit 1
git status --porcelain | ! grep private/
fleet-keys add-node --role panel && test $(fleet-keys list --count) = "18"
```