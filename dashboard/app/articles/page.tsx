"use client";

import { useCallback, useEffect, useState } from "react";
import { catColor } from "../lib/pressColors";
import { categoryLabel, useCategories } from "../lib/useCategories";
import { getRatings, setRating } from "../lib/ratings";
import type { Article } from "../lib/types";

const SERIF = "var(--font-serif)";
const SANS  = "var(--font-sans)";
const C = {
  ink:  "var(--color-press-ink)",
  mut:  "var(--color-press-muted)",
  sub:  "var(--color-press-subtle)",
  line: "var(--color-press-border)",
  accent: "var(--color-press-accent)",
};

function toJSTDate(d: Date) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo" }).format(d);
}

interface ArticlesData {
  dates: string[];
  articles: Record<string, Article[]>;
}

type Filter = "today" | "yesterday" | "all";

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
  url, rating, onRate,
}: {
  url: string;
  rating: "good" | "bad" | undefined;
  onRate: (url: string, action: "good" | "bad") => void;
}) {
  return (
    <div style={{ display: "flex", gap: 6 }}>
      {(["good", "bad"] as const).map((type) => {
        const on = rating === type;
        const col = type === "good" ? "#0a7d5a" : "#b1402e";
        return (
          <button
            key={type}
            type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onRate(url, type); }}
            style={{
              display: "flex", alignItems: "center",
              border: `1px solid ${on ? col : "#e3ddd1"}`,
              background: on ? `rgba(${hexToRgb(col)},0.09)` : "transparent",
              borderRadius: 3, fontFamily: SANS, fontWeight: 600,
              color: on ? col : C.sub, cursor: "pointer", transition: "all 0.14s",
              padding: "3px 9px", fontSize: 12,
            }}
          >
            {type === "good" ? "👍" : "👎"}
          </button>
        );
      })}
    </div>
  );
}

export default function ArticlesPage() {
  const categories = useCategories();
  const today = toJSTDate(new Date());
  const yesterday = toJSTDate(new Date(Date.now() - 86400_000));
  const thirtyDaysAgo = toJSTDate(new Date(Date.now() - 30 * 86400_000));

  const [filter, setFilter] = useState<Filter>("today");
  const [data, setData] = useState<ArticlesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [ratings, setRatings] = useState<Record<string, "good" | "bad">>({});

  useEffect(() => {
    setRatings(getRatings());
  }, []);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/articles?from=${thirtyDaysAgo}&to=${today}`)
      .then((r) => r.json() as Promise<ArticlesData>)
      .then((d) => { setData(d); setLoading(false); });
  }, [today, thirtyDaysAgo]);

  const handleRate = useCallback((url: string, action: "good" | "bad") => {
    const prev = ratings[url];
    const next = prev === action ? null : action;
    if (next === null) {
      setRating(url, null);
      setRatings((r) => { const n = { ...r }; delete n[url]; return n; });
    } else {
      setRating(url, next);
      setRatings((r) => ({ ...r, [url]: next }));
      fetch("/api/preferences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: next, url }),
      }).catch(() => {});
    }
  }, [ratings]);

  // Build grouped articles based on filter
  const filteredDates = (data?.dates ?? []).filter((d) => {
    if (filter === "today") return d === today;
    if (filter === "yesterday") return d === yesterday;
    return true;
  });

  function dateLabel(d: string) {
    if (d === today) return `今日 — ${d.slice(5).replace("-", "月")}日`;
    if (d === yesterday) return `昨日 — ${d.slice(5).replace("-", "月")}日`;
    return `${d.replace("-", "年").replace("-", "月")}日`;
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, background: "var(--color-press-bg)" }}>
      {/* Header */}
      <div style={{ flexShrink: 0, padding: "12px 22px 0", borderBottom: `2px solid ${C.ink}` }}>
        <h2 style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 21, fontWeight: 600, color: C.ink, letterSpacing: "-0.01em", marginBottom: 10 }}>
          過去記事
        </h2>
        <div style={{ display: "flex", gap: 22 }}>
          {([["today", "今日"], ["yesterday", "昨日"], ["all", "すべて"]] as [Filter, string][]).map(([k, l]) => (
            <button
              key={k}
              type="button"
              onClick={() => setFilter(k)}
              style={{
                fontFamily: SANS, fontSize: 11, letterSpacing: "0.1em",
                textTransform: "uppercase", fontWeight: 600,
                color: filter === k ? C.ink : C.sub,
                background: "none", border: "none", cursor: "pointer",
                paddingBottom: 9,
                borderBottom: `2px solid ${filter === k ? C.accent : "transparent"}`,
              }}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: "auto", WebkitOverflowScrolling: "touch" } as React.CSSProperties}>
        {loading ? (
          <div style={{ padding: "32px 22px", textAlign: "center", fontFamily: SANS, fontSize: 13, color: C.sub }}>読み込み中...</div>
        ) : filteredDates.length === 0 ? (
          <div style={{ padding: "32px 22px", textAlign: "center", fontFamily: SANS, fontSize: 13, color: C.sub }}>記録なし</div>
        ) : (
          filteredDates.map((date) => {
            const arts = data?.articles[date] ?? [];
            return (
              <div key={date}>
                <div style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 12.5, color: C.sub, padding: "10px 22px 2px", textAlign: "center" }}>
                  — {dateLabel(date)} —
                </div>
                {arts.map((a, i) => (
                  <div key={a.url} style={{ display: "grid", gridTemplateColumns: "32px 1fr", gap: 12, padding: "14px 22px", borderBottom: `1px solid ${C.line}` }}>
                    <div style={{ fontFamily: SERIF, fontSize: 22, color: C.sub, fontWeight: 500, lineHeight: 1, paddingTop: 3 }}>
                      {String(i + 1).padStart(2, "0")}
                    </div>
                    <div>
                      <Kicker catId={a.category_id} label={categoryLabel(categories, a.category_id)} />
                      <a href={a.url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none" }}>
                        <h3 style={{
                          fontFamily: SERIF, fontWeight: 560, fontSize: 16.5, lineHeight: 1.3,
                          letterSpacing: "-0.01em", color: C.ink, margin: "4px 0 7px",
                          display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
                        } as React.CSSProperties}>
                          {a.title}
                        </h3>
                      </a>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                        <Byline src={a.source} reason={a.reason} />
                        <ReactionRow url={a.url} rating={ratings[a.url]} onRate={handleRate} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            );
          })
        )}
        <div style={{ height: 16 }} />
      </div>
    </div>
  );
}
