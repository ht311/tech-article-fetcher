"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

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
  articles: Record<string, { title: string; source: string; url: string; category_id: string | null }[]>;
}

const CATEGORY_LABELS: Record<string, string> = {
  backend: "バックエンド",
  frontend: "フロントエンド",
  aws: "AWS",
  management: "マネジメント",
  others: "その他",
};

export default function HomePage() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [today, setToday] = useState<{ date: string; articles: ArticlesData["articles"][string] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const todayStr = new Date().toISOString().slice(0, 10);
    Promise.all([
      fetch("/api/stats").then((r) => r.json() as Promise<StatsData>),
      fetch(`/api/articles?from=${todayStr}&to=${todayStr}`).then((r) => r.json() as Promise<ArticlesData>),
    ]).then(([s, a]) => {
      setStats(s);
      setToday({ date: todayStr, articles: a.articles[todayStr] ?? [] });
      setLoading(false);
    });
  }, []);

  if (loading) return <p className="text-gray-500 text-sm">読み込み中...</p>;

  const topGood = Object.entries(stats?.goodBySource ?? {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">ダッシュボード</h1>

      {/* サマリーカード */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
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
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-2xl font-bold mt-1">{value}</p>
          </div>
        ))}
      </div>

      {/* 今日の配信 */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">今日の配信 ({today?.date})</h2>
          <Link href="/articles/" className="text-sm text-blue-600 hover:underline">
            過去記事を見る →
          </Link>
        </div>
        {today?.articles.length === 0 ? (
          <p className="text-sm text-gray-400">本日の配信はまだありません</p>
        ) : (
          <div className="space-y-2">
            {today?.articles.map((a, i) => (
              <a
                key={i}
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block bg-white border border-gray-200 rounded-lg px-4 py-3 hover:border-blue-300 transition-colors"
              >
                <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                  <span>{CATEGORY_LABELS[a.category_id ?? "others"] ?? a.category_id}</span>
                  <span>·</span>
                  <span>{a.source}</span>
                </div>
                <p className="text-sm font-medium line-clamp-2">{a.title}</p>
              </a>
            ))}
          </div>
        )}
      </section>

      {/* 高評価ソース */}
      {topGood.length > 0 && (
        <section>
          <h2 className="font-semibold mb-3">高評価ソース Top 3</h2>
          <div className="flex gap-3">
            {topGood.map(([source, count]) => (
              <div key={source} className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 flex-1">
                <p className="text-sm font-medium">{source}</p>
                <p className="text-lg font-bold text-green-600">👍 {count}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
