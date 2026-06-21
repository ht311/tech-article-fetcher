const CAT_COLORS: Record<string, string> = {
  backend:    "#1c4fd8",
  frontend:   "#7a2fbd",
  aws:        "#c2410c",
  management: "#0a7d5a",
};

const CAT_EMOJI: Record<string, string> = {
  backend:    "🗄️",
  frontend:   "🎨",
  aws:        "☁️",
  management: "🧭",
};

export function catColor(id: string | null | undefined): string {
  return CAT_COLORS[id ?? ""] ?? "#9a9183";
}

export function catEmoji(id: string | null | undefined): string {
  return CAT_EMOJI[id ?? ""] ?? "📄";
}

export function catGradient(id: string | null | undefined): string {
  const hex = catColor(id);
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `linear-gradient(140deg,rgba(${r},${g},${b},0.24),rgba(${r},${g},${b},0.08))`;
}
