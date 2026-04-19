import type { Env } from "./_types";

export const onRequestGet: PagesFunction<Env> = async ({ env }) => {
  const raw = await env.KV.get("preferences");
  if (!raw) return Response.json({ history: [] });
  return new Response(raw, {
    headers: { "Content-Type": "application/json" },
  });
};
