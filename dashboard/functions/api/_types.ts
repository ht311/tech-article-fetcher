export type { SourceDef, CategoryDef, UserSettings } from "./_types.generated";

export interface Env {
  KV: KVNamespace;
}

export interface ArticleHistoryEntry {
  title: string;
  source: string;
  url: string;
  category_id: string | null;
  reason: string;
  thumbnail_url: string | null;
  published_at: string | null;
}

export const VALID_SOURCE_TYPES: ("rss" | "qiita" | "speakerdeck" | "docswell")[] = ["rss", "qiita", "speakerdeck", "docswell"];

export const TYPE_LABELS: Record<"rss" | "qiita" | "speakerdeck" | "docswell", string> = {
  rss: "RSS",
  qiita: "Qiita",
  speakerdeck: "SpeakerDeck",
  docswell: "Docswell",
};
