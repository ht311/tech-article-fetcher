# KV キー名の唯一の定義場所 (Python 側)
# dashboard 側の対応: dashboard/functions/api/_kv_keys.ts
# Worker 側の対応: infrastructure/cloudflare/index.js (コメント参照)

KV_PREFERENCES = "preferences"
KV_LAST_ARTICLES = "last_articles"
KV_SETTINGS = "settings"
KV_DEFAULT_SETTINGS = "default_settings"
KV_ARTICLE_INDEX = "article_index"
KV_ARTICLE_HISTORY_PREFIX = "articles:"
