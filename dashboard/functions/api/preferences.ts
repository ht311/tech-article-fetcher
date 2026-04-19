import type { Env } from "./_types";
import { KV_PREFERENCES } from "./_kv_keys";

export const onRequestGet: PagesFunction<Env> = async ({ env }) => {
  const raw = await env.KV.get(KV_PREFERENCES);
  if (!raw) return Response.json({ history: [] });
  return new Response(raw, {
    headers: { "Content-Type": "application/json" },
  });
};
