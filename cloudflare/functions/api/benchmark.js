// Pages Function: serves the canonical flagship benchmark data.
// Data is precomputed by the Python scientific code (tools/reproduce);
// this function never reimplements the simulation.
import data from "../../site/data/benchmark.json";

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { "content-type": "application/json", "cache-control": "public, max-age=300", "x-content-type-options": "nosniff" } });
}
function err(code, message, status) {
  return json({ error: { code, message } }, status);
}

export async function onRequestGet({ request }) {
  const url = new URL(request.url);
  const seedParam = url.searchParams.get("seed");
  if (seedParam === null) {
    return json({ pooled: data.pooled, seeds: data.seeds, definition: data.definition,
                  source: data.source, canonical_sha256: data.canonical_sha256,
                  execution: "precomputed_canonical_python" });
  }
  if (!/^-?\d+$/.test(seedParam)) return err("VALIDATION_ERROR", "seed must be an integer 0-15", 400);
  const seed = Number(seedParam);
  const row = data.per_seed.find((r) => r.seed === seed);
  if (!row) return err("SEED_OUT_OF_RANGE", "benchmark seeds are 0-15 (canonical set); other seeds: run tools/reproduce locally", 422);
  const rates = {};
  for (const k of ["clear", "scrambled", "private"]) {
    rates[k] = { recoveries: row[`${k}_recoveries`], tasks: row[`${k}_tasks`],
                 rate: row[`${k}_tasks`] ? row[`${k}_recoveries`] / row[`${k}_tasks`] : null };
  }
  return json({ seed, conditions: rates, definition: data.definition, canonical_sha256: data.canonical_sha256 });
}
