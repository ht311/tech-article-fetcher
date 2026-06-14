# CI 改善の実装計画 (plan-15)

## Context

`.github/workflows/` の CI 構成を改善する。調査の結果、見過ごせない問題が複数判明した。

- **【重大】auto-merge がテストをゲートしていない**
  `auto-merge.yml` / `dependabot-auto-merge.yml` は `workflow_run` で `"Static Analysis"`(`lint.yml`)の成功完了をトリガにマージする。しかし `lint.yml` は ruff + mypy + biome + tsc のみで、**pytest も dashboard の vitest も実行しない**。`workflow_run.conclusion` は当該 1 workflow の結果しか見ないため、**テストが落ちている PR が自動マージされ得る**。
- **大量の重複** — Python の `ruff`+`mypy` が `lint.yml`(python ジョブ)と `python-ci.yml` の両方で、TS の `biome`+`tsc` が `lint.yml`(typescript ジョブ)と `dashboard-ci.yml` の両方で実行されている。`lint.yml` は実質的に `python-ci.yml` ∪ `dashboard-ci.yml` のサブセットで完全に冗長。
- **pip キャッシュ無し** — `python-ci.yml` / `type-drift.yml` が毎回 `pip install -e ".[dev]"` をノーキャッシュで実行。
- **concurrency 無し** — どの PR workflow も古い実行をキャンセルせず、連続 push で無駄に走り続ける。
- **type-drift の paths フィルタ + 必須チェック問題** — `type-drift.yml` は paths フィルタ運用のため、対象パスを変更しない PR では実行されない。必須チェックにすると "Expected — Waiting for status" で PR がブロックされ得る。pip キャッシュも無い。

**ゴール:** 重複を排除し、テストを含む全 CI 通過を自動マージの条件にし、キャッシュ/concurrency で高速化する。ユーザ選択により、ワークフローは **python-ci / dashboard-ci / type-drift の分離を維持**し、auto-merge は **GitHub ネイティブ auto-merge** に切り替えてゲートを修正する。カバレッジ計測は今回スコープ外。

---

## 設計方針

### auto-merge のゲート修正: GitHub ネイティブ auto-merge

`workflow_run` ハックは「1 workflow の結果しか見られない」構造的欠陥がある。分離ワークフローを維持したまま「全チェック通過」を条件にする最も堅牢な手段は、GitHub の **ネイティブ auto-merge**(`gh pr merge --auto`)。

- PR 作成時に `gh pr merge --auto --squash` で auto-merge を「有効化」するだけ。
- 実際のマージは GitHub が **branch protection の必須ステータスチェック全通過 + mergeable** を満たした時点で自動実行する。
- main は既に保護ブランチ(`CLAUDE.md`)。必須チェックに python-ci / dashboard-ci / type-drift の各ジョブを登録すれば、テスト失敗時はマージされない。

> **重要な前提:** 必須ステータスチェックが未設定のまま `--auto` を有効化すると、CI 開始前に mergeable になった瞬間マージされてしまい**かえって危険**。よって「必須チェック登録」(Step 7)は本変更とセットで必須。

---

## 実装ステップ

### Step 1: `lint.yml` を削除
[ ] `lint.yml`("Static Analysis")を削除。中身は `python-ci.yml`(ruff+mypy+pytest)と `dashboard-ci.yml`(biome+tsc+tests)に完全に内包されており冗長。auto-merge のトリガ元でもあるため、Step 5/6 とセットで実施。

### Step 2: `python-ci.yml` — キャッシュ・concurrency・権限
[ ] トップに最小権限と concurrency を追加:
```yaml
permissions:
  contents: read
concurrency:
  group: python-ci-${{ github.ref }}
  cancel-in-progress: true
```
[ ] `actions/setup-python` に pip キャッシュを追加:
```yaml
      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: pyproject.toml
```
[ ] ジョブ名 `Python (ruff + mypy + pytest)` は必須チェック名になるため変更しない。

### Step 3: `dashboard-ci.yml` — concurrency・権限
[ ] 同様に `permissions: contents: read` と concurrency(`group: dashboard-ci-${{ github.ref }}`)を追加。pnpm キャッシュは既存(`cache: "pnpm"`)。
[ ] 末尾の `Upload test results` ステップの `path:` が `dashboard/test-results || ... || ''` という不正な式(`||` はシェルでなく YAML 文字列)。vitest はファイル出力していないため、このアーティファクトアップロードは削除する。
[ ] ジョブ名 `TypeScript (biome + typecheck + tests)` は変更しない。

### Step 4: `type-drift.yml` — 常時実行化 + キャッシュ
[ ] `on:` の `paths:` フィルタを削除し、push(main)/ pull_request で常時実行する。これにより安定した必須チェックにできる(paths フィルタ + 必須チェックのブロック問題を回避)。
[ ] `permissions: contents: read` と concurrency を追加。
[ ] pip キャッシュ(Step 2 と同形)、pnpm キャッシュ(既存)を有効化。
[ ] `check-drift` ジョブに `name:` を付与(例 `Type Drift`)し必須チェック名を固定。
[ ] drift 検出時のメッセージを明確化(`git diff --exit-code` 失敗時に「`python scripts/gen_types.py` を実行して再コミットせよ」と出力)。

### Step 5: `auto-merge.yml` — ネイティブ auto-merge 化(非 bot PR)
[ ] `workflow_run` トリガを廃止し、`pull_request`(`types: [opened, reopened, synchronize, ready_for_review]`)に変更。
[ ] 非 bot 著者の PR に対し `gh pr merge --auto --squash "$PR_URL"` を実行して auto-merge を有効化:
```yaml
on:
  pull_request:
    types: [opened, reopened, synchronize, ready_for_review]
permissions:
  contents: write
  pull-requests: write
jobs:
  enable-automerge:
    if: ${{ !endsWith(github.event.pull_request.user.login, '[bot]') }}
    runs-on: ubuntu-latest
    steps:
      - name: Enable auto-merge
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PR_URL: ${{ github.event.pull_request.html_url }}
        run: gh pr merge --auto --squash "$PR_URL"
```

### Step 6: `dependabot-auto-merge.yml` — ネイティブ auto-merge 化(dependabot)
[ ] 同様に `pull_request` トリガへ変更し、`github.event.pull_request.user.login == 'dependabot[bot]'` のときに `gh pr merge --auto --squash` を実行。
[ ] (任意・要相談)`dependabot/fetch-metadata` で patch/minor のみ自動マージに絞る案 → 既存は全 dependabot PR を自動マージしているため、今回は挙動維持(全 dependabot を auto-merge)。

### Step 7: リポジトリ設定 — auto-merge 許可 + 必須チェック登録(共有状態の変更)
> ここは**リポジトリ設定の変更**なので、実装フェーズで実行前に明示確認する。
[ ] `gh api -X PATCH repos/{owner}/{repo} -f allow_auto_merge=true` で auto-merge を許可。
[ ] main の branch protection に必須ステータスチェックを登録:
  - `Python (ruff + mypy + pytest)`
  - `TypeScript (biome + typecheck + tests)`
  - `Type Drift`
  `gh api -X PATCH repos/{owner}/{repo}/branches/main/protection/required_status_checks` 等を使用。
[ ] auto-merge を有効化するワークフロー自体は必須チェックに含めない。

---

## テスト方針

- `actionlint`(あれば)で全 workflow YAML を静的検査。なければ YAML 構文を目視 + `python -c "import yaml; ..."` で parse 確認。
- テスト用ブランチ → ダミー PR を作成し、以下を確認:
  - python-ci / dashboard-ci / type-drift が走り、キャッシュがヒットする(2 回目以降)。
  - わざとテストを失敗させた PR が **auto-merge されない**ことを確認(ゲート修正の検証)。
  - 全 CI 通過時に auto-merge が発火しマージされること。
- 連続 push で古い run が `cancel-in-progress` でキャンセルされること。

---

## 不明点・確認事項

[Q1] Step 7 の必須ステータスチェック登録を、私が `gh api` で設定して良いか? それとも手順だけ提示してユーザ自身が GitHub UI で設定するか?(リポジトリ設定変更のため)
[A1] y

[Q2] dependabot の自動マージは現状どおり「全 dependabot PR」を対象で良いか? それとも patch/minor のみに絞るか?
[A2] y

[Q3] このプランは承認後 `plan/plan-15.md` として保存する(/plan スキルの慣習)。問題ないか?
[A3] y
