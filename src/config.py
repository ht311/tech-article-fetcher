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

# 優先検索トピック（Gemini 選定基準・Qiita タグ検索・Reddit サブレディットに反映される）
PREFERRED_TOPICS: list[str] = [
    "Java", "Spring Boot", "PostgreSQL",
    "TypeScript", "React", "Next.js",
    "AWS",
    "スクラム", "Scrum",
    "エンジニアリングマネージャー", "Engineering Manager",
]

# Qiita API
QIITA_API_URL = "https://qiita.com/api/v2/items"
# トピックタグ別検索用（各タグで並列リクエストを行う）
QIITA_TAGS: list[str] = [
    "Java", "SpringBoot", "PostgreSQL",
    "TypeScript", "React", "Next.js",
    "AWS", "スクラム",
]
QIITA_TAG_QUERY = "stocks:>10"   # タグ別検索の基本クエリ
QIITA_QUERY = "stocks:>50"       # タグなし（人気記事全般）のクエリ
QIITA_PER_PAGE = 10              # タグ別は件数を抑える（タグ数×10件）

# 使用する Gemini モデル（無料枠あり・高速）
GEMINI_MODEL = "gemini-2.0-flash"

# 直近何時間の記事を対象にするか
ARTICLE_FETCH_HOURS = 24

# Gemini に選ばせる記事数の範囲
SELECT_MIN = 5
SELECT_MAX = 7

# Gemini に渡す記事数の上限（トークン削減のためプリフィルタリング）
GEMINI_MAX_INPUT_ARTICLES = 25

# Gemini API エラー時のリトライ設定（指数バックオフ）
GEMINI_MAX_RETRIES = 5
GEMINI_RETRY_BASE_WAIT = 2.0  # seconds

# LINE Quick Reply の制約（最大13アイテム = 6記事×2ボタン）
MAX_ARTICLES_WITH_QUICKREPLY = 6

# Hacker News API（Firebase REST API、認証不要）
HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
HN_FETCH_COUNT = 30   # 上位N件をフェッチしてフィルタする
HN_MIN_SCORE = 100    # スコアのしきい値

# Reddit JSON API（認証不要・User-Agent必須）
REDDIT_BASE_URL = "https://www.reddit.com/r/{subreddit}/hot.json"
REDDIT_SUBREDDITS = [
    "java", "SpringBoot",
    "typescript", "reactjs", "nextjs",
    "aws",
    "agile",
    "ExperiencedDevs",
]
REDDIT_MIN_SCORE = 500
REDDIT_PER_PAGE = 25

# dev.to API（認証不要）
DEVTO_API_URL = "https://dev.to/api/articles"
DEVTO_TOP_PERIOD = 7    # 過去N日のトレンド
DEVTO_PER_PAGE = 20
