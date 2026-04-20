# ダッシュボード設定画面の UX 改善計画

## Context

- **現状**: `/workspaces/tech-article-fetcher/dashboard/app/settings/page.tsx` の 4 タブ構成（カテゴリ/ソース/パラメータ/キーワード）は、ツールチップ・プレビュー・確認ダイアログがいずれも未実装。
  - 削除 (`✕`) は即時実行（`CategoryEditor.tsx:93`, `SourceEditor.tsx:55`）
  - パラメータスライダーは数値のみで、変更した場合の影響が見えない（`ParamsEditor.tsx`）
  - 保存結果は「✓ 保存しました」のみで、反映タイミングが UI に現れない（`settings/page.tsx:97`）
  - エラーはブラウザ `alert()`（`settings/page.tsx:136,169`）
  - 未保存変更の検知や離脱警告なし
- **問題**: 各操作の結果がクリックしてみないと分からず、破壊的操作（削除・初期化の上書き）もワンクリックで実行される。ユーザーは「この操作をしたらどうなるのか」を把握できない。
- **ゴール**: 操作前に結果を提示する UX 層（説明文・プレビュー・確認ダイアログ・未保存インジケータ）を追加する。見た目はアクセシブルな Radix プリミティブ + Tailwind で統一。

---

## 設計方針

### 依存追加（ユーザー承認済み）

- `@radix-ui/react-tooltip`（ツールチップ）
- `@radix-ui/react-dialog`（確認ダイアログ）

### 再利用プリミティブを新設

`dashboard/app/components/ui/` 配下に汎用コンポーネントを配置し、編集コンポーネントから呼び出す。

| File | 責務 |
|---|---|
| `ui/Tooltip.tsx` | `ℹ️` アイコン + hover/focus で説明文。Radix Tooltip をラップ |
| `ui/ConfirmDialog.tsx` | 破壊的操作の確認モーダル。`variant="destructive" \| "default"` |
| `ui/HelpText.tsx` | ラベル直下の薄字の説明・プレビュー文言。`variant="hint" \| "preview"` |

---

## アーキテクチャ / データ構造

### 未保存変更の検知

`settings/page.tsx` に `original: UserSettings | null` を追加し、初回 fetch 完了時と `save()` 成功時にスナップショットを更新する。

```ts
const isDirty = original !== null &&
  JSON.stringify(original) !== JSON.stringify(settings);
```

- 保存ボタン横に `●` インジケータ（`isDirty === true` の時のみ表示）
- `useEffect` で `beforeunload` を登録（`isDirty` の時だけ `preventDefault`）

### 型・スキーマ変更

なし（`functions/api/_types.ts` の `UserSettings` はそのまま）。純粋にフロントエンドのプレゼンテーション層のみ変更。

---

## 実装ステップ

### Step 1: 依存追加
[ ] `dashboard/package.json` に `@radix-ui/react-tooltip`, `@radix-ui/react-dialog` を追加
[ ] `npm install`

### Step 2: 共通 UI プリミティブを作成
[ ] `dashboard/app/components/ui/Tooltip.tsx` — Radix `Tooltip.Provider/Root/Trigger/Content` をラップ。`children` とは別に `label` prop を受け、トリガーを囲む薄い wrapper に。`ℹ️` 単独用のバリアントも export（`<InfoTooltip text="..." />`）
[ ] `dashboard/app/components/ui/ConfirmDialog.tsx` — Radix `Dialog` をラップ。`open`, `onOpenChange`, `title`, `description`, `confirmLabel`, `cancelLabel`, `onConfirm`, `variant` を受ける。destructive 時は確定ボタンを赤系に
[ ] `dashboard/app/components/ui/HelpText.tsx` — `<p>` の薄字スタイル。variant=`hint`（gray-500, text-xs）/ `preview`（blue-600 bg-blue-50, 枠付き）

### Step 3: `settings/page.tsx` — 未保存状態と保存文言
[ ] `original` state を追加、初回 fetch と `save()` 成功時に同期
[ ] `isDirty` を算出し、保存ボタン横に `<span className="w-2 h-2 rounded-full bg-amber-500" title="未保存の変更があります" />` を条件表示
[ ] `useEffect` で `beforeunload` リスナーを登録（`isDirty` のみ発火）
[ ] 保存直後のラベルを「✓ 保存しました（次回配信バッチから反映）」に変更
[ ] カテゴリ/ソース初期化ボタンを `ConfirmDialog` 経由に変更（`variant="destructive"` で「現在の {対象} 設定を破棄してデフォルトで上書きします」を提示）
[ ] `alert()`（L136, L169）を削除し、失敗時は `HelpText variant="hint"` でインライン表示（`seedError` state を追加して表示切り替え）

### Step 4: `CategoryEditor.tsx`
[ ] `✕` 削除ボタン → `ConfirmDialog`（「カテゴリ『{name}』を削除します。配信履歴は残りますが、今後このカテゴリには記事が配信されません。」）
[ ] `enabled` チェックボックスの右に `<InfoTooltip text="OFFにすると次回配信からこのカテゴリが除外されます" />`
[ ] `↑` `↓` ボタンに `aria-label` / `title` 付与（「上に移動（配信順を変更）」「下に移動」）
[ ] `id` 表示（L89）に `<InfoTooltip text="内部ID。配信記事の分類キーとして使われます" />`
[ ] `KeywordChips` の placeholder を「例: React, TypeScript」に

### Step 5: `SourceEditor.tsx`
[ ] `✕` 削除ボタン → `ConfirmDialog`（「ソース『{name}』を削除します」）
[ ] `enabled` チェックボックスに `<InfoTooltip text="OFFにすると次回配信からこのソースを取得しません" />`
[ ] グループ見出し（rss/qiita/speakerdeck）の右に `<InfoTooltip />` — 各 type の説明（例: qiita は「指定タグの記事を Qiita API から取得」）
[ ] 「+ ソースを追加」ボタンの横に、選択中 type の取得仕様を示す `<HelpText variant="hint" />`

### Step 6: `ParamsEditor.tsx`
[ ] `SliderRow` に `description?: string` と `preview?: string` prop を追加。`preview` は `<HelpText variant="preview">` で描画
[ ] 呼び出し側（`settings/page.tsx` 経由で enabled なカテゴリ数を渡す）で以下を計算して preview に渡す：
  - `max_per_category`: 「有効カテゴリ {M} 件 × 最大 {N} 件 = 1日最大 **{M×N} 記事**」
  - `article_fetch_hours`: 「過去 {N} 時間に公開された記事を対象（{N/24 向き丸め} 日分）」
  - `gemini_max_input_per_category`: 「各カテゴリから最大 {N} 件を Gemini で評価し、上位 `max_per_category` 件を選定」
[ ] `description`（hint）として、各パラメータの目的を 1 行で添える

### Step 7: キーワードタブ
[ ] `settings/page.tsx` の `KeywordList` ラベルを簡潔化、代わりに `<HelpText variant="hint">` で用途と例示：
  - 優先: 「Gemini に『これらを含む記事を優先せよ』と追加指示します。例: React, TypeScript」
  - 除外: 「タイトル・要約にマッチした記事は配信候補から除外します。例: PR, 広告」

### Step 8: 動作確認
[ ] `cd dashboard && npm run dev` でローカル起動、`/settings` を開く
[ ] 各タブで Tooltip / ConfirmDialog / HelpText が正しく表示されるか目視
[ ] 削除・初期化の「キャンセル」「実行」両パスを確認
[ ] 未保存状態でタブ切替・ページ離脱（beforeunload）を確認
[ ] `npm run build` でビルド・型チェックが通る

---

## テスト方針

- ダッシュボードに既存の単体テストはない（`dashboard/` に `*.test.*` なし）ため、手動検証を中心とする
- 回帰観点: `functions/api/settings.ts` の API 契約は変更しないので、バックエンド側テスト（`tests/test_contract.py`）は影響を受けない
- 型安全: `npm run build` で Next の型検査を通す

---

## Out of Scope

- 反映タイミングの恒常バナー（ユーザー選択により除外。保存後トーストに集約）
- shadcn/ui への完全移行
- stats / articles / home ページへの UX 施策
- `ui/` プリミティブのユニットテスト整備（今回は手動検証で可とする）

---

## 不明点・確認事項

[Q1] パラメータタブの「1日最大 M×N 記事」プレビューの **M（有効カテゴリ数）** は `category_defs.filter(c => c.enabled).length` で算出する想定でよいか？（カテゴリ未設定時は fetcher デフォルトを使う旨を注記する必要あり）
[A1] y

[Q2] `ConfirmDialog` の確定ボタン色は既存の赤系 (`text-red-400 hover:text-red-600`, `CategoryEditor.tsx:93`) と合わせて `bg-red-600 hover:bg-red-700 text-white` でよいか？
[A2] y
