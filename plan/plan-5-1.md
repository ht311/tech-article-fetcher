# dashboard / fetcher 設定ベース化 フェーズ1 — ダッシュボード + Cloudflare 側 (plan-5-1)

## Context

### 現状
- fetcher の設定は大半が `src/config.py` のモジュール定数としてハードコードされている。
- ダッシュボード経由で変えられるのは `UserSettings`(`src/models.py:37-50`) に入る 5 項目のみ:
  - `categories` (ON/OFF)、`sources_enabled` (ON/OFF のみ。URL は config 側)、`max_per_category`、`exclude_keywords`、`include_keywords`。
- 設定の永続化は Cloudflare KV の `settings` キー 1 つ。Python と TS で型が二重定義(`src/models.py` と `dashboard/functions/api/_types.ts`)、手動同期。
- ダッシュボードの `ALL_SOURCES`(`dashboard/app/settings/page.tsx:21-29`) が Python 側フェッチャーのソース名と文字列で二重管理。

### 問題
1. 新しい RSS ソースを足す・カテゴリを増やすのに毎回デプロイが必要。
2. ソース名・カテゴリ ID が Python / TS / UI の 3 箇所で手動同期。ドリフトリスク。
3. `UserSettings.sources_enabled` は `{name: bool}` dict のみなので、UI からソース URL を持てない。
4. `CATEGORIES` のキーワードを調整したいが config を触らないといけない。

### ゴール (このフェーズ)
- スキーマを v2 に拡張し、ソース一覧・カテゴリ定義・主要パラメータを KV に保存できるようにする。
- ダッシュボード UI でこれらを編集・保存できる。
- **fetcher 側は未変更のまま動作し続ける**（後方互換必須）。plan-5-2 で fetcher が v2 を読むようになる。

---

## 設計方針

- KV を継続使用（D1 は導入しない）。設定は構造化 JSON 1 件で十分扱える規模。
- 既存の `settings` キーに **後方互換でフィールド追加**（v1 フィールドは残す）。
- 型定義は当面手動同期を継続。
- 認証は現状の `DASHBOARD_SECRET` Basic Auth を継続（スコープ外）。

---

## スキーマ拡張 (`UserSettings` v2)

`src/models.py:37` と `dashboard/functions/api/_types.ts:15` を同時に更新する。

```ts
// 追加する型
interface SourceDef {
  name: string;         // 一意キー（例: "Zenn", "Reddit r/aws"）
  type: "rss" | "qiita" | "speakerdeck" | "hackernews" | "reddit" | "devto";
  url?: string;         // rss の場合必須
  params?: Record<string, string | number | string[]>;  // 例: {tag: "typescript"}, {subreddit: "aws"}
  enabled: boolean;
}

interface CategoryDef {
  id: string;           // "backend" 等
  name: string;         // 表示名
  keywords: string[];   // 分類 & プロンプト用
  enabled: boolean;
  order: number;        // LINE 送信順
}

// UserSettings に追加 (全て optional)
interface UserSettings {
  // v1 互換フィールド (deprecated だが読み書き継続)
  categories: Record<string, boolean>;
  sources_enabled: Record<string, boolean>;
  max_per_category: number;
  exclude_keywords: string[];
  include_keywords: string[];

  // v2 新フィールド (未設定時は fetcher が config デフォルトを使用)
  sources?: SourceDef[];
  category_defs?: CategoryDef[];
  article_fetch_hours?: number;        // default 24
  gemini_max_input_per_category?: number;  // default 25
  schema_version?: 1 | 2;
}
```

---

## 実装ステップ

### Step 1: 型定義拡張 (`src/models.py` + `dashboard/functions/api/_types.ts`)
- [ ] `src/models.py`: `SourceDef` / `CategoryDef` を追加。`UserSettings` に v2 optional フィールドを追加。
- [ ] `dashboard/functions/api/_types.ts`: 同内容を追加。`DEFAULT_SETTINGS` は v1 のまま。

### Step 2: `src/config.py` に defaults エクスポート関数を追加
- [ ] `default_sources() -> list[SourceDef]`: `RSS_SOURCES` / `QIITA_TAGS` / `SPEAKERDECK_CATEGORIES` を統合して返す。
- [ ] `default_category_defs() -> list[CategoryDef]`: `CATEGORIES` を `CategoryDef` に変換して返す。
- **既存定数は消さない**（plan-5-2 で fetcher が移行するまで現状維持）。

### Step 3: API バリデーション強化 (`dashboard/functions/api/settings.ts`)
- [ ] PUT ハンドラのバリデーションを拡張:
  - `sources[].name` の重複禁止
  - `sources[].type` の許可値チェック
  - `sources[].type === "rss"` かつ `url` が空なら 400
  - `category_defs[].id` の重複禁止
  - `article_fetch_hours` は 1-168 の範囲
  - `gemini_max_input_per_category` は 5-50 の範囲
- [ ] vitest を導入し、バリデーション関数の単体テストを追加。

### Step 4: ダッシュボード UI 再設計 (`dashboard/app/settings/page.tsx`)
- [ ] 現状の単純縦列を **タブ構成** に再編。
- [ ] コンポーネントを `dashboard/app/components/` に分割（現在空ディレクトリ）:
  - `CategoryEditor.tsx`: カテゴリ追加/削除、name 編集、keywords 編集(Chip 入力)、ON/OFF、並び替え
  - `SourceEditor.tsx`: type 別グループ表示、URL 編集、params 編集、新規追加、削除、ON/OFF
  - `ParamsEditor.tsx`: `max_per_category`, `article_fetch_hours`, `gemini_max_input_per_category` のスライダー/入力
- [ ] `ALL_SOURCES` ハードコード(L21-29) を廃止し `settings.sources` から動的生成。
- [ ] PUT 時に v2 フィールドが空なら defaults を自動で埋めて KV に書く（透過的マイグレーション）。

### Step 5: README 更新 (`README.md:488-513`, `L37-45`)
- [ ] 設定スキーマ v2 の説明と v1→v2 マイグレーション手順を追記。

---

## テスト方針

- `src/models.py` の型拡張: 既存 `tests/test_settings.py` が壊れないこと(後方互換確認)。
- API バリデーション: バリデーション関数を純関数に切り出して手動確認（フレームワーク追加は別検討）。
- UI: `npm run dev` でローカル確認、v2 保存 → リロードで保持されることを検証。
- **旧 fetcher(未変更)を動かしても v1 フィールドは従来通り機能すること** をローカルで確認。

---

## 検証

1. `pytest tests/ -v` グリーン（Python 型変更で既存テストが壊れないこと）
2. `cd dashboard && npm run dev` → `/settings` で v2 セクションが編集可能、保存後リロードで保持
3. `/api/settings` GET で保存された JSON が期待形状
4. `python -m src.main` が v2 フィールドを無視して正常に動作すること（fetcher 未変更段階）

---

## 不明点・確認事項

[Q1] **スコープ**: `article_fetch_hours` と `gemini_max_input_per_category` を v2 に含めることに合意か？また Gemini モデル名 (`GEMINI_MODEL`) もここで追加するか？
[A1] 合意

[Q2] **未配線 fetcher (HN / Reddit / dev.to)**: `SourceDef.type` の選択肢として UI に出すか（有効化は plan-5-2 だが、型だけ入れておく）？ それとも dead code として削除するか？
[A2] dead code として削除

[Q3] **v1 → v2 マイグレーション**: 「v2 化ボタンを押させる（案α）」でよいか？ それとも PUT 時に透過的に昇格させる（案β）？
[A3] ユーザーが何もしないことを最優先

[Q4] **ダッシュボード API テスト**: バリデーションロジックが複雑化するため vitest を導入して最低限テストを書くことを推奨。入れる？
[A4] 入れる
