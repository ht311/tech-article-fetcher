# Dashboard — Tech Dispatch

tech-article-fetcher のモバイルダッシュボード。新聞風 **Press** デザイン（iPhone ファースト）。

## 技術スタック

| 項目 | 内容 |
|---|---|
| フレームワーク | Next.js (App Router) |
| スタイリング | Tailwind CSS v4 |
| フォント | Newsreader (serif / 見出し)・Noto Sans JP (sans / 本文)・Geist Mono (mono / 数値) |
| ランタイム | Cloudflare Pages + Pages Functions |

## 画面構成

| タブ | 説明 |
|---|---|
| ホーム | マストヘッド・統計ストリップ・リード記事ヒーロー・番号付き記事リスト |
| 過去記事 | 今日/昨日/すべてフィルタ・日付グループ別番号付きリスト・ミニ反応ボタン |
| 統計 | KPI 2×2グリッド・Good/Bad 比率バー・カテゴリ別配信バー |
| 設定 | 配信時刻・カテゴリ ON/OFF トグル・学習フィードバック統計 |

## デザイントークン

`app/globals.css` の `@theme` ブロックで定義。

| トークン | 用途 |
|---|---|
| `--color-press-bg` `#f8f6f1` | ページ背景（ウォームペーパー） |
| `--color-press-ink` `#1c1a17` | 主テキスト |
| `--color-press-accent` `#b1402e` | アクティブ状態・下線（テラコッタ赤） |
| `--color-press-good` `#0a7d5a` | 👍 Good 状態（ダークグリーン） |
| `--color-cat-{backend,frontend,aws,management}` | カテゴリ別カラー |

## ディレクトリ構成

```
app/
├── layout.tsx            # BottomTabBar 込みのルートレイアウト
├── globals.css           # Press デザイントークン + Tailwind v4 @theme
├── page.tsx              # ホーム画面
├── articles/page.tsx     # 過去記事画面
├── stats/page.tsx        # 統計画面
├── settings/page.tsx     # 設定画面
├── components/
│   ├── BottomTabBar.tsx  # 固定ボトムタブナビゲーション
│   ├── icons/
│   │   └── TabIcons.tsx  # SVG ライン アイコン (Home/Archive/Stats/Settings)
│   └── ...               # 既存コンポーネント（ArticleCard, CategorySection 等）
└── lib/
    ├── pressColors.ts    # カテゴリ色・絵文字・グラデーション ユーティリティ
    └── ...               # ratings, types, useCategories 等
```

## 開発

```bash
pnpm dev        # 開発サーバー
pnpm lint       # Biome lint
pnpm typecheck  # TypeScript 型検査
pnpm test       # Vitest
```
