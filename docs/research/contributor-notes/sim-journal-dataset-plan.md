<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

# Open Data Pack for Simulated Robot-Search Runs

## 1. Per-Run Folder Layout

```
dataset/
  README.md
  runs/
    run_2026-11-06_1400_M12/
      MANIFEST.json
      MISSION_SLATE.json
      CHECKSUMS.sha256
      controller/
        controller.log.jsonl
        controller.hashchain.jsonl
      panels/
        panel_01.log.jsonl ... panel_16.log.jsonl
        panels.hashchain.jsonl
      sync/
        tick_map.csv
        sync_report.json
      media/
        wall_downscaled_720p.mp4
        wall_timecodes.csv
        slate_frame.png
```

> One folder = one run. No cross-run files. Immutable after publish.

## 2. Log Files: 1 Controller + 16 Panels

**Controller:** `controller.log.jsonl` - mission ticks, commands, search events
```
{"tick":1042, "utc":"2026-11-06T14:00:12.100Z", "monotonic_ms":61200, "event":"TICK", "prev_hash":"..."}
```

**Panels 01-16:** `panel_XX.log.jsonl` - UI inputs, local observations, ack of controller ticks. Same schema, plus `panel_id`.

All logs: UTF-8 JSONL, one event per line, sorted by `tick`.

## 3. Hash-Chaining + Mission Checksum Slate

**Hash chain per log file:**
```
entry_hash = SHA256(prev_hash + canonical_json(entry_without_hashes))
```
Stored in `*.hashchain.jsonl`: `{seq, tick, entry_hash, prev_hash}`. Genesis `prev_hash = "0"*64`.

**Mission Slate `MISSION_SLATE.json` - ties media to logs:**
```json
{
  "mission_id": "M12",
  "start_tick": 0, "end_tick": 5400,
  "files": [
    {"path":"controller/controller.log.jsonl","sha256":"abc..."},
    {"path":"panels/panel_01.log.jsonl","sha256":"def..."},
    {"path":"media/wall_downscaled_720p.mp4","sha256":"789..."}
  ],
  "merkle_root": "root...",
  "chain_heads": {"controller":"h...","panels":"h..."}
}
```

Publish `CHECKSUMS.sha256` for all files.

## 4. Privacy Redaction Rules

Redact **before** hashing for public release. Keep raw private.

* **Remove:** device hostnames, serials, MACs, IP/MAC, WiFi SSIDs, user accounts, credentials/tokens/API keys
* **Replace with:** `panel_01-16`, `192.0.2.x -> REDACTED_NET`, `user -> ROLE_OPERATOR_N`
* **Method:** allowlist fields only (`tick, utc, monotonic_ms, event, payload_public`). Denylist regex scan for `[A-F0-9:]{17}`, `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`, `password|token|secret|key=`.
* Log redaction in `MANIFEST.json`: `redaction_tool v1.2 + ruleset hash`.

## 5. Tick / Timestamp Sync Evidence

`sync/tick_map.csv`:
```
tick,controller_utc,controller_mono_ms,panel_id,panel_mono_ms,offset_ms
1042,...,61200,03,...,61235,+35
```

`sync/sync_report.json`: NTP server, pre/post offsets, dropped ticks, max drift. Controller broadcasts tick @10Hz; panels log receipt. Evidence = can map any `tick <-> UTC`.

## 6. Pairing Logs with Downscaled Wall Video

* Source wall video downscaled to **720p, 5fps, H.264, no audio**.
* First 5s = burned slate frame: `mission_id, start_utc, start_tick, slate_sha`.
* Burned overlay entire video: `tick | UTC` bottom-right.
* `wall_timecodes.csv`: `frame_no, tick, utc, log_seq` for alignment check.

## 7. Third-Party Verify Checklist

```bash
# 1. File integrity
sha256sum -c CHECKSUMS.sha256

# 2. Slate matches files
jq -r '.files[] | "\(.sha256)  \(.path)"' MISSION_SLATE.json | sha256sum -c -

# 3. Verify hash chains
python3 verify_chain.py --run ./runs/run_2026-11-06_1400_M12/

# 4. Tick continuity + sync
python3 verify_sync.py --tick_map sync/tick_map.csv --report sync/sync_report.json

# 5. Log <-> video pairing
ffprobe -v error -show_streams media/wall_downscaled_720p.mp4
head -n 5 media/wall_timecodes.csv
# check first frame = slate_frame.png hash in MANIFEST.json

# 6. Privacy scan (should return nothing)
grep -R -E -i "([0-9A-F]{2}:){5}|password|BEGIN .*PRIVATE|192\.168\.|10\." controller/ panels/
```
