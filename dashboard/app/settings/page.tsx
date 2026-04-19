"use client";

import { useEffect, useState } from "react";
import CategoryEditor, { type CategoryDef } from "../components/CategoryEditor";
import SourceEditor, { type SourceDef } from "../components/SourceEditor";
import ParamsEditor from "../components/ParamsEditor";

interface UserSettings {
  categories: Record<string, boolean>;
  sources_enabled: Record<string, boolean>;
  max_per_category: number;
  exclude_keywords: string[];
  include_keywords: string[];
  sources?: SourceDef[];
  category_defs?: CategoryDef[];
  article_fetch_hours?: number;
  gemini_max_input_per_category?: number;
  schema_version?: 1 | 2;
}

type Tab = "categories" | "sources" | "params" | "keywords";

const TABS: { id: Tab; label: string }[] = [
  { id: "categories", label: "カテゴリ" },
  { id: "sources", label: "ソース" },
  { id: "params", label: "パラメータ" },
  { id: "keywords", label: "キーワード" },
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
    if (kw && !keywords.includes(kw)) onChange([...keywords, kw]);
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
        <button onClick={add} className="px-3 py-1 bg-gray-100 rounded text-sm hover:bg-gray-200">追加</button>
      </div>
      <div className="flex flex-wrap gap-2">
        {keywords.map((kw) => (
          <span key={kw} className="flex items-center gap-1 bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full">
            {kw}
            <button onClick={() => onChange(keywords.filter((k) => k !== kw))} className="hover:text-blue-900">×</button>
          </span>
        ))}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [tab, setTab] = useState<Tab>("categories");
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

  const sources = settings.sources ?? [];
  const categoryDefs = settings.category_defs ?? [];

  return (
    <div className="space-y-6 max-w-3xl">
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

      {/* タブ */}
      <div className="flex border-b border-gray-200 gap-0">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === id
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5">
        {tab === "categories" && (
          <>
            <h2 className="font-semibold mb-4">カテゴリ設定</h2>
            {categoryDefs.length > 0 ? (
              <CategoryEditor
                categories={categoryDefs}
                onChange={(cats) => setSettings({ ...settings, category_defs: cats })}
              />
            ) : (
              /* v1 互換: category_defs 未設定時は v1 の ON/OFF のみ表示 */
              <div className="space-y-3">
                {Object.entries(settings.categories).map(([id, enabled]) => (
                  <label key={id} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enabled !== false}
                      onChange={(e) =>
                        setSettings({ ...settings, categories: { ...settings.categories, [id]: e.target.checked } })
                      }
                      className="w-4 h-4 accent-blue-600"
                    />
                    <span className="text-sm">{id}</span>
                  </label>
                ))}
                <p className="text-xs text-gray-400 mt-2">
                  v2 設定を有効にするには「ソース」タブで保存してください。
                </p>
              </div>
            )}
          </>
        )}

        {tab === "sources" && (
          <>
            <h2 className="font-semibold mb-4">ソース設定</h2>
            {sources.length > 0 ? (
              <SourceEditor
                sources={sources}
                onChange={(srcs) => setSettings({ ...settings, sources: srcs })}
              />
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-gray-500">
                  現在は fetcher のデフォルトソースが使用されています。
                  ソースを管理するには初期化してください。
                </p>
                <button
                  onClick={() =>
                    setSettings({
                      ...settings,
                      sources: [
                        { name: "Zenn", type: "rss", url: "https://zenn.dev/feed", enabled: true },
                        { name: "Qiita人気記事", type: "rss", url: "https://qiita.com/popular-items/feed", enabled: true },
                        { name: "GitHub Blog", type: "rss", url: "https://github.blog/feed/", enabled: true },
                        { name: "Qiita:TypeScript", type: "qiita", params: { tag: "TypeScript" }, enabled: true },
                        { name: "SpeakerDeck:programming", type: "speakerdeck", params: { category: "programming" }, enabled: true },
                      ],
                    })
                  }
                  className="px-3 py-1.5 bg-blue-50 text-blue-700 text-sm rounded hover:bg-blue-100"
                >
                  ソースを初期化する
                </button>
              </div>
            )}
          </>
        )}

        {tab === "params" && (
          <>
            <h2 className="font-semibold mb-4">パラメータ設定</h2>
            <ParamsEditor
              maxPerCategory={settings.max_per_category}
              articleFetchHours={settings.article_fetch_hours ?? 24}
              geminiMaxInput={settings.gemini_max_input_per_category ?? 25}
              onChange={(key, value) => setSettings({ ...settings, [key]: value })}
            />
          </>
        )}

        {tab === "keywords" && (
          <>
            <h2 className="font-semibold mb-4">キーワード設定</h2>
            <div className="space-y-4">
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
            </div>
          </>
        )}
      </div>
    </div>
  );
}
