"use client";

import { useState } from "react";

export interface SourceDef {
  name: string;
  type: "rss" | "qiita" | "speakerdeck";
  url?: string;
  params?: Record<string, string | number | string[]>;
  enabled: boolean;
}

interface SourceEditorProps {
  sources: SourceDef[];
  onChange: (sources: SourceDef[]) => void;
}

const TYPE_LABELS: Record<SourceDef["type"], string> = {
  rss: "RSS",
  qiita: "Qiita",
  speakerdeck: "SpeakerDeck",
};

function SourceRow({
  src,
  onUpdate,
  onRemove,
}: {
  src: SourceDef;
  onUpdate: (patch: Partial<SourceDef>) => void;
  onRemove: () => void;
}) {
  const paramKey = src.type === "qiita" ? "tag" : src.type === "speakerdeck" ? "category" : null;
  const paramValue = paramKey ? String(src.params?.[paramKey] ?? "") : "";

  return (
    <div className="flex items-center gap-2 border border-gray-200 rounded p-2 bg-white">
      <input
        type="checkbox"
        checked={src.enabled}
        onChange={(e) => onUpdate({ enabled: e.target.checked })}
        className="w-4 h-4 accent-blue-600 shrink-0"
      />
      <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded shrink-0">{TYPE_LABELS[src.type]}</span>
      <input
        value={src.name}
        onChange={(e) => onUpdate({ name: e.target.value })}
        placeholder="表示名"
        className="w-32 border border-gray-200 rounded px-2 py-0.5 text-sm"
      />
      {src.type === "rss" && (
        <input
          value={src.url ?? ""}
          onChange={(e) => onUpdate({ url: e.target.value })}
          placeholder="https://example.com/feed"
          className="flex-1 border border-gray-200 rounded px-2 py-0.5 text-sm font-mono text-xs"
        />
      )}
      {paramKey && (
        <input
          value={paramValue}
          onChange={(e) => onUpdate({ params: { ...src.params, [paramKey]: e.target.value } })}
          placeholder={paramKey}
          className="flex-1 border border-gray-200 rounded px-2 py-0.5 text-sm"
        />
      )}
      <button onClick={onRemove} className="text-red-400 hover:text-red-600 shrink-0">✕</button>
    </div>
  );
}

export default function SourceEditor({ sources, onChange }: SourceEditorProps) {
  const [newType, setNewType] = useState<SourceDef["type"]>("rss");

  const update = (idx: number, patch: Partial<SourceDef>) => {
    onChange(sources.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
  };

  const remove = (idx: number) => {
    onChange(sources.filter((_, i) => i !== idx));
  };

  const add = () => {
    const base: SourceDef = { name: "", type: newType, enabled: true };
    if (newType === "rss") base.url = "";
    if (newType === "qiita") base.params = { tag: "" };
    if (newType === "speakerdeck") base.params = { category: "" };
    onChange([...sources, base]);
  };

  const groups: SourceDef["type"][] = ["rss", "qiita", "speakerdeck"];

  return (
    <div className="space-y-4">
      {groups.map((type) => {
        const grouped = sources.filter((s) => s.type === type);
        if (grouped.length === 0) return null;
        return (
          <div key={type}>
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{TYPE_LABELS[type]}</p>
            <div className="space-y-1">
              {grouped.map((src) => {
                const idx = sources.indexOf(src);
                return (
                  <SourceRow key={idx} src={src} onUpdate={(p) => update(idx, p)} onRemove={() => remove(idx)} />
                );
              })}
            </div>
          </div>
        );
      })}
      <div className="flex gap-2 pt-2">
        <select
          value={newType}
          onChange={(e) => setNewType(e.target.value as SourceDef["type"])}
          className="border border-gray-300 rounded px-2 py-1 text-sm"
        >
          {groups.map((t) => (
            <option key={t} value={t}>{TYPE_LABELS[t]}</option>
          ))}
        </select>
        <button onClick={add} className="px-3 py-1 text-sm bg-blue-50 text-blue-700 rounded hover:bg-blue-100">
          + ソースを追加
        </button>
      </div>
    </div>
  );
}
