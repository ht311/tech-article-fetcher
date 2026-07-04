---
name: fix-ci
description: >
  GitHub Actions の CI 失敗を修正するスキル。
  「fix + Actions の URL」「CI がコケた」「このワークフロー落ちてる」といった指示や、
  CI のエラーログが貼り付けられたときに積極的に使う。
  gh CLI で失敗ログを取得して原因を特定し、ローカルで再現・修正・検証してから push する。
---

# fix-ci: CI 失敗の修正

## 目的

GitHub Actions の失敗を「ログ取得 → ローカル再現 → 修正 → ローカル検証 → push」で
一気通貫に解消する。CI 上での試行錯誤（push しては落ちる）を避ける。

---

## ワークフロー

### Step 1: 失敗ログを取得する

URL やログの貼り付けから run / PR を特定し、失敗ステップだけを読む:

```bash
gh run view <run-id> --log-failed        # URL 末尾の runs/<run-id> から
gh pr checks <pr-number>                 # PR 単位で失敗しているジョブを確認
gh run list --workflow=<file>.yml -L 5   # どの run か不明な場合
```

ユーザーがログを貼ってくれた場合も、前後の文脈が必要なら gh で全文を取る。

### Step 2: ローカルで再現する

失敗したジョブに対応するコマンドをローカルで実行し、同じエラーを再現する:

| CI ジョブ | ローカル再現コマンド |
|---|---|
| Python テスト | `pytest tests/ -v` |
| Python lint | `ruff check src/ tests/` |
| Python 型検査 | `mypy src/` |
| dashboard lint | `cd dashboard && pnpm lint` |
| dashboard 型検査 | `cd dashboard && pnpm typecheck` |
| dashboard テスト | `cd dashboard && pnpm test` |
| dashboard ビルド | `cd dashboard && pnpm build` |

再現しない場合は環境差分（Python / node / pnpm のバージョン、キャッシュ、secrets）を疑う。

### Step 3: 原因を特定して修正する

- テストの失敗: まず実装のバグを疑い、テストの期待値を安易に書き換えない
- 依存関係の失敗: lockfile とマニフェストの不整合、minimumReleaseAge 制約を確認
- secrets / 権限の失敗: **Claude からは設定できない**。必要な secret 名・PAT 権限を
  具体的に提示してユーザーに登録を依頼する

### Step 4: ローカルで全チェックを通す

修正した領域だけでなく、CI が走らせる一式をローカルで通してから push する
（1 つ直して別のチェックで落ちるのを防ぐ）。

### Step 5: push する

- 既存 PR のブランチが落ちている場合: そのブランチにコミットして push
- 新規の修正の場合: `commit-and-pr` スキルで PR を起票
- push 後は CI の結果を確認して完了報告する:

```bash
gh pr checks <pr-number> --watch
```

---

## 注意点

- **CI 上で試行錯誤しない** — 必ずローカルで再現・検証してから push する
- **ワークフロー YAML の修正時は該当ワークフローが本当に走る条件（paths / branches）も確認する**
  — 「今まで全然走ってなかった」事故の防止
- 修正できない・判断が要る場合は、原因の仮説と選択肢を短くまとめて早めにユーザーに聞く
