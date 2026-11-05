export async function onRequestGet() {
  return new Response(JSON.stringify({ ok: true, service: "flockinator-sim", execution: "simulation_only", real_nodes: false }),
    { headers: { "content-type": "application/json" } });
}
