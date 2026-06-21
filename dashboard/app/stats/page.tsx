"use client";

import { useEffect, useState } from "react";
import { catColor } from "../lib/pressColors";
import { categoryLabel, useCategories } from "../lib/useCategories";

const SERIF = "var(--font-serif)";
const SANS  = "var(--font-sans)";
const MONO  = "var(--font-mono)";
const C = {
  ink:     "var(--color-press-ink)",
  mut:     "var(--color-press-muted)",
  sub:     "var(--color-press-subtle)",
  line:    "var(--color-press-border)",
  surface: "var(--color-press-surface)",
  accent:  "var(--color-press-accent)",
  good:    "var(--color-press-good)",
};

interface StatsData {
  totalGood: number;
  totalBad: number;
  goodBySource: Record<string, number>;
  badBySource: Record<string, number>;
  weeklyTrend: { date: string; good: number; bad: number }[];
  categoryCount: Record<string, number>;
}

function toWeekLabel() {
  const today = new Date();
  const weekStart = new Date(today);
  weekStart.setDate(today.getDate() - today.getDay());
  const fmt = (d: Date) => `${d.getMonth() + 1}月${d.getDate()}日`;
  return `今週 — ${fmt(weekStart)}〜${fmt(today)}`;
}

export default function StatsPage() {
  const categories = useCategories();
  const [stats, setStats] = useState<StatsData | null>(null);

  useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json() as Promise<StatsData>)
      .then(setStats);
  }, []);

  if (!stats) {
    return (
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, background: "var(--color-press-bg)" }}>
        <div style={{ flexShrink: 0, padding: "12px 22px 12px", borderBottom: `2px solid ${C.ink}` }}>
          <h2 style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 21, fontWeight: 600, color: C.ink, letterSpacing: "-0.01em" }}>統計</h2>
        </div>
        <div style={{ padding: "32px 22px", textAlign: "center", fontFamily: SANS, fontSize: 13, color: C.sub }}>読み込み中...</div>
      </div>
    );
  }

  const totalFeedback = stats.totalGood + stats.totalBad;
  const adoptionRate = totalFeedback > 0 ? Math.round((stats.totalGood / totalFeedback) * 100) : 0;
  const totalDelivered = Object.values(stats.categoryCount).reduce((a, b) => a + b, 0);

  // Category bars (sorted by count, excluding "others")
  const catTotal = Object.entries(stats.categoryCount)
    .filter(([id]) => id !== "others")
    .reduce((a, [, v]) => a + v, 0) || 1;
  const catBars = Object.entries(stats.categoryCount)
    .filter(([id]) => id !== "others")
    .sort((a, b) => b[1] - a[1])
    .map(([id, count]) => ({ id, pct: Math.round((count / catTotal) * 100) }));

  // Top category for trend note
  const topCat = catBars[0];
  const topCatLabel = topCat ? categoryLabel(categories, topCat.id) : null;

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, background: "var(--color-press-bg)" }}>
      {/* Header */}
      <div style={{ flexShrink: 0, padding: "12px 22px 12px", borderBottom: `2px solid ${C.ink}` }}>
        <h2 style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 21, fontWeight: 600, color: C.ink, letterSpacing: "-0.01em" }}>統計</h2>
      </div>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "18px 22px", WebkitOverflowScrolling: "touch" } as React.CSSProperties}>
        <div style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 12, color: C.sub, marginBottom: 16 }}>
          {toWeekLabel()}
        </div>

        {/* KPI 2×2 grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 22 }}>
          {([
            ["配信", `${totalDelivered}本`],
            ["採用率", `${adoptionRate}%`],
            ["👍 Good", String(stats.totalGood)],
            ["👎 Bad", String(stats.totalBad)],
          ] as [string, string][]).map(([label, value]) => (
            <div key={label} style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 4, padding: "12px 15px" }}>
              <div style={{ fontFamily: SANS, fontSize: 10, color: C.sub, letterSpacing: "0.04em", marginBottom: 5 }}>{label}</div>
              <div style={{ fontFamily: SERIF, fontSize: 27, fontWeight: 600, color: C.ink, letterSpacing: "-0.025em", lineHeight: 1 }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Good/Bad bar */}
        {totalFeedback > 0 && (
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 13.5, color: C.mut, marginBottom: 9 }}>Good / Bad 比率</div>
            <div style={{ display: "flex", height: 9, borderRadius: 2, overflow: "hidden" }}>
              <div style={{ flex: stats.totalGood, background: C.good }} />
              <div style={{ flex: stats.totalBad, background: C.accent }} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 5 }}>
              <span style={{ fontFamily: SANS, fontSize: 11, color: "#0a7d5a", fontWeight: 600 }}>Good {adoptionRate}%</span>
              <span style={{ fontFamily: SANS, fontSize: 11, color: "#b1402e", fontWeight: 600 }}>Bad {100 - adoptionRate}%</span>
            </div>
          </div>
        )}

        {/* Category bars */}
        {catBars.length > 0 && (
          <div>
            <div style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 13.5, color: C.mut, marginBottom: 13 }}>カテゴリ別配信数</div>
            {catBars.map(({ id, pct }) => (
              <div key={id} style={{ marginBottom: 13 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5, alignItems: "center" }}>
                  <span style={{ fontFamily: SANS, fontSize: 12, color: C.ink, display: "flex", alignItems: "center", gap: 7 }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: catColor(id), display: "inline-block", flexShrink: 0 }} />
                    {categoryLabel(categories, id)}
                  </span>
                  <span style={{ fontFamily: MONO, fontSize: 11.5, color: C.sub }}>{pct}%</span>
                </div>
                <div style={{ height: 5, background: C.line, borderRadius: 2 }}>
                  <div style={{ height: "100%", width: `${pct}%`, background: catColor(id), borderRadius: 2 }} />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Trend note */}
        {topCatLabel && (
          <div style={{ marginTop: 22, padding: "13px 16px", border: `1px solid ${C.line}`, borderLeft: `3px solid ${catColor(topCat.id)}`, borderRadius: 2, background: C.surface }}>
            <div style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 13, color: C.mut, lineHeight: 1.6 }}>
              配信数トップ —{" "}
              <span style={{ color: catColor(topCat.id), fontWeight: 600 }}>{topCatLabel}</span>{" "}
              が全体の {topCat.pct}% を占めています。
            </div>
          </div>
        )}

        <div style={{ height: 16 }} />
      </div>
    </div>
  );
}
