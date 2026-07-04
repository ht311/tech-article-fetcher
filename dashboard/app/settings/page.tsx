"use client";

import { useEffect, useState } from "react";
import type { UserSettings } from "../../functions/api/_types";

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

const CAT_COLORS: Record<string, string> = {
  backend:    "#1c4fd8",
  frontend:   "#7a2fbd",
  aws:        "#c2410c",
  management: "#0a7d5a",
};
function catColor(id: string) {
  return CAT_COLORS[id] ?? "#9a9183";
}

const LS_DELIVERY_KEY = "press_delivery_time";
// src/core/config.py の SEMANTIC_DEDUP_THRESHOLD と同値（未設定時の表示用）
const DEFAULT_DEDUP_THRESHOLD = 0.88;

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontFamily: SANS, fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 700, color: C.sub, marginBottom: 15 }}>
      {children}
    </div>
  );
}

function Toggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={onToggle}
      style={{
        width: 42, height: 24, borderRadius: 12,
        background: on ? C.accent : C.line,
        position: "relative", cursor: "pointer",
        transition: "background 0.2s", flexShrink: 0,
        border: "none", padding: 0,
      }}
    >
      <div style={{
        position: "absolute", top: 3, left: on ? 21 : 3,
        width: 18, height: 18, borderRadius: "50%",
        background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
        transition: "left 0.2s",
      }} />
    </button>
  );
}

interface StatsData {
  totalGood: number;
  totalBad: number;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [deliveryTime, setDeliveryTime] = useState("08:00");
  const [stats, setStats] = useState<StatsData | null>(null);
  const [saving, setSaving] = useState(false);
  const [threshold, setThreshold] = useState(DEFAULT_DEDUP_THRESHOLD);

  useEffect(() => {
    const saved = localStorage.getItem(LS_DELIVERY_KEY);
    if (saved) setDeliveryTime(saved);

    fetch("/api/settings")
      .then((r) => r.json() as Promise<UserSettings>)
      .then((s) => {
        setSettings(s);
        setThreshold(s.semantic_dedup_threshold ?? DEFAULT_DEDUP_THRESHOLD);
      })
      .catch(() => {});

    fetch("/api/stats")
      .then((r) => r.json() as Promise<StatsData>)
      .then(setStats)
      .catch(() => {});
  }, []);

  function handleTimeBlur() {
    localStorage.setItem(LS_DELIVERY_KEY, deliveryTime);
  }

  async function toggleCategory(id: string) {
    if (!settings?.category_defs) return;
    const updated = settings.category_defs.map((c) =>
      c.id === id ? { ...c, enabled: !c.enabled } : c
    );
    const next = { ...settings, category_defs: updated };
    setSettings(next);
    setSaving(true);
    await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(next),
    }).catch(() => {});
    setSaving(false);
  }

  async function saveThreshold(v: number) {
    if (!settings) return;
    const next = { ...settings, semantic_dedup_threshold: v };
    setSettings(next);
    setSaving(true);
    await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(next),
    }).catch(() => {});
    setSaving(false);
  }

  const totalFeedback = (stats?.totalGood ?? 0) + (stats?.totalBad ?? 0);
  const adoptionRate = totalFeedback > 0
    ? `${(((stats?.totalGood ?? 0) / totalFeedback) * 100).toFixed(1)}%`
    : "—";

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, background: "var(--color-press-bg)" }}>
      {/* Header */}
      <div style={{ flexShrink: 0, padding: "12px 22px 12px", borderBottom: `2px solid ${C.ink}` }}>
        <h2 style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 21, fontWeight: 600, color: C.ink, letterSpacing: "-0.01em" }}>設定</h2>
      </div>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: "auto", WebkitOverflowScrolling: "touch" } as React.CSSProperties}>
        {/* Delivery time */}
        <div style={{ padding: "16px 22px 18px", borderBottom: `1px solid ${C.line}` }}>
          <SectionLabel>配信設定</SectionLabel>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <div>
              <div style={{ fontFamily: SERIF, fontSize: 16.5, color: C.ink, marginBottom: 3 }}>配信時刻</div>
              <div style={{ fontFamily: SANS, fontSize: 11.5, color: C.sub }}>毎朝 LINE へ配信する時刻</div>
            </div>
            <input
              type="time"
              value={deliveryTime}
              onChange={(e) => setDeliveryTime(e.target.value)}
              onBlur={handleTimeBlur}
              style={{
                fontFamily: MONO, fontSize: 14, color: C.ink,
                border: `1px solid ${C.line}`,
                background: C.surface, borderRadius: 4,
                padding: "6px 10px", flexShrink: 0, cursor: "pointer",
                outline: "none",
              }}
            />
          </div>
        </div>

        {/* Categories */}
        <div style={{ padding: "16px 22px 18px", borderBottom: `1px solid ${C.line}` }}>
          <SectionLabel>カテゴリ</SectionLabel>
          {saving && (
            <div style={{ fontFamily: SANS, fontSize: 11, color: C.sub, marginBottom: 12 }}>保存中...</div>
          )}
          {!settings ? (
            <div style={{ fontFamily: SANS, fontSize: 13, color: C.sub }}>読み込み中...</div>
          ) : (settings.category_defs ?? []).map((cat) => (
            <div key={cat.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: catColor(cat.id), display: "inline-block", flexShrink: 0 }} />
                <span style={{ fontFamily: SERIF, fontSize: 16, color: C.ink }}>{cat.name}</span>
              </div>
              <Toggle on={cat.enabled ?? true} onToggle={() => toggleCategory(cat.id)} />
            </div>
          ))}
        </div>

        {/* Selection tuning */}
        <div style={{ padding: "16px 22px 18px", borderBottom: `1px solid ${C.line}` }}>
          <SectionLabel>選定チューニング</SectionLabel>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 3 }}>
            <div style={{ fontFamily: SERIF, fontSize: 16.5, color: C.ink }}>重複判定しきい値</div>
            <div style={{
              fontFamily: MONO, fontSize: 14, color: C.ink,
              border: `1px solid ${C.line}`, background: C.surface,
              borderRadius: 4, padding: "4px 10px", flexShrink: 0,
            }}>
              {threshold.toFixed(2)}
            </div>
          </div>
          <div style={{ fontFamily: SANS, fontSize: 11.5, color: C.sub, marginBottom: 12 }}>
            意味的に同一トピックとみなすコサイン類似度。高いほど重複判定が厳しくなる（1.0 で実質無効）
          </div>
          <input
            type="range"
            min={0.5}
            max={1}
            step={0.01}
            value={threshold}
            disabled={!settings}
            onChange={(e) => setThreshold(Number(e.target.value))}
            onPointerUp={(e) => saveThreshold(Number(e.currentTarget.value))}
            onBlur={(e) => saveThreshold(Number(e.currentTarget.value))}
            style={{ width: "100%", accentColor: C.accent, cursor: "pointer" }}
          />
        </div>

        {/* Feedback */}
        <div style={{ padding: "16px 22px" }}>
          <SectionLabel>学習フィードバック</SectionLabel>
          <div style={{ fontFamily: SERIF, fontSize: 14.5, color: C.mut, lineHeight: 1.7 }}>
            👍 / 👎 のフィードバックを Gemini の選別基準に反映します。
            {totalFeedback > 0 && (
              <>
                <br />
                累積{" "}
                <span style={{ color: C.ink, fontWeight: 600 }}>{totalFeedback}</span> 件のフィードバックを学習済み。
              </>
            )}
          </div>
          {totalFeedback > 0 && (
            <div style={{ marginTop: 14, padding: "10px 14px", border: `1px solid ${C.line}`, borderRadius: 4, background: C.surface }}>
              <div style={{ fontFamily: SANS, fontSize: 11.5, color: C.sub, display: "flex", justifyContent: "space-between" }}>
                <span>今月の採用率</span>
                <span style={{ color: "#0a7d5a", fontWeight: 600, fontFamily: MONO }}>{adoptionRate}</span>
              </div>
            </div>
          )}
        </div>

        <div style={{ height: 16 }} />
      </div>
    </div>
  );
}
