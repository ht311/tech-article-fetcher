/** カテゴリID → Tailwind クラス（バッジ背景+文字色） */
const CATEGORY_COLORS: Record<string, string> = {
  backend: "bg-blue-100 text-blue-700",
  frontend: "bg-purple-100 text-purple-700",
  aws: "bg-orange-100 text-orange-700",
  management: "bg-green-100 text-green-700",
  others: "bg-gray-100 text-gray-600",
};

/** カテゴリID → Tailwind プレースホルダ背景色 */
const CATEGORY_BG: Record<string, string> = {
  backend: "bg-blue-100",
  frontend: "bg-purple-100",
  aws: "bg-orange-100",
  management: "bg-green-100",
  others: "bg-gray-100",
};

export function categoryBadgeClass(id: string | null): string {
  return CATEGORY_COLORS[id ?? "others"] ?? CATEGORY_COLORS.others;
}

export function categoryPlaceholderBg(id: string | null): string {
  return CATEGORY_BG[id ?? "others"] ?? CATEGORY_BG.others;
}
