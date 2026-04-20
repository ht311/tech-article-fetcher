import type { Env, UserSettings, SourceDef, CategoryDef } from "./_types";
import { VALID_SOURCE_TYPES } from "./_types";
import { KV_SETTINGS } from "./_kv_keys";

const EMPTY_SETTINGS: UserSettings = {
  max_per_category: 5,
  exclude_keywords: [],
  include_keywords: [],
};

export type ValidationError = string;

export function validateSettings(body: Partial<UserSettings>): ValidationError | null {
  if (body.max_per_category !== undefined) {
    if (typeof body.max_per_category !== "number" || body.max_per_category < 1 || body.max_per_category > 5) {
      return "max_per_category must be 1-5";
    }
  }

  if (body.article_fetch_hours !== undefined) {
    if (typeof body.article_fetch_hours !== "number" || body.article_fetch_hours < 1 || body.article_fetch_hours > 168) {
      return "article_fetch_hours must be 1-168";
    }
  }

  if (body.gemini_max_input_per_category !== undefined) {
    if (
      typeof body.gemini_max_input_per_category !== "number" ||
      body.gemini_max_input_per_category < 5 ||
      body.gemini_max_input_per_category > 50
    ) {
      return "gemini_max_input_per_category must be 5-50";
    }
  }

  if (body.sources !== undefined) {
    const names = new Set<string>();
    for (const src of body.sources as SourceDef[]) {
      if (names.has(src.name)) return `Duplicate source name: ${src.name}`;
      names.add(src.name);
      if (!VALID_SOURCE_TYPES.includes(src.type)) {
        return `Invalid source type: ${src.type}`;
      }
      if (src.type === "rss" && !src.url) {
        return `Source "${src.name}" of type rss requires a url`;
      }
    }
  }

  if (body.category_defs !== undefined) {
    const ids = new Set<string>();
    for (const cat of body.category_defs as CategoryDef[]) {
      if (ids.has(cat.id)) return `Duplicate category id: ${cat.id}`;
      ids.add(cat.id);
    }
  }

  return null;
}

export const onRequestGet: PagesFunction<Env> = async ({ env }) => {
  const raw = await env.KV.get(KV_SETTINGS);
  if (!raw) return Response.json(EMPTY_SETTINGS);
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

  const error = validateSettings(body);
  if (error) return new Response(error, { status: 400 });

  const current = await env.KV.get(KV_SETTINGS);
  const existing: UserSettings = current ? JSON.parse(current) : { ...EMPTY_SETTINGS };
  const merged: UserSettings = { ...existing, ...body };

  await env.KV.put(KV_SETTINGS, JSON.stringify(merged));
  return Response.json(merged);
};
