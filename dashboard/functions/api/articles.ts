import type { Env, ArticleHistoryEntry } from "./_types";

export const onRequestGet: PagesFunction<Env> = async ({ request, env }) => {
  const url = new URL(request.url);
  const from = url.searchParams.get("from");
  const to = url.searchParams.get("to");

  const indexRaw = await env.KV.get("article_index");
  if (!indexRaw) {
    return Response.json({ dates: [], articles: {} });
  }

  const index = JSON.parse(indexRaw) as { dates: string[] };
  let dates = index.dates;

  if (from) dates = dates.filter((d) => d >= from);
  if (to) dates = dates.filter((d) => d <= to);

  const entries = await Promise.all(
    dates.map(async (date) => {
      const raw = await env.KV.get(`articles:${date}`);
      const articles: ArticleHistoryEntry[] = raw ? JSON.parse(raw) : [];
      return [date, articles] as [string, ArticleHistoryEntry[]];
    })
  );

  return Response.json({
    dates,
    articles: Object.fromEntries(entries),
  });
};
