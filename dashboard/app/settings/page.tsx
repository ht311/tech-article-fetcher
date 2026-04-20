"use client";

import { useEffect, useRef, useState } from "react";
import CategoryEditor from "../components/CategoryEditor";
import SourceEditor from "../components/SourceEditor";
import type { SourceDef, UserSettings } from "../../functions/api/_types";
import ParamsEditor from "../components/ParamsEditor";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { HelpText } from "../components/ui/HelpText";
import { TooltipProvider } from "../components/ui/Tooltip";

type Tab = "categories" | "sources" | "params" | "keywords";

const TABS: { id: Tab; label: string }[] = [
  { id: "categories", label: "カテゴリ" },
  { id: "sources", label: "ソース" },
  { id: "params", label: "パラメータ" },
  { id: "keywords", label: "キーワード" },
];

function KeywordList({
  label,
  description,
  keywords,
  onChange,
}: {
  label: string;
  description: string;
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
      <p className="text-sm font-medium mb-0.5">{label}</p>
      <HelpText>{description}</HelpText>
      <div className="flex gap-2 mt-2 mb-2">
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
  const [original, setOriginal] = useState<UserSettings | null>(null);
  const [tab, setTab] = useState<Tab>("categories");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [seedError, setSeedError] = useState<string | null>(null);
  const [initCatConfirm, setInitCatConfirm] = useState(false);
  const [initSrcConfirm, setInitSrcConfirm] = useState(false);
  const defaultsRef = useRef<{ category_defs?: UserSettings["category_defs"]; sources?: SourceDef[] } | null>(null);

  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json() as Promise<UserSettings>)
      .then((s) => {
        setSettings(s);
        setOriginal(s);
      });
  }, []);

  const isDirty = original !== null && settings !== null &&
    JSON.stringify(original) !== JSON.stringify(settings);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isDirty]);

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
    setOriginal(settings);
    setTimeout(() => setSaved(false), 3000);
  };

  const fetchDefaults = async () => {
    setSeedError(null);
    const res = await fetch("/api/defaults");
    if (!res.ok) {
      setSeedError("デフォルトが未 seed です。python -m src.seed を実行してください。");
      return null;
    }
    const data = await res.json() as { category_defs?: UserSettings["category_defs"]; sources?: SourceDef[] };
    defaultsRef.current = data;
    return data;
  };

  const handleInitCategories = async () => {
    const data = await fetchDefaults();
    if (!data) return;
    setInitCatConfirm(true);
  };

  const handleInitSources = async () => {
    const data = await fetchDefaults();
    if (!data) return;
    setInitSrcConfirm(true);
  };

  const applyDefaultCategories = () => {
    if (!settings || !defaultsRef.current) return;
    setSettings({ ...settings, category_defs: defaultsRef.current.category_defs ?? [] });
  };

  const applyDefaultSources = () => {
    if (!settings || !defaultsRef.current) return;
    setSettings({
      ...settings,
      sources: defaultsRef.current.sources ?? [],
      category_defs: defaultsRef.current.category_defs ?? settings.category_defs,
    });
  };

  if (!settings) return <p className="text-sm text-gray-400">読み込み中...</p>;

  const sources = settings.sources ?? [];
  const categoryDefs = settings.category_defs ?? [];
  const enabledCategoryCount = categoryDefs.filter((c) => c.enabled).length;

  return (
    <TooltipProvider>
      <div className="space-y-6 max-w-3xl">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">設定</h1>
          <div className="flex items-center gap-2">
            {isDirty && (
              <span className="flex items-center gap-1.5 text-xs text-amber-600">
                <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
                未保存の変更があります
              </span>
            )}
            <button
              onClick={save}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "保存中..." : saved ? "✓ 保存しました（次回配信バッチから反映）" : "保存"}
            </button>
          </div>
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
              <h2 className="font-semibold mb-1">カテゴリ設定</h2>
              <HelpText>配信する記事のカテゴリ（テーマ）を定義します。各カテゴリにキーワードを設定すると Gemini が記事を分類します。</HelpText>
              <div className="mt-4">
                {categoryDefs.length > 0 ? (
                  <CategoryEditor
                    categories={categoryDefs}
                    onChange={(cats) => setSettings({ ...settings, category_defs: cats })}
                  />
                ) : (
                  <div className="space-y-3">
                    <p className="text-sm text-gray-500">
                      カテゴリが未設定です。デフォルトから初期化してください。
                    </p>
                    {seedError && <HelpText>{seedError}</HelpText>}
                    <button
                      onClick={handleInitCategories}
                      className="px-3 py-1.5 bg-blue-50 text-blue-700 text-sm rounded hover:bg-blue-100"
                    >
                      カテゴリを初期化する
                    </button>
                  </div>
                )}
              </div>
            </>
          )}

          {tab === "sources" && (
            <>
              <h2 className="font-semibold mb-1">ソース設定</h2>
              <HelpText>記事を取得するフィード・API の一覧です。有効なソースのみがバッチ実行時に取得されます。</HelpText>
              <div className="mt-4">
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
                    {seedError && <HelpText>{seedError}</HelpText>}
                    <button
                      onClick={handleInitSources}
                      className="px-3 py-1.5 bg-blue-50 text-blue-700 text-sm rounded hover:bg-blue-100"
                    >
                      ソースを初期化する
                    </button>
                  </div>
                )}
              </div>
            </>
          )}

          {tab === "params" && (
            <>
              <h2 className="font-semibold mb-1">パラメータ設定</h2>
              <HelpText>配信バッチの動作を数値で調整します。変更は保存後、次回配信バッチ（毎日 JST 8:00）から反映されます。</HelpText>
              <div className="mt-4">
                <ParamsEditor
                  maxPerCategory={settings.max_per_category ?? 5}
                  articleFetchHours={settings.article_fetch_hours ?? 24}
                  geminiMaxInput={settings.gemini_max_input_per_category ?? 25}
                  enabledCategoryCount={enabledCategoryCount}
                  onChange={(key, value) => setSettings({ ...settings, [key]: value })}
                />
              </div>
            </>
          )}

          {tab === "keywords" && (
            <>
              <h2 className="font-semibold mb-1">キーワード設定</h2>
              <HelpText>Gemini による記事選定の際の追加指示です。カテゴリのキーワードと組み合わせて機能します。</HelpText>
              <div className="space-y-6 mt-4">
                <KeywordList
                  label="優先キーワード"
                  description='Gemini に「これらを含む記事を優先せよ」と追加指示します。例: React, TypeScript'
                  keywords={settings.include_keywords ?? []}
                  onChange={(kws) => setSettings({ ...settings, include_keywords: kws })}
                />
                <KeywordList
                  label="除外キーワード"
                  description="タイトル・要約にマッチした記事は配信候補から除外します。例: PR, 広告"
                  keywords={settings.exclude_keywords ?? []}
                  onChange={(kws) => setSettings({ ...settings, exclude_keywords: kws })}
                />
              </div>
            </>
          )}
        </div>

        <ConfirmDialog
          open={initCatConfirm}
          onOpenChange={setInitCatConfirm}
          title="カテゴリをデフォルトで初期化しますか？"
          description="現在のカテゴリ設定を破棄してデフォルト値で上書きします。この操作は保存後に確定します。"
          confirmLabel="初期化する"
          variant="destructive"
          onConfirm={applyDefaultCategories}
        />
        <ConfirmDialog
          open={initSrcConfirm}
          onOpenChange={setInitSrcConfirm}
          title="ソースをデフォルトで初期化しますか？"
          description="現在のソース設定を破棄してデフォルト値で上書きします。カテゴリも合わせて初期化されます。この操作は保存後に確定します。"
          confirmLabel="初期化する"
          variant="destructive"
          onConfirm={applyDefaultSources}
        />
      </div>
    </TooltipProvider>
  );
}
