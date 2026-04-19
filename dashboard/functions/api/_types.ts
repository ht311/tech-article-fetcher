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

export interface UserSettings {
  categories: Record<string, boolean>;
  sources_enabled: Record<string, boolean>;
  max_per_category: number;
  exclude_keywords: string[];
  include_keywords: string[];
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
