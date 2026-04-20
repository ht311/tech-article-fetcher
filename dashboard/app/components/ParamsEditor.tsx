"use client";

import { HelpText } from "./ui/HelpText";

interface ParamsEditorProps {
  maxPerCategory: number;
  articleFetchHours: number;
  geminiMaxInput: number;
  enabledCategoryCount: number;
  onChange: (key: "max_per_category" | "article_fetch_hours" | "gemini_max_input_per_category", value: number) => void;
}

interface SliderRowProps {
  label: string;
  value: number;
  min: number;
  max: number;
  unit: string;
  description: string;
  preview: string;
  onChange: (v: number) => void;
}

function SliderRow({ label, value, min, max, unit, description, preview, onChange }: SliderRowProps) {
  return (
    <div>
      <p className="text-sm font-medium mb-0.5">{label}</p>
      <HelpText>{description}</HelpText>
      <div className="flex items-center gap-3 mt-2">
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
      <HelpText variant="preview">{preview}</HelpText>
    </div>
  );
}

export default function ParamsEditor({ maxPerCategory, articleFetchHours, geminiMaxInput, enabledCategoryCount, onChange }: ParamsEditorProps) {
  const catCount = enabledCategoryCount > 0 ? enabledCategoryCount : null;
  const maxArticles = catCount !== null ? catCount * maxPerCategory : null;
  const days = Math.round((articleFetchHours / 24) * 10) / 10;

  return (
    <div className="space-y-6">
      <SliderRow
        label="カテゴリあたり最大件数"
        value={maxPerCategory}
        min={1}
        max={5}
        unit="件"
        description="1つのカテゴリから配信する記事の上限数です"
        preview={
          catCount !== null
            ? `有効カテゴリ ${catCount} 件 × 最大 ${maxPerCategory} 件 = 1日最大 ${maxArticles} 記事`
            : `最大 ${maxPerCategory} 件 / カテゴリ（有効カテゴリ数が設定されると合計が確定します）`
        }
        onChange={(v) => onChange("max_per_category", v)}
      />
      <SliderRow
        label="記事フェッチ対象時間"
        value={articleFetchHours}
        min={1}
        max={168}
        unit="時間"
        description="バッチ実行時点から何時間前までに公開された記事を取得するかを指定します"
        preview={`過去 ${articleFetchHours} 時間（約 ${days} 日分）に公開された記事を対象にします`}
        onChange={(v) => onChange("article_fetch_hours", v)}
      />
      <SliderRow
        label="Gemini 入力上限（カテゴリごと）"
        value={geminiMaxInput}
        min={5}
        max={50}
        unit="件"
        description="各カテゴリで Gemini に評価させる候補記事の最大数です。多いほど精度が上がりますが処理時間も増えます"
        preview={`各カテゴリから最大 ${geminiMaxInput} 件を Gemini で評価し、上位 ${maxPerCategory} 件を選定します`}
        onChange={(v) => onChange("gemini_max_input_per_category", v)}
      />
    </div>
  );
}
