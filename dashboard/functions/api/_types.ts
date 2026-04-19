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

export interface SourceDef {
  name: string;
  type: "rss" | "qiita" | "speakerdeck";
  url?: string;
  params?: Record<string, string | number | string[]>;
  enabled: boolean;
}

export interface CategoryDef {
  id: string;
  name: string;
  keywords: string[];
  enabled: boolean;
  order: number;
}

export interface UserSettings {
  // v1 互換フィールド
  categories: Record<string, boolean>;
  sources_enabled: Record<string, boolean>;
  max_per_category: number;
  exclude_keywords: string[];
  include_keywords: string[];
  // v2 新フィールド
  sources?: SourceDef[];
  category_defs?: CategoryDef[];
  article_fetch_hours?: number;
  gemini_max_input_per_category?: number;
  schema_version?: 1 | 2;
}

export const DEFAULT_SETTINGS: UserSettings = {
  categories: {
    backend: true,
    frontend: true,
    aws: true,
    management: true,
    others: true,
  },
  sources_enabled: {},
  max_per_category: 5,
  exclude_keywords: [],
  include_keywords: [],
};

export const VALID_SOURCE_TYPES: SourceDef["type"][] = ["rss", "qiita", "speakerdeck"];
