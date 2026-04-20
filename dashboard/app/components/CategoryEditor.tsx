"use client";

import { useState } from "react";
import type { CategoryDef } from "../../functions/api/_types";
import { InfoTooltip, TooltipProvider } from "./ui/Tooltip";
import { ConfirmDialog } from "./ui/ConfirmDialog";

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
          placeholder="例: React, TypeScript"
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
  const [confirmIdx, setConfirmIdx] = useState<number | null>(null);
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

  const confirmingCat = confirmIdx !== null ? sorted[confirmIdx] : null;

  return (
    <TooltipProvider>
      <div className="space-y-3">
        {sorted.map((cat, idx) => (
          <div key={cat.id} className={`border rounded-lg p-3 space-y-2 bg-white transition-colors ${cat.enabled ? "border-gray-200" : "border-gray-100 opacity-60"}`}>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={cat.enabled}
                onChange={(e) => update(idx, { enabled: e.target.checked })}
                className="w-4 h-4 accent-blue-600 shrink-0"
                aria-label={`${cat.name} を有効化`}
              />
              <InfoTooltip text={cat.enabled ? "チェックを外すと次回配信からこのカテゴリが除外されます" : "チェックを入れると次回配信からこのカテゴリが復活します"} />
              <input
                value={cat.name}
                onChange={(e) => update(idx, { name: e.target.value })}
                className="flex-1 border border-gray-200 rounded px-2 py-1 text-sm font-medium"
              />
              <span className="flex items-center gap-1 text-xs text-gray-400 font-mono">
                {cat.id}
                <InfoTooltip text="内部ID。配信記事の分類キーとして使われます" />
              </span>
              <div className="flex gap-1">
                <button
                  onClick={() => move(idx, -1)}
                  disabled={idx === 0}
                  aria-label="上に移動（配信順を変更）"
                  title="上に移動（配信順を変更）"
                  className="px-1.5 text-gray-400 hover:text-gray-700 disabled:opacity-30"
                >↑</button>
                <button
                  onClick={() => move(idx, 1)}
                  disabled={idx === sorted.length - 1}
                  aria-label="下に移動（配信順を変更）"
                  title="下に移動（配信順を変更）"
                  className="px-1.5 text-gray-400 hover:text-gray-700 disabled:opacity-30"
                >↓</button>
                <button
                  onClick={() => setConfirmIdx(idx)}
                  aria-label={`${cat.name} を削除`}
                  className="px-1.5 text-red-400 hover:text-red-600"
                >✕</button>
              </div>
            </div>
            <KeywordChips keywords={cat.keywords} onChange={(kws) => update(idx, { keywords: kws })} />
          </div>
        ))}
        <button onClick={add} className="text-sm text-blue-600 hover:underline">+ カテゴリを追加</button>
      </div>

      <ConfirmDialog
        open={confirmIdx !== null}
        onOpenChange={(open) => { if (!open) setConfirmIdx(null); }}
        title={`カテゴリ「${confirmingCat?.name ?? ""}」を削除しますか？`}
        description="配信履歴は残りますが、今後このカテゴリには記事が配信されません。この操作は保存後に確定します。"
        confirmLabel="削除する"
        variant="destructive"
        onConfirm={() => { if (confirmIdx !== null) remove(confirmIdx); setConfirmIdx(null); }}
      />
    </TooltipProvider>
  );
}
