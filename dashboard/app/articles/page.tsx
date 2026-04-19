"use client";

import { useEffect, useState } from "react";

interface Article {
  title: string;
  source: string;
  url: string;
  category_id: string | null;
  reason: string;
  thumbnail_url: string | null;
  published_at: string | null;
}

interface ArticlesData {
  dates: string[];
  articles: Record<string, Article[]>;
}

const CATEGORY_LABELS: Record<string, string> = {
  backend: "バックエンド",
  frontend: "フロントエンド",
  aws: "AWS",
  management: "マネジメント",
  others: "その他",
};

const CATEGORY_COLORS: Record<string, string> = {
  backend: "bg-blue-100 text-blue-700",
  frontend: "bg-purple-100 text-purple-700",
  aws: "bg-orange-100 text-orange-700",
  management: "bg-green-100 text-green-700",
  others: "bg-gray-100 text-gray-600",
};

function toISODate(d: Date) {
  return d.toISOString().slice(0, 10);
}

export default function ArticlesPage() {
  const today = toISODate(new Date());
  const thirtyDaysAgo = toISODate(new Date(Date.now() - 30 * 86400_000));

  const [from, setFrom] = useState(thirtyDaysAgo);
  const [to, setTo] = useState(today);
  const [data, setData] = useState<ArticlesData | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const fetchArticles = () => {
    setLoading(true);
    fetch(`/api/articles?from=${from}&to=${to}`)
      .then((r) => r.json() as Promise<ArticlesData>)
      .then((d) => {
        setData(d);
        setSelectedDate(d.dates[0] ?? null);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchArticles();
  }, []);

  const currentArticles = selectedDate ? (data?.articles[selectedDate] ?? []) : [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">過去記事</h1>

      {/* 期間フィルタ */}
      <div className="flex items-end gap-3 flex-wrap">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-gray-500">From</span>
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-gray-500">To</span>
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-sm"
          />
        </label>
        <button
          onClick={fetchArticles}
          className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
        >
          検索
        </button>
      </div>

      {loading && <p className="text-sm text-gray-400">読み込み中...</p>}

      {data && (
        <div className="flex gap-6">
          {/* 日付リスト */}
          <div className="w-36 shrink-0 space-y-1">
            {data.dates.length === 0 && (
              <p className="text-sm text-gray-400">記録なし</p>
            )}
            {data.dates.map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDate(d)}
                className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                  selectedDate === d
                    ? "bg-blue-600 text-white"
                    : "hover:bg-gray-100 text-gray-700"
                }`}
              >
                {d}
                <span className="ml-1 text-xs opacity-70">
                  ({(data.articles[d] ?? []).length})
                </span>
              </button>
            ))}
          </div>

          {/* 記事リスト */}
          <div className="flex-1 space-y-3">
            {currentArticles.length === 0 ? (
              <p className="text-sm text-gray-400">記事なし</p>
            ) : (
              currentArticles.map((a, i) => (
                <a
                  key={i}
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex gap-3 bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
                >
                  {a.thumbnail_url && (
                    <img
                      src={a.thumbnail_url}
                      alt=""
                      className="w-20 h-14 object-cover rounded shrink-0"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          CATEGORY_COLORS[a.category_id ?? "others"]
                        }`}
                      >
                        {CATEGORY_LABELS[a.category_id ?? "others"]}
                      </span>
                      <span className="text-xs text-gray-400">{a.source}</span>
                    </div>
                    <p className="text-sm font-medium line-clamp-2">{a.title}</p>
                    {a.reason && (
                      <p className="text-xs text-gray-400 mt-1">{a.reason}</p>
                    )}
                  </div>
                </a>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
