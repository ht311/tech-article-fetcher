"use client";

import { useState } from "react";

export interface CategoryDef {
  id: string;
  name: string;
  keywords: string[];
  enabled: boolean;
  order: number;
}

interface CategoryEditorProps {
  categories: CategoryDef[];
  onChange: (cats: CategoryDef[]) => void;
}

function KeywordChips({
  keywords,
  onChange,
}: {
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
      <div className="flex gap-1 mb-1">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="キーワード追加"
          className="flex-1 border border-gray-200 rounded px-2 py-0.5 text-xs"
        />
        <button onClick={add} className="px-2 py-0.5 bg-gray-100 rounded text-xs hover:bg-gray-200">+</button>
      </div>
      <div className="flex flex-wrap gap-1">
        {keywords.map((kw) => (
          <span key={kw} className="flex items-center gap-0.5 bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full">
            {kw}
            <button onClick={() => onChange(keywords.filter((k) => k !== kw))} className="hover:text-blue-900">×</button>
          </span>
        ))}
      </div>
    </div>
  );
}

export default function CategoryEditor({ categories, onChange }: CategoryEditorProps) {
  const sorted = [...categories].sort((a, b) => a.order - b.order);

  const update = (idx: number, patch: Partial<CategoryDef>) => {
    const next = sorted.map((c, i) => (i === idx ? { ...c, ...patch } : c));
    onChange(next);
  };

  const add = () => {
    const newId = `cat_${Date.now()}`;
    onChange([...sorted, { id: newId, name: "新しいカテゴリ", keywords: [], enabled: true, order: sorted.length }]);
  };

  const remove = (idx: number) => {
    onChange(sorted.filter((_, i) => i !== idx).map((c, i) => ({ ...c, order: i })));
  };

  const move = (idx: number, dir: -1 | 1) => {
    const next = [...sorted];
    const target = idx + dir;
    if (target < 0 || target >= next.length) return;
    [next[idx], next[target]] = [next[target], next[idx]];
    onChange(next.map((c, i) => ({ ...c, order: i })));
  };

  return (
    <div className="space-y-3">
      {sorted.map((cat, idx) => (
        <div key={cat.id} className="border border-gray-200 rounded-lg p-3 space-y-2 bg-white">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={cat.enabled}
              onChange={(e) => update(idx, { enabled: e.target.checked })}
              className="w-4 h-4 accent-blue-600"
            />
            <input
              value={cat.name}
              onChange={(e) => update(idx, { name: e.target.value })}
              className="flex-1 border border-gray-200 rounded px-2 py-1 text-sm font-medium"
            />
            <span className="text-xs text-gray-400 font-mono">{cat.id}</span>
            <div className="flex gap-1">
              <button onClick={() => move(idx, -1)} disabled={idx === 0} className="px-1.5 text-gray-400 hover:text-gray-700 disabled:opacity-30">↑</button>
              <button onClick={() => move(idx, 1)} disabled={idx === sorted.length - 1} className="px-1.5 text-gray-400 hover:text-gray-700 disabled:opacity-30">↓</button>
              <button onClick={() => remove(idx)} className="px-1.5 text-red-400 hover:text-red-600">✕</button>
            </div>
          </div>
          <KeywordChips keywords={cat.keywords} onChange={(kws) => update(idx, { keywords: kws })} />
        </div>
      ))}
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ カテゴリを追加</button>
    </div>
  );
}
