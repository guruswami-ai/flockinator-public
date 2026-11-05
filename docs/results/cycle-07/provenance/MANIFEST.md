# Cycle-07 provenance manifest

Copied 2026-11-05 (UTC) from `/tmp/cycle07-twins/` into this directory.

| File | Source | md5 |
|---|---|---|
| `planner.py` | `/tmp/cycle07-twins/planner.py` (trust twin: auth + T0-T4/T1R) | `cc056f821b81c8eab446fb1dc60af4fc` |
| `identity_check.py` | `/tmp/cycle07-twins/identity_check.py` | (helper, see twin run logs) |
| `treatment_sanity.py` | `/tmp/cycle07-twins/treatment_sanity.py` | (helper, see twin run logs) |
| `parity-out.txt` | `/tmp/cycle07-twins/parity-out.txt` (100-line parity binary output) | — |
| `twin.patch` | `diff -u tools/mission-host/planner.py /tmp/cycle07-twins/planner.py` | — |

`parity-err.txt` was 0 bytes (empty stderr) and was not copied.

Production twins re-verified unchanged at copy time:

| File | md5 |
|---|---|
| `tools/mission-host/planner.py` | `fd25c1277e1a510b70171930ad25eb99` |
| `firmware/korvo-monitor/main/board_model.cpp` | `5447183b9672d29a4e01dc7521b599f1` |

Gate configs in this run point parity evidence at
`docs/operations/fleet-reports/2026-11-05-cycle-07/provenance/parity-out.txt`
(repo path), never `/tmp`.

---

Publication corrigendum (public tree): the parity-evidence path named
above (`docs/operations/fleet-reports/2026-11-05-cycle-07/...`) is the
private-tree location at run time. In this published copy the gate
configs and verdict payloads cite the repo-relative published path:
`docs/results/cycle-07/provenance/parity-out.txt`. The file content is
unchanged. Verdict annotations (vacuity, policy-independence) live in
`../verdicts/annotations.json`; frozen verdict payloads were not edited
beyond the disclosed absolute->repo-relative path scrub.
