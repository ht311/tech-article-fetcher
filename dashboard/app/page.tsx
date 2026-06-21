"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useCategories } from "./lib/useCategories";
import { groupByCategory } from "./lib/groupByCategory";
import { CategorySection } from "./components/CategorySection";
import { getRatings, setRating } from "./lib/ratings";
import type { Article } from "./lib/types";

interface StatsData {
  totalGood: number;
  totalBad: number;
  goodBySource: Record<string, number>;
  badBySource: Record<string, number>;
  weeklyTrend: { date: string; good: number; bad: number }[];
  categoryCount: Record<string, number>;
}

interface ArticlesData {
  dates: string[];
  articles: Record<string, Article[]>;
}

export default function HomePage() {
  const categories = useCategories();
  const [stats, setStats] = useState<StatsData | null>(null);
  const [today, setToday] = useState<{ date: string; articles: Article[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [ratings, setRatings] = useState<Record<string, "good" | "bad">>({});

  useEffect(() => {
    setRatings(getRatings());
    const todayStr = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo" }).format(new Date());
    Promise.all([
      fetch("/api/stats").then((r) => r.json() as Promise<StatsData>),
      fetch(`/api/articles?from=${todayStr}&to=${todayStr}`).then((r) => r.json() as Promise<ArticlesData>),
    ]).then(([s, a]) => {
      setStats(s);
      setToday({ date: todayStr, articles: a.articles[todayStr] ?? [] });
      setLoading(false);
    });
  }, []);

  function handleRate(article: Article, action: "good" | "bad") {
    const prev = ratings[article.url];
    if (prev === action) {
      setRating(article.url, null);
      setRatings((r) => { const next = { ...r }; delete next[article.url]; return next; });
      return;
    }
    setRating(article.url, action);
    setRatings((r) => ({ ...r, [article.url]: action }));
    fetch("/api/preferences", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, title: article.title, source: article.source, url: article.url }),
    }).catch((err) => {
      console.warn("Failed to record rating", err);
      setRating(article.url, prev ?? null);
      setRatings((r) => {
        const next = { ...r };
        if (prev) next[article.url] = prev; else delete next[article.url];
        return next;
      });
    });
  }

  if (loading) return <p className="text-gray-500 text-sm">読み込み中...</p>;

  const topGood = Object.entries(stats?.goodBySource ?? {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  const categoryGroups = groupByCategory(today?.articles ?? [], categories);

  return (
    <div className="space-y-6">
      <h1 className="text-xl sm:text-2xl font-bold">ダッシュボード</h1>

      {/* サマリーカード */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "👍 Good 合計", value: stats?.totalGood ?? 0 },
          { label: "👎 Bad 合計", value: stats?.totalBad ?? 0 },
          { label: "今日の配信", value: today?.articles.length ?? 0 },
          {
            label: "エンゲージメント率",
            value:
              (stats?.totalGood ?? 0) + (stats?.totalBad ?? 0) > 0
                ? `${Math.round(((stats?.totalGood ?? 0) / ((stats?.totalGood ?? 0) + (stats?.totalBad ?? 0))) * 100)}%`
                : "—",
          },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-3 sm:p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-xl sm:text-2xl font-bold mt-1">{value}</p>
          </div>
        ))}
      </div>

      {/* 今日の配信（カテゴリ別） */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-sm sm:text-base">
            今日の配信{today?.date ? ` (${today.date})` : ""}
          </h2>
          <Link href="/articles/" className="text-xs sm:text-sm text-blue-600 hover:underline shrink-0">
            過去記事を見る →
          </Link>
        </div>

        {(today?.articles.length ?? 0) === 0 ? (
          <p className="text-sm text-gray-400">本日の配信はまだありません</p>
        ) : (
          <div className="space-y-5">
            {categoryGroups.map((group) => (
              <CategorySection
                key={group.id}
                id={group.id}
                name={group.name}
                articles={group.articles}
                ratings={ratings}
                onRate={handleRate}
              />
            ))}
          </div>
        )}
      </section>

      {/* 高評価ソース */}
      {topGood.length > 0 && (
        <section>
          <h2 className="font-semibold mb-3 text-sm sm:text-base">高評価ソース Top 3</h2>
          <div className="flex gap-2 sm:gap-3 flex-wrap">
            {topGood.map(([source, count]) => (
              <div
                key={source}
                className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 sm:px-4 sm:py-3 flex-1 min-w-[6rem]"
              >
                <p className="text-xs sm:text-sm font-medium truncate">{source}</p>
                <p className="text-base sm:text-lg font-bold text-green-600">👍 {count}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
