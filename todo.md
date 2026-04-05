# tech-article-fetcher 実装TODO

spec.mdに基づく実装タスク一覧。毎日Webエンジニア向けに技術記事をキュレーションしてLINEに配信するボット。

## Phase 1: 基盤整備

- [x] `pyproject.toml` の依存関係修正（`anthropic` → `google-generativeai>=0.8.0`）
- [x] `src/` ディレクトリ構成作成（`__init__.py` 含む）
- [x] `src/fetchers/__init__.py` 作成
- [x] `src/selector/__init__.py` 作成
- [x] `src/notifier/__init__.py` 作成
- [x] `.env.example` 作成（`GEMINI_API_KEY`, `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`）
- [x] `requirements.txt` 作成

## Phase 2: データモデル・設定

- [x] `src/models.py`: `Article` / `SelectedArticle` モデルをPydanticで定義
- [x] `src/config.py`: RSSソース14件リスト＋Qiita API設定・定数定義

## Phase 3: フェッチャー実装

- [x] `src/fetchers/rss_fetcher.py`: feedparserで複数RSSフィード並列取得・24時間フィルタ
- [x] `src/fetchers/qiita_fetcher.py`: Qiita APIでトレンド記事取得
- [x] 重複排除ロジック（URLベース、`gemini_selector.deduplicate()`）

## Phase 4: AI選定

- [x] `src/selector/gemini_selector.py`: Gemini API（gemini-2.0-flash）で上位5〜7記事を選定
  - 選定基準: 実用性・新規性・学習価値・多様性
  - 最大3回リトライ（指数バックオフ）

## Phase 5: LINE通知

- [x] `src/notifier/line_notifier.py`: LINE Messaging APIでプッシュ送信
  - メッセージフォーマット: タイトル・URL・選定理由

## Phase 6: オーケストレーション

- [x] `src/main.py`: 全モジュール統合・エントリポイント
  - RSS + Qiita を並列フェッチ → 重複排除 → Gemini選定 → LINE送信

## Phase 7: CI/CD

- [x] `.github/workflows/daily-fetch.yml`: 毎朝8時JST（23:00 UTC）のcronジョブ
  - GitHub Secretsから環境変数を注入
  - `workflow_dispatch` で手動実行も可能

## Phase 8: テスト

- [x] `tests/test_fetchers.py`: RSSフェッチャー・Qiitaフェッチャーのユニットテスト
- [x] `tests/test_selector.py`: Geminiセレクターのユニットテスト（モック使用）
- [x] `tests/test_notifier.py`: LINE通知のユニットテスト（モック使用）

---

## 環境変数（GitHub Secrets / ローカル .env）

| 変数名 | 取得元 |
|--------|--------|
| `GEMINI_API_KEY` | Google AI Studio |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers コンソール |
| `LINE_USER_ID` | LINE Messaging API（送信先ユーザーID）|

## 次のステップ（手動作業）

1. `.env` ファイルに各APIキーを設定（`.env.example` を参考）
2. `pip install -e .` で依存関係インストール
3. `python -m src.main` でローカル実行確認
4. `pytest tests/` でテスト実行
5. GitHub Repository Secrets に3つの変数を登録
6. GitHub Actions の `workflow_dispatch` で手動実行して動作確認
