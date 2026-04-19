import type { Env } from "./_types";
import { KV_DEFAULT_SETTINGS } from "./_kv_keys";

export const onRequestGet: PagesFunction<Env> = async ({ env }) => {
  const raw = await env.KV.get(KV_DEFAULT_SETTINGS);
  if (!raw) {
    return new Response(
      "デフォルトが未 seed です。python -m src.seed を実行してください。",
      { status: 404 },
    );
  }
  return new Response(raw, { headers: { "Content-Type": "application/json" } });
};
