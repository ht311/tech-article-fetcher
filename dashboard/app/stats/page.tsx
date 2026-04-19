"use client";

import { useEffect, useState } from "react";
import { useCategories, categoryLabel } from "../lib/useCategories";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell,
} from "recharts";

interface StatsData {
  totalGood: number;
  totalBad: number;
  goodBySource: Record<string, number>;
  badBySource: Record<string, number>;
  weeklyTrend: { date: string; good: number; bad: number }[];
  categoryCount: Record<string, number>;
}

const PIE_COLORS = ["#3b82f6", "#8b5cf6", "#f97316", "#22c55e", "#94a3b8"];

export default function StatsPage() {
  const categories = useCategories();
  const [stats, setStats] = useState<StatsData | null>(null);

  useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json() as Promise<StatsData>)
      .then(setStats);
  }, []);

  if (!stats) return <p className="text-sm text-gray-400">読み込み中...</p>;

  const sourceData = [
    ...new Set([...Object.keys(stats.goodBySource), ...Object.keys(stats.badBySource)]),
  ]
    .map((src) => ({
      source: src,
      good: stats.goodBySource[src] ?? 0,
      bad: stats.badBySource[src] ?? 0,
    }))
    .sort((a, b) => b.good + b.bad - (a.good + a.bad))
    .slice(0, 10);

  const categoryData = Object.entries(stats.categoryCount).map(([id, count]) => ({
    name: categoryLabel(categories, id),
    value: count,
  }));

  const weeklyData = stats.weeklyTrend.map((d) => ({
    ...d,
    date: d.date.slice(5),
  }));

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">統計</h1>

      {/* サマリー */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <p className="text-xs text-gray-500">合計 Good</p>
          <p className="text-3xl font-bold text-green-600">👍 {stats.totalGood}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <p className="text-xs text-gray-500">合計 Bad</p>
          <p className="text-3xl font-bold text-red-500">👎 {stats.totalBad}</p>
        </div>
      </div>

      {/* 週次トレンド */}
      <section>
        <h2 className="font-semibold mb-3">週次フィードバック推移</h2>
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={weeklyData}>
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="good" name="Good" fill="#22c55e" />
              <Bar dataKey="bad" name="Bad" fill="#f87171" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {/* ソース別評価 */}
        <section>
          <h2 className="font-semibold mb-3">ソース別フィードバック</h2>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={sourceData} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="source"
                  width={80}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip />
                <Bar dataKey="good" name="Good" fill="#22c55e" stackId="a" />
                <Bar dataKey="bad" name="Bad" fill="#f87171" stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* カテゴリ分布 */}
        <section>
          <h2 className="font-semibold mb-3">カテゴリ配信分布 (直近7日)</h2>
          <div className="bg-white border border-gray-200 rounded-xl p-4 flex items-center justify-center">
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={categoryData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, percent }) =>
                    `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                  }
                  labelLine={false}
                >
                  {categoryData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
    </div>
  );
}
