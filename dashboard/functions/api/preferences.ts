import type { Env } from "./_types";
import { KV_PREFERENCES } from "./_kv_keys";

// Must match src/core/constants.py (MAX_HISTORY) and infrastructure/cloudflare/index.js (MAX_HISTORY).
const MAX_HISTORY = 100;

export type FeedbackError = string;

export function validateFeedback(body: unknown): FeedbackError | null {
  if (typeof body !== "object" || body === null) return "Request body must be a JSON object";
  const b = body as Record<string, unknown>;
  if (b.action !== "good" && b.action !== "bad") return 'action must be "good" or "bad"';
  if (typeof b.url !== "string" || !b.url) return "url must be a non-empty string";
  if (typeof b.title !== "string" || !b.title) return "title must be a non-empty string";
  if (typeof b.source !== "string" || !b.source) return "source must be a non-empty string";
  return null;
}

export const onRequestGet: PagesFunction<Env> = async ({ env }) => {
  const raw = await env.KV.get(KV_PREFERENCES);
  if (!raw) return Response.json({ history: [] });
  return new Response(raw, {
    headers: { "Content-Type": "application/json" },
  });
};

export const onRequestPost: PagesFunction<Env> = async ({ request, env }) => {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  const error = validateFeedback(body);
  if (error) return new Response(error, { status: 400 });

  const { action, title, source, url } = body as { action: "good" | "bad"; title: string; source: string; url: string };

  const raw = await env.KV.get(KV_PREFERENCES);
  const prefs = raw ? JSON.parse(raw) : { history: [] };
  if (!Array.isArray(prefs.history)) prefs.history = [];

  prefs.history.push({ action, title, source, url, timestamp: new Date().toISOString() });
  if (prefs.history.length > MAX_HISTORY) {
    prefs.history = prefs.history.slice(-MAX_HISTORY);
  }

  await env.KV.put(KV_PREFERENCES, JSON.stringify(prefs));
  return Response.json({ ok: true });
};
