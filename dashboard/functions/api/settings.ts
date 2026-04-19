import type { Env, UserSettings, DEFAULT_SETTINGS } from "./_types";
import { DEFAULT_SETTINGS as defaults } from "./_types";

export const onRequestGet: PagesFunction<Env> = async ({ env }) => {
  const raw = await env.KV.get("settings");
  if (!raw) return Response.json(defaults);
  return new Response(raw, {
    headers: { "Content-Type": "application/json" },
  });
};

export const onRequestPut: PagesFunction<Env> = async ({ request, env }) => {
  let body: Partial<UserSettings>;
  try {
    body = await request.json();
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  const current = await env.KV.get("settings");
  const existing: UserSettings = current ? JSON.parse(current) : { ...defaults };
  const merged: UserSettings = { ...existing, ...body };

  if (
    typeof merged.max_per_category !== "number" ||
    merged.max_per_category < 1 ||
    merged.max_per_category > 5
  ) {
    return new Response("max_per_category must be 1-5", { status: 400 });
  }

  await env.KV.put("settings", JSON.stringify(merged));
  return Response.json(merged);
};
