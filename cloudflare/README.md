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

## Live

Deployed 2026-11-06 (owner account): https://flockinator-sim.pages.dev

Verified live after deploy: `/api/health` (simulation_only,
`real_nodes: false`), `/api/benchmark` (canonical sha256
`406549c3...`), `?seed=5` 200, `?seed=99` 422, `?seed=abc` 400,
`/` and `/data/replay.json` 200.

## Deploy (owner account)

```sh
cd cloudflare
npx wrangler login          # owner Cloudflare account, once
npx wrangler pages project create flockinator-sim --production-branch main  # first time only
npx wrangler pages deploy --branch main
```

Run deploy from this directory so `wrangler.toml` sets the output
dir (`site/`) and Pages Functions in `functions/` deploy with the
project. `--branch main` targets production; without it, wrangler
uses the current git branch name and creates a preview deployment.
Verify after deploy: `/api/health`, `/api/benchmark`,
`/api/benchmark?seed=99` (expect 422), and the wall replay.
Rollback: redeploy the previous commit, or delete the deployment
in the Cloudflare dashboard (Pages -> flockinator-sim ->
Deployments). No data or state is stored, so rollback is a pure
static redeploy.

## Local preview

```sh
python3 -m http.server --directory cloudflare/site 8811
# open http://127.0.0.1:8811/  (API falls back to static JSON)
npx wrangler pages dev site   # full Functions behaviour, if desired
```
