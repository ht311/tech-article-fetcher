# RSSフィードのソース一覧。name はメッセージ表示にも使われる。
# ソースを追加・削除したい場合はここだけ編集すればよい。
RSS_SOURCES: list[dict[str, str]] = [
    # 日本語技術記事
    {"name": "Zenn", "url": "https://zenn.dev/feed"},
    {"name": "Qiita人気記事", "url": "https://qiita.com/popular-items/feed"},
    {"name": "はてブIT", "url": "https://b.hatena.ne.jp/hotentry/it.rss"},
    {"name": "noteテック", "url": "https://note.com/hashtag/tech?format=rss"},
    # 企業テックブログ
    {"name": "メルカリ", "url": "https://engineering.mercari.com/blog/feed.xml"},
    {"name": "サイバーエージェント", "url": "https://developers.cyberagent.co.jp/blog/feed/"},
    {"name": "DeNA", "url": "https://engineering.dena.com/blog/index.xml"},
    {"name": "SmartHR", "url": "https://tech.smarthr.jp/feed"},
    {"name": "LayerX", "url": "https://tech.layerx.co.jp/feed"},
    # 海外技術記事
    {"name": "dev.to", "url": "https://dev.to/feed"},
    {"name": "GitHub Blog", "url": "https://github.blog/feed/"},
    {"name": "AWS Blog", "url": "https://aws.amazon.com/blogs/aws/feed/"},
    {"name": "Cloudflare Blog", "url": "https://blog.cloudflare.com/rss/"},
    {"name": "Vercel Blog", "url": "https://vercel.com/blog/rss.xml"},
]

# Qiita API（ストック数50以上の記事を対象にする）
QIITA_API_URL = "https://qiita.com/api/v2/items"
QIITA_QUERY = "stocks:>50"
QIITA_PER_PAGE = 20

# 使用する Gemini モデル（無料枠あり・高速）
GEMINI_MODEL = "gemini-2.0-flash"

# 直近何時間の記事を対象にするか
ARTICLE_FETCH_HOURS = 24

# Gemini に選ばせる記事数の範囲
SELECT_MIN = 5
SELECT_MAX = 7

# Gemini API エラー時のリトライ設定（指数バックオフ）
GEMINI_MAX_RETRIES = 3
GEMINI_RETRY_BASE_WAIT = 2.0  # seconds
