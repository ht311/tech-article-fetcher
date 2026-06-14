"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useCategories } from "../lib/useCategories";
import { groupByCategory } from "../lib/groupByCategory";
import { CategorySection } from "../components/CategorySection";
import type { Article } from "../lib/types";

interface ArticlesData {
  dates: string[];
  articles: Record<string, Article[]>;
}

function toISODate(d: Date) {
  return d.toISOString().slice(0, 10);
}

export default function ArticlesPage() {
  const categories = useCategories();
  const today = toISODate(new Date());
  const thirtyDaysAgo = toISODate(new Date(Date.now() - 30 * 86400_000));

  const [from, setFrom] = useState(thirtyDaysAgo);
  const [to, setTo] = useState(today);
  const [data, setData] = useState<ArticlesData | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  // 横スクロールチップで選択中の日付ボタンを自動スクロール
  const chipListRef = useRef<HTMLDivElement>(null);

  const fetchArticles = useCallback(() => {
    setLoading(true);
    fetch(`/api/articles?from=${from}&to=${to}`)
      .then((r) => r.json() as Promise<ArticlesData>)
      .then((d) => {
        setData(d);
        setSelectedDate(d.dates[0] ?? null);
        setLoading(false);
      });
  }, [from, to]);

  useEffect(() => {
    fetchArticles();
  }, [fetchArticles]);

  // 選択中のチップを表示領域内にスクロール
  useEffect(() => {
    if (!selectedDate || !chipListRef.current) return;
    const btn = chipListRef.current.querySelector(`[data-date="${selectedDate}"]`);
    btn?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [selectedDate]);

  const currentArticles = selectedDate ? (data?.articles[selectedDate] ?? []) : [];
  const categoryGroups = groupByCategory(currentArticles, categories);

  return (
    <div className="space-y-4 sm:space-y-6">
      <h1 className="text-xl sm:text-2xl font-bold">過去記事</h1>

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
          type="button"
          onClick={fetchArticles}
          className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
        >
          検索
        </button>
      </div>

      {loading && <p className="text-sm text-gray-400">読み込み中...</p>}

      {data &&
        (data.dates.length === 0 ? (
          <p className="text-sm text-gray-400">記録なし</p>
        ) : (
          <div className="flex flex-col gap-4 lg:flex-row lg:gap-6">
              {/* 日付選択 — スマホ: 上部横スクロールチップ / デスクトップ: 左サイドバー */}

              {/* スマホ用横スクロールチップ (lg 未満で表示) */}
              <div
                ref={chipListRef}
                className="flex gap-2 overflow-x-auto pb-1 scrollbar-none lg:hidden"
              >
                {data.dates.map((d) => (
                  <button
                    type="button"
                    key={d}
                    data-date={d}
                    onClick={() => setSelectedDate(d)}
                    className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                      selectedDate === d
                        ? "bg-blue-600 text-white"
                        : "bg-white border border-gray-300 text-gray-600 hover:border-blue-400"
                    }`}
                  >
                    {d.slice(5)}{/* MM-DD */}
                    <span className="ml-1 opacity-70">
                      ({(data.articles[d] ?? []).length})
                    </span>
                  </button>
                ))}
              </div>

              {/* デスクトップ用左サイドバー (lg 以上で表示) */}
              <div className="hidden lg:block w-36 shrink-0 space-y-1">
                {data.dates.map((d) => (
                  <button
                    type="button"
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

              {/* 記事リスト（カテゴリ別） */}
              <div className="flex-1 min-w-0 space-y-5">
                {currentArticles.length === 0 ? (
                  <p className="text-sm text-gray-400">記事なし</p>
                ) : (
                  categoryGroups.map((group) => (
                    <CategorySection
                      key={group.id}
                      id={group.id}
                      name={group.name}
                      articles={group.articles}
                    />
                  ))
                )}
              </div>
            </div>
        ))}
    </div>
  );
}
