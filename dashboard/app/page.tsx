"use client";

import { useCallback, useEffect, useState } from "react";
import { catColor, catEmoji, catGradient } from "./lib/pressColors";
import { categoryLabel, useCategories } from "./lib/useCategories";
import { getRatings, setRating } from "./lib/ratings";
import type { Article } from "./lib/types";

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
const DAYS_JP = ["日", "月", "火", "水", "木", "金", "土"];

function toJSTDate(d: Date) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo" }).format(d);
}

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

function hexToRgb(hex: string) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `${r},${g},${b}`;
}

function Kicker({ catId, label }: { catId: string | null; label: string }) {
  return (
    <div style={{
      fontFamily: SANS, fontSize: 10, letterSpacing: "0.16em",
      textTransform: "uppercase", fontWeight: 700,
      color: catColor(catId),
    }}>
      {label}
    </div>
  );
}

function Byline({ src, reason }: { src: string; reason?: string }) {
  return (
    <div style={{ fontFamily: SANS, fontSize: 11, color: C.sub, display: "flex", gap: 5, alignItems: "center", flexWrap: "wrap" }}>
      <span style={{ color: C.ink, fontWeight: 600 }}>{src}</span>
      {reason && (
        <>
          <span style={{ opacity: 0.5 }}>·</span>
          <span>🏷 {reason}</span>
        </>
      )}
    </div>
  );
}

function ReactionRow({
  url, rating, onRate, mini = false,
}: {
  url: string;
  rating: "good" | "bad" | undefined;
  onRate: (url: string, action: "good" | "bad") => void;
  mini?: boolean;
}) {
  const sz = mini
    ? { padding: "3px 9px", fontSize: 12 }
    : { padding: "6px 14px", fontSize: 13 };
  return (
    <div style={{ display: "flex", gap: 6 }}>
      {(["good", "bad"] as const).map((type) => {
        const on = rating === type;
        const col = type === "good" ? "#0a7d5a" : "#b1402e";
        const label = mini ? (type === "good" ? "👍" : "👎") : (type === "good" ? "👍 Good" : "👎 Bad");
        return (
          <button
            key={type}
            type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onRate(url, type); }}
            style={{
              display: "flex", alignItems: "center", gap: 4,
              border: `1px solid ${on ? col : "#e3ddd1"}`,
              background: on ? `rgba(${hexToRgb(col)},0.09)` : "transparent",
              borderRadius: 3, fontFamily: SANS, fontWeight: 600,
              color: on ? col : C.sub, cursor: "pointer", transition: "all 0.14s",
              ...sz,
            }}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

export default function HomePage() {
  const categories = useCategories();
  const [stats, setStats] = useState<StatsData | null>(null);
  const [todayArticles, setTodayArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [ratings, setRatings] = useState<Record<string, "good" | "bad">>({});

  const todayStr = toJSTDate(new Date());
  const todayDate = new Date(todayStr);
  const dayOfWeek = DAYS_JP[todayDate.getDay()];
  const [year, month, day] = todayStr.split("-");
  const uniqueSources = [...new Set(todayArticles.map((a) => a.source))].length;

  useEffect(() => {
    setRatings(getRatings());
    Promise.all([
      fetch("/api/stats").then((r) => r.json() as Promise<StatsData>),
      fetch(`/api/articles?from=${todayStr}&to=${todayStr}`).then((r) => r.json() as Promise<ArticlesData>),
    ]).then(([s, a]) => {
      setStats(s);
      setTodayArticles(a.articles[todayStr] ?? []);
      setLoading(false);
    });
  }, [todayStr]);

  const handleRate = useCallback((url: string, action: "good" | "bad") => {
    const prev = ratings[url];
    const next = prev === action ? null : action;
    if (next === null) {
      setRating(url, null);
      setRatings((r) => { const n = { ...r }; delete n[url]; return n; });
    } else {
      setRating(url, next);
      setRatings((r) => ({ ...r, [url]: next }));
    }
    if (next) {
      const article = todayArticles.find((a) => a.url === url);
      if (article) {
        fetch("/api/preferences", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: next, title: article.title, source: article.source, url }),
        }).catch(() => {});
      }
    }
  }, [ratings, todayArticles]);

  const totalFeedback = (stats?.totalGood ?? 0) + (stats?.totalBad ?? 0);
  const adoptionRate = totalFeedback > 0
    ? `${Math.round(((stats?.totalGood ?? 0) / totalFeedback) * 100)}%`
    : "—";

  const [lead, ...rest] = todayArticles;

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, background: "var(--color-press-bg)" }}>
      {/* Masthead */}
      <div style={{ flexShrink: 0, padding: "12px 22px 10px", borderBottom: `2px solid ${C.ink}`, textAlign: "center" }}>
        <div style={{ fontFamily: SERIF, fontSize: 25, fontWeight: 600, fontStyle: "italic", letterSpacing: "-0.01em", color: C.ink, lineHeight: 1.1 }}>
          <span style={{ fontStyle: "normal", fontWeight: 700 }}>Tech</span> Dispatch
        </div>
        <div style={{ fontFamily: SERIF, fontSize: 11, color: C.mut, marginTop: 3, letterSpacing: "0.02em" }}>
          {loading
            ? " "
            : `${year}年${month}月${day}日 ${dayOfWeek}曜日 — 本日 ${todayArticles.length}本 / ${uniqueSources}ソース`}
        </div>
      </div>

      {/* Stats strip */}
      <div style={{ flexShrink: 0, display: "flex", justifyContent: "space-around", padding: "9px 16px", borderBottom: `1px solid ${C.line}` }}>
        {([
          ["配信", String(todayArticles.length)],
          ["👍 Good", String(stats?.totalGood ?? "—")],
          ["👎 Bad", String(stats?.totalBad ?? "—")],
          ["採用率", adoptionRate],
        ] as [string, string][]).map(([k, v]) => (
          <div key={k} style={{ textAlign: "center" }}>
            <div style={{ fontFamily: MONO, fontSize: 16, fontWeight: 600, color: C.ink, letterSpacing: "-0.02em", lineHeight: 1 }}>{v}</div>
            <div style={{ fontFamily: SANS, fontSize: 9.5, color: C.sub, marginTop: 2 }}>{k}</div>
          </div>
        ))}
      </div>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: "auto", WebkitOverflowScrolling: "touch" } as React.CSSProperties}>
        {loading ? (
          <div style={{ padding: "32px 22px", textAlign: "center", fontFamily: SANS, fontSize: 13, color: C.sub }}>読み込み中...</div>
        ) : todayArticles.length === 0 ? (
          <div style={{ padding: "32px 22px", textAlign: "center", fontFamily: SANS, fontSize: 13, color: C.sub }}>本日の配信はまだありません</div>
        ) : (
          <>
            {/* Lead article */}
            {lead && (
              <div style={{ padding: "18px 22px 20px", borderBottom: `1px solid ${C.line}` }}>
                <Kicker catId={lead.category_id} label={categoryLabel(categories, lead.category_id)} />
                <a href={lead.url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none" }}>
                  <div style={{
                    height: 152, borderRadius: 3, marginTop: 10, marginBottom: 14,
                    background: catGradient(lead.category_id), position: "relative", overflow: "hidden",
                  }}>
                    <span style={{
                      position: "absolute", top: 10, left: 10, fontFamily: MONO, fontSize: 10,
                      background: "rgba(255,255,255,0.9)", padding: "3px 8px", borderRadius: 3,
                      fontWeight: 600, color: C.ink,
                    }}>{lead.source}</span>
                    <span style={{ position: "absolute", right: 12, bottom: 8, fontSize: 40, opacity: 0.45 }}>
                      {catEmoji(lead.category_id)}
                    </span>
                  </div>
                  <h1 style={{
                    fontFamily: SERIF, fontWeight: 560, fontSize: 26, lineHeight: 1.15,
                    letterSpacing: "-0.01em", color: C.ink, margin: "0 0 10px",
                  }}>
                    {lead.title}
                  </h1>
                  {lead.summary && (
                    <p style={{ fontFamily: SERIF, fontSize: 15, lineHeight: 1.6, color: "#3a352e", margin: "0 0 12px" }}>
                      {lead.summary}
                    </p>
                  )}
                </a>
                <Byline src={lead.source} reason={lead.reason} />
                <div style={{ marginTop: 13 }}>
                  <ReactionRow url={lead.url} rating={ratings[lead.url]} onRate={handleRate} />
                </div>
              </div>
            )}

            {/* Section divider */}
            {rest.length > 0 && (
              <div style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 13, color: C.sub, padding: "12px 22px 2px", textAlign: "center" }}>
                — 本日のその他の記事 —
              </div>
            )}

            {/* Article list */}
            {rest.map((a, i) => (
              <div key={a.url} style={{ display: "grid", gridTemplateColumns: "34px 1fr", gap: 13, padding: "15px 22px", borderBottom: `1px solid ${C.line}` }}>
                <div style={{ fontFamily: SERIF, fontSize: 24, color: C.sub, fontWeight: 500, lineHeight: 1, paddingTop: 5 }}>
                  {String(i + 2).padStart(2, "0")}
                </div>
                <div>
                  <Kicker catId={a.category_id} label={categoryLabel(categories, a.category_id)} />
                  <a href={a.url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none" }}>
                    <h3 style={{
                      fontFamily: SERIF, fontWeight: 560, fontSize: 17, lineHeight: 1.28,
                      letterSpacing: "-0.01em", color: C.ink, margin: "5px 0 6px",
                      display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
                    } as React.CSSProperties}>
                      {a.title}
                    </h3>
                    {a.summary && (
                      <p style={{
                        fontFamily: SERIF, fontSize: 12.5, color: C.mut, lineHeight: 1.55, margin: "0 0 7px",
                        display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
                      } as React.CSSProperties}>
                        {a.summary}
                      </p>
                    )}
                  </a>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                    <Byline src={a.source} reason={a.reason} />
                    <ReactionRow url={a.url} rating={ratings[a.url]} onRate={handleRate} mini />
                  </div>
                </div>
              </div>
            ))}
            <div style={{ height: 16 }} />
          </>
        )}
      </div>
    </div>
  );
}
