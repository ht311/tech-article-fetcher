import type { Env, ArticleHistoryEntry } from "./_types";
import { KV_PREFERENCES, KV_ARTICLE_INDEX, articleHistoryKey } from "./_kv_keys";

interface FeedbackEntry {
  action: "good" | "bad";
  source: string;
  timestamp: string;
}

export const onRequestGet: PagesFunction<Env> = async ({ env }) => {
  const [prefsRaw, indexRaw] = await Promise.all([
    env.KV.get(KV_PREFERENCES),
    env.KV.get(KV_ARTICLE_INDEX),
  ]);

  const prefs = prefsRaw ? JSON.parse(prefsRaw) : { history: [] };
  const history: FeedbackEntry[] = prefs.history ?? [];

  // Good / Bad counts by source
  const goodBySource: Record<string, number> = {};
  const badBySource: Record<string, number> = {};
  for (const entry of history) {
    if (entry.action === "good") {
      goodBySource[entry.source] = (goodBySource[entry.source] ?? 0) + 1;
    } else {
      badBySource[entry.source] = (badBySource[entry.source] ?? 0) + 1;
    }
  }

  // Weekly trend: last 7 days good/bad count
  const weeklyTrend: { date: string; good: number; bad: number }[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    const dayEntries = history.filter((e) => e.timestamp.slice(0, 10) === dateStr);
    weeklyTrend.push({
      date: dateStr,
      good: dayEntries.filter((e) => e.action === "good").length,
      bad: dayEntries.filter((e) => e.action === "bad").length,
    });
  }

  // Category distribution from recent articles
  const categoryCount: Record<string, number> = {};
  if (indexRaw) {
    const index = JSON.parse(indexRaw) as { dates: string[] };
    const recentDates = index.dates.slice(0, 7);
    const articleBatches = await Promise.all(
      recentDates.map((d) => env.KV.get(articleHistoryKey(d)))
    );
    for (const raw of articleBatches) {
      if (!raw) continue;
      const articles: ArticleHistoryEntry[] = JSON.parse(raw);
      for (const a of articles) {
        const cat = a.category_id ?? "others";
        categoryCount[cat] = (categoryCount[cat] ?? 0) + 1;
      }
    }
  }

  return Response.json({
    totalGood: history.filter((e) => e.action === "good").length,
    totalBad: history.filter((e) => e.action === "bad").length,
    goodBySource,
    badBySource,
    weeklyTrend,
    categoryCount,
  });
};
