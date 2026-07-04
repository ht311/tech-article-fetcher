from typing import Any

# RSSフィードのソース一覧。name はメッセージ表示にも使われる。
# ソースを追加・削除したい場合はここだけ編集すればよい。
RSS_SOURCES: list[dict[str, Any]] = [
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
    # 海外公式テックブログ
    {"name": "GitHub Blog", "url": "https://github.blog/feed/"},
    {"name": "AWS Blog", "url": "https://aws.amazon.com/blogs/aws/feed/"},
    {"name": "Cloudflare Blog", "url": "https://blog.cloudflare.com/rss/"},
    # Java 専門（重要ソース: 延長ウィンドウ・ピン留め対象）
    {"name": "Inside.java", "url": "https://inside.java/feed.xml", "important": True},
    {"name": "InfoQ Java", "url": "https://feed.infoq.com/java/", "important": True},
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
QIITA_TAG_QUERY = "stocks:>5"    # タグ別検索の基本クエリ（>10 は最新記事が拾えないため緩和）
QIITA_QUERY = "stocks:>50"       # タグなし（人気記事全般）のクエリ
QIITA_PER_PAGE = 10              # タグ別は件数を抑える（タグ数×10件）

# 使用する Gemini モデル（精度優先・無料枠あり）
GEMINI_MODEL = "gemini-2.5-flash"
# 日次クォータ枯渇時のフォールバックモデル（無料枠あり・flash より RPD 上限が大きい軽量版）
GEMINI_FALLBACK_MODEL = "gemini-2.5-flash-lite"

# 直近何時間の記事を対象にするか
ARTICLE_FETCH_HOURS = 24
# 重要ソース（Java専門・カンファスライド）の取得ウィンドウ
EXTENDED_FETCH_HOURS = 168  # 7日
# カンファスライドの収集ウィンドウ
CONFERENCE_SEARCH_HOURS = 168
# カテゴリ毎にピン確保する重要記事の上限
MAX_PINNED_PER_CATEGORY = 2
# 再送防止のため遡る送信済み履歴の日数
SENT_HISTORY_DEDUP_DAYS = 7

# 大カテゴリ定義（id 順でプロンプト・LINE 送信順序が決まる）
# ASCII キーワードは前後に英数字が続かない位置でのみマッチする（categorizer._kw_match）。
# 短い略語（ecs/rds 等）を追加しても "specs"/"words" に誤爆しない前提のリスト。
CATEGORIES: list[dict[str, Any]] = [
    {
        "id": "backend",
        "name": "バックエンド",
        "keywords": [
            "java", "jdk", "openjdk", "jvm", "graalvm",
            "spring", "springboot", "spring boot",
            "kotlin", "quarkus", "hibernate", "jpa", "jakarta",
            "maven", "gradle",
            "postgres", "postgresql", "mysql", "sql",
            "grpc", "kafka", "redis",
            # "go" 単体は境界マッチでも誤爆過多のため golang のみ
            "golang", "rust",
            "マイクロサービス", "バックエンド",
        ],
    },
    {
        "id": "frontend",
        "name": "フロントエンド",
        "keywords": [
            "react", "next.js", "nextjs", "typescript", "javascript",
            "vue", "nuxt", "svelte", "angular",
            "css", "tailwind", "vite",
            "フロントエンド",
        ],
    },
    {
        "id": "aws",
        "name": "AWS",
        # iam は Azure/GCP 記事にも頻出、sns は日本語でソーシャルメディアの意味が支配的なため除外
        "keywords": [
            "aws", "amazon web services",
            "ec2", "s3", "ecs", "eks", "fargate", "lambda",
            "dynamodb", "rds", "aurora",
            "cloudfront", "cloudformation", "cloudwatch",
            "sqs", "kinesis", "eventbridge", "step functions",
            "bedrock", "sagemaker", "cdk",
        ],
    },
    {
        "id": "management",
        "name": "マネジメント/組織",
        # 「採用」「評価」単体は技術選定・性能評価の文脈で誤爆するため除外
        "keywords": [
            "engineering manager", "エンジニアリングマネージャー",
            "1on1", "組織", "リーダー", "チームビルディング", "マネジメント",
            "scrum", "スクラム", "agile", "アジャイル",
            "テックリード", "tech lead", "okr",
            "心理的安全性", "psychological safety",
            "ふりかえり", "レトロスペクティブ", "retrospective",
            "オンボーディング", "人事評価",
        ],
    },
    {"id": "others", "name": "その他", "keywords": []},
]

# カテゴリごとの最大選定件数（0 件もあり）
SELECT_MAX_PER_CATEGORY = 5
# Gemini に渡す候補記事数の上限（カテゴリごと）
GEMINI_MAX_INPUT_PER_CATEGORY = 25

# Gemini API エラー時のリトライ設定（指数バックオフ）
GEMINI_MAX_RETRIES = 5
GEMINI_RETRY_BASE_WAIT = 2.0  # seconds

# Embedding 基盤
GEMINI_EMBED_MODEL = "gemini-embedding-001"
# これ以上のコサイン類似度を同一トピックとみなす（KV settings.semantic_dedup_threshold で上書き可）
SEMANTIC_DEDUP_THRESHOLD = 0.88
ENABLE_SEMANTIC_DEDUP = True
ENABLE_PREFERENCE_RERANK = True
MAX_EMBED_TEXTS_PER_RUN = 400   # 1実行あたりの埋め込み上限ガード。超過時はフォールバック


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

# SpeakerDeck カテゴリフィード（/c/<category>.atom）
# /trending.atom / /popular.atom はエントリ空のため不使用
SPEAKERDECK_CATEGORIES: list[str] = [
    "programming",
    "science",
    "business",
    "education",
    "design",
]


def default_sources() -> list[dict[str, object]]:
    """RSS_SOURCES / QIITA_TAGS / SPEAKERDECK_CATEGORIES を SourceDef 形式で返す。"""
    from src.core.models import SourceDef  # 循環 import 回避

    sources: list[SourceDef] = []
    for i, s in enumerate(RSS_SOURCES):
        sources.append(SourceDef(
            name=s["name"], type="rss", url=s["url"], enabled=True,
            important=bool(s.get("important", False)),
        ))
    for tag in QIITA_TAGS:
        sources.append(SourceDef(
            name=f"Qiita:{tag}", type="qiita", params={"tag": tag}, enabled=True
        ))
    for cat in SPEAKERDECK_CATEGORIES:
        sources.append(SourceDef(
            name=f"SpeakerDeck:{cat}", type="speakerdeck", params={"category": cat}, enabled=True
        ))
    return [s.model_dump() for s in sources]


def default_category_defs() -> list[dict[str, object]]:
    """CATEGORIES を CategoryDef 形式で返す。"""
    from src.core.models import CategoryDef  # 循環 import 回避

    defs: list[CategoryDef] = []
    for i, c in enumerate(CATEGORIES):
        defs.append(CategoryDef(
            id=c["id"],
            name=c["name"],
            keywords=c.get("keywords", []),
            enabled=True,
            order=i,
        ))
    return [d.model_dump() for d in defs]
