// KV キー名の唯一の定義場所 (TypeScript 側)
// 値は src/core/kv_keys.py と一致させること。tests/test_contract.py で検証される。

export const KV_PREFERENCES = "preferences";
export const KV_LAST_ARTICLES = "last_articles";
export const KV_SETTINGS = "settings";
export const KV_DEFAULT_SETTINGS = "default_settings";
export const KV_ARTICLE_INDEX = "article_index";

export const articleHistoryKey = (date: string): string => `articles:${date}`;
