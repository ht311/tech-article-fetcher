# アーキテクチャ図 + スクリーンショットを GitHub Pages で公開 (plan-11)

## Context

- **現状**: README のアーキテクチャは ASCII ツリーのみ。`docs/` は README に記述があるが実体なし。画像・draw.io ファイル未配置。GitHub Pages 用ワークフロー未導入（Cloudflare Pages のみ）
- **問題**: アーキテクチャが視覚的に伝わらない。ダッシュボードの見た目が外から分からない
- **ゴール**: draw.io アーキテクチャ図 + Dashboard スクリーンショット 4 枚を `docs/` に置き、`https://ht311.github.io/tech-article-fetcher/` でショーケースサイトとして公開

---

## 採用方針

- **GitHub Pages**: `docs/index.html` (プレーン HTML) を `actions/deploy-pages` でデプロイ。Dashboard API 依存なし
- **SVG 生成**: CI で `jgraph/drawio-export-action` → `architecture.drawio` から `architecture.svg` を生成、Pages artifact に含める
- **スクリーンショット**: Playwright (`page.route()` でAPIモック) でローカル撮影後コミット
- **README**: 画像を冒頭に追加、ASCII ツリーは `<details>` で折りたたみ

---

## ディレクトリ構成

```
docs/
├── index.html              # ショーケースページ
├── style.css               # 最小 CSS
├── architecture.drawio     # draw.io ソース
└── screenshots/
    ├── home.png
    ├── articles.png
    ├── stats.png
    └── settings.png

dashboard/scripts/
├── screenshot.mts          # Playwright撮影スクリプト
└── fixtures/
    ├── settings.json
    ├── stats.json
    ├── articles.json
    └── preferences.json

.github/workflows/pages.yml # GitHub Pages デプロイワークフロー
```

---

## 実装ステップ

- [x] `plan/plan-11.md` を作成
- [x] `docs/architecture.drawio` を作成
- [x] `docs/index.html` + `docs/style.css` を作成
- [x] `dashboard/scripts/fixtures/*.json` を作成
- [x] `dashboard/scripts/screenshot.mts` を作成
- [x] `dashboard/package.json` を更新（playwright + tsx + scripts）
- [x] `.github/workflows/pages.yml` を作成
- [x] `README.md` を更新（画像追加 + ASCII 折りたたみ）

---

## テスト方針

1. `docs/index.html` をブラウザで直接開いて画像が表示されることを確認
2. `npm run dev` 起動後 `npm run screenshots` でスクショが `docs/screenshots/` に生成されることを確認
3. Push 後 GitHub Actions で pages ジョブが緑になることを確認
4. `https://ht311.github.io/tech-article-fetcher/` でアクセスできることを確認
   - 事前に Repository Settings → Pages → Source を **GitHub Actions** に設定すること
