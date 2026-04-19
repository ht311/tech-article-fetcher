"use client";

import { useEffect, useState } from "react";

interface UserSettings {
  categories: Record<string, boolean>;
  sources_enabled: Record<string, boolean>;
  max_per_category: number;
  exclude_keywords: string[];
  include_keywords: string[];
}

const CATEGORY_LABELS: Record<string, string> = {
  backend: "バックエンド",
  frontend: "フロントエンド",
  aws: "AWS",
  management: "マネジメント",
  others: "その他",
};

const ALL_SOURCES = [
  "Zenn", "Qiita人気記事", "はてブIT", "noteテック",
  "メルカリ", "サイバーエージェント", "DeNA", "SmartHR", "LayerX",
  "GitHub Blog", "AWS Blog", "Cloudflare Blog", "Vercel Blog",
  "Qiita", "dev.to", "Hacker News", "SpeakerDeck",
  "Reddit r/java", "Reddit r/SpringBoot", "Reddit r/typescript",
  "Reddit r/reactjs", "Reddit r/nextjs", "Reddit r/aws",
  "Reddit r/agile", "Reddit r/ExperiencedDevs",
];

function KeywordList({
  label,
  keywords,
  onChange,
}: {
  label: string;
  keywords: string[];
  onChange: (kws: string[]) => void;
}) {
  const [input, setInput] = useState("");

  const add = () => {
    const kw = input.trim();
    if (kw && !keywords.includes(kw)) {
      onChange([...keywords, kw]);
    }
    setInput("");
  };

  return (
    <div>
      <p className="text-sm font-medium mb-2">{label}</p>
      <div className="flex gap-2 mb-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="キーワードを入力して Enter"
          className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
        />
        <button
          onClick={add}
          className="px-3 py-1 bg-gray-100 rounded text-sm hover:bg-gray-200"
        >
          追加
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {keywords.map((kw) => (
          <span
            key={kw}
            className="flex items-center gap-1 bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full"
          >
            {kw}
            <button
              onClick={() => onChange(keywords.filter((k) => k !== kw))}
              className="hover:text-blue-900"
            >
              ×
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json() as Promise<UserSettings>)
      .then(setSettings);
  }, []);

  const save = async () => {
    if (!settings) return;
    setSaving(true);
    await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (!settings) return <p className="text-sm text-gray-400">読み込み中...</p>;

  const allSourcesEnabled = ALL_SOURCES.every(
    (s) => settings.sources_enabled[s] !== false
  );

  return (
    <div className="space-y-8 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">設定</h1>
        <button
          onClick={save}
          disabled={saving}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "保存中..." : saved ? "✓ 保存しました" : "保存"}
        </button>
      </div>

      {/* カテゴリ ON/OFF */}
      <section className="bg-white border border-gray-200 rounded-xl p-5 space-y-3">
        <h2 className="font-semibold">カテゴリ配信</h2>
        {Object.entries(CATEGORY_LABELS).map(([id, label]) => (
          <label key={id} className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.categories[id] !== false}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  categories: { ...settings.categories, [id]: e.target.checked },
                })
              }
              className="w-4 h-4 accent-blue-600"
            />
            <span className="text-sm">{label}</span>
          </label>
        ))}
      </section>

      {/* カテゴリあたりの件数 */}
      <section className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="font-semibold mb-3">カテゴリあたりの最大件数</h2>
        <div className="flex items-center gap-3">
          <input
            type="range"
            min={1}
            max={5}
            value={settings.max_per_category}
            onChange={(e) =>
              setSettings({ ...settings, max_per_category: Number(e.target.value) })
            }
            className="w-40 accent-blue-600"
          />
          <span className="text-sm font-medium">{settings.max_per_category} 件</span>
        </div>
      </section>

      {/* ソース ON/OFF */}
      <section className="bg-white border border-gray-200 rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">ソース配信設定</h2>
          <button
            onClick={() =>
              setSettings({
                ...settings,
                sources_enabled: allSourcesEnabled
                  ? Object.fromEntries(ALL_SOURCES.map((s) => [s, false]))
                  : {},
              })
            }
            className="text-xs text-blue-600 hover:underline"
          >
            {allSourcesEnabled ? "全て OFF" : "全て ON"}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {ALL_SOURCES.map((src) => (
            <label key={src} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.sources_enabled[src] !== false}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    sources_enabled: {
                      ...settings.sources_enabled,
                      [src]: e.target.checked,
                    },
                  })
                }
                className="w-3.5 h-3.5 accent-blue-600"
              />
              <span className="text-xs">{src}</span>
            </label>
          ))}
        </div>
      </section>

      {/* キーワード設定 */}
      <section className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
        <h2 className="font-semibold">キーワード設定</h2>
        <KeywordList
          label="優先キーワード（Gemini に追加指示）"
          keywords={settings.include_keywords}
          onChange={(kws) => setSettings({ ...settings, include_keywords: kws })}
        />
        <KeywordList
          label="除外キーワード（タイトル・サマリーにマッチしたら除外）"
          keywords={settings.exclude_keywords}
          onChange={(kws) => setSettings({ ...settings, exclude_keywords: kws })}
        />
      </section>
    </div>
  );
}
