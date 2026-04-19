"use client";

interface ParamsEditorProps {
  maxPerCategory: number;
  articleFetchHours: number;
  geminiMaxInput: number;
  onChange: (key: "max_per_category" | "article_fetch_hours" | "gemini_max_input_per_category", value: number) => void;
}

interface SliderRowProps {
  label: string;
  value: number;
  min: number;
  max: number;
  unit: string;
  onChange: (v: number) => void;
}

function SliderRow({ label, value, min, max, unit, onChange }: SliderRowProps) {
  return (
    <div>
      <p className="text-sm font-medium mb-1">{label}</p>
      <div className="flex items-center gap-3">
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-48 accent-blue-600"
        />
        <input
          type="number"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-20 border border-gray-300 rounded px-2 py-1 text-sm"
        />
        <span className="text-sm text-gray-500">{unit}</span>
      </div>
    </div>
  );
}

export default function ParamsEditor({ maxPerCategory, articleFetchHours, geminiMaxInput, onChange }: ParamsEditorProps) {
  return (
    <div className="space-y-5">
      <SliderRow
        label="カテゴリあたり最大件数"
        value={maxPerCategory}
        min={1}
        max={5}
        unit="件"
        onChange={(v) => onChange("max_per_category", v)}
      />
      <SliderRow
        label="記事フェッチ対象時間"
        value={articleFetchHours}
        min={1}
        max={168}
        unit="時間"
        onChange={(v) => onChange("article_fetch_hours", v)}
      />
      <SliderRow
        label="Gemini 入力上限（カテゴリごと）"
        value={geminiMaxInput}
        min={5}
        max={50}
        unit="件"
        onChange={(v) => onChange("gemini_max_input_per_category", v)}
      />
    </div>
  );
}
