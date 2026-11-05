# Flockinator interactive simulation (Cloudflare Pages + Functions)

Public, anonymous, **simulation-only** surface. It never connects
to the physical fleet, a lab network, or any controller.

## What it serves

- `/` - headline, flagship benchmark explorer, and a 4x4 wall
  replay of one scored simulation (composite-defence seed 200),
  labelled as a visualisation of a host-scored run.
- `GET /api/benchmark` - pooled canonical flagship result.
- `GET /api/benchmark?seed=0..15` - one canonical seed.
  Errors are structured: 400 malformed seed, 422 outside the
  canonical set (run `tools/reproduce` locally for other seeds).
- `GET /api/health` - `{ ok, execution: "simulation_only", real_nodes: false }`.

All benchmark data is precomputed by the Python scientific code
(`tools/reproduce/run.py`) and served unchanged; the Worker never
reimplements the simulation. Wall-replay data is a generated
fixture from `kulira_core.composite`, with its provenance in the
JSON.

## Deploy (owner account)

```sh
cd cloudflare
npx wrangler login          # owner Cloudflare account, once
npx wrangler pages deploy site --project-name flockinator-sim
```

Pages Functions in `functions/` deploy with the project when the
project root is this directory (`wrangler.toml` sets the output
dir). Verify after deploy: `/api/health`, `/api/benchmark`,
`/api/benchmark?seed=99` (expect 422), and the wall replay.

## Local preview

```sh
python3 -m http.server --directory cloudflare/site 8811
# open http://127.0.0.1:8811/  (API falls back to static JSON)
npx wrangler pages dev site   # full Functions behaviour, if desired
```
