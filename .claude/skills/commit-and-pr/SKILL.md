---
name: commit-and-pr
description: >
  作業完了後にコミット・push・PR起票を行うスキル。
  「作業が完了したら」「コミットして」「PRを起票して」「push して PR 作って」
  といった指示、または実装タスクの仕上げとして積極的に使う。
  doc-sync で README を更新してからコミットし、PR を起票する。
---

# commit-and-pr: コミット・push・PR起票

## 目的

実装完了後にドキュメントを更新し、コミット・push・PR起票まで一気通貫で行う。

---

## ワークフロー

### Step 1: CI 相当のチェックをローカルで通す

**PR を切る前に、CI が走らせるチェックを変更領域に応じてローカルで全て通す。**
これを省くと CI でコケて自動マージが止まる。

| 変更領域 | 実行するチェック |
|---|---|
| `src/` / `tests/` | `pytest tests/ -v` + `ruff check src/ tests/` + `mypy src/` |
| `dashboard/` | `cd dashboard && pnpm lint && pnpm typecheck && pnpm test` |
| `.github/workflows/` | 該当ワークフローのトリガー条件（paths / branches）を目視確認 |

失敗したら修正してから次へ進む（`fix-ci` スキル参照）。

### Step 2: doc-sync でドキュメントを更新する

コミット前に必ず `doc-sync` スキルを実行し、README.md をコードの変更に合わせて更新する。

### Step 3: ブランチを確認する

```bash
git branch --show-current
git status --short
```

- `main` ブランチに居る場合は作業ブランチを作成してから進める
- main は保護ブランチのため直接プッシュ不可

```bash
git switch -c <branch-name>
```

### Step 4: コミットする

```bash
git add <変更ファイル>
git commit -m "<message>"
```

- コミットメッセージは変更内容を端的に表す日本語または英語で
- `git add .` は使わず、関係するファイルだけを明示的に指定する

### Step 5: push する

```bash
git push -u origin <branch-name>
```

### Step 6: PR を起票する

```bash
gh pr create --title "<title>" --body "<body>"
```

- タイトルは変更内容を一行で表す
- ボディには変更の背景・内容・確認方法を記載する

### Step 7: PR 起票後に検証する

**起票して終わりにしない。** 以下を確認してから完了報告する:

```bash
gh pr diff <pr-number>            # 意図した変更が全て入っているか（push 漏れ検知）
gh pr checks <pr-number> --watch  # CI が通るまで見届ける
```

- diff に入っているはずの変更が無い場合: コミット漏れ・push 漏れを疑い、修正して push し直す
- CI が落ちた場合: `fix-ci` スキルで対応する

---

## 注意点

- **doc-sync を省略しない** — コミット前に必ず README の同期を確認する
- **main へ直接プッシュしない** — 必ずブランチ経由で PR を通す
- **作業ブランチは main の最新を取り込んでから作成する**

```bash
git switch main && git pull && git switch -c <branch-name>
```
