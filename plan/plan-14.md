# 日次フェッチの定時起動化 (Cloudflare Cron Trigger) — plan-14

## Context

**問題**: `daily-fetch.yml` は `cron: "15 23 * * *"`（JST 8:15）を指定していたが、
GitHub Actions の `schedule` イベントは混雑時に大きく遅延する。実測で**毎日40〜70分遅延**しており、
LINE 通知が JST 9:00〜9:25 に届いていた（例: run 27483331477 は createdAt `2026-06-14T00:20:04Z` = JST 9:20）。

| 日付 | 起動(UTC) | 指定(23:15)からの遅延 |
|------|-----------|------|
| 06-14 | 00:20 | 65分 |
| 06-13 | 00:15 | 60分 |
| 06-04 | 00:26 | 71分 |
| 06-05 | 00:00 | 45分 |

**原因**: GitHub Actions の `schedule` はベストエフォートで、毎時付近の高負荷時間帯はキュー待ちが長い。
cron の前倒しでは遅延の±幅が大きく、目標の「8:00〜8:30」を保証できない。

**ゴール**: LINE 通知を確実に JST 8:15 前後に届ける。

**方針**: 既存の Cloudflare Worker（`infrastructure/cloudflare/index.js`、Terraform 管理）に
**Cron Trigger** を追加し、定時に GitHub の `workflow_dispatch` API を叩いて `daily-fetch.yml` を起動する。
`workflow_dispatch` 起動は `schedule` の混雑遅延を受けず数分以内に走るため、定時性が保証される。

```
Cloudflare Cron (23:15 UTC = 8:15 JST, 定時) ── scheduled()
   └─ fetch → POST /repos/ht311/tech-article-fetcher/actions/workflows/daily-fetch.yml/dispatches
        └─ daily-fetch run 起動（遅延ほぼ無し、実行 ~95秒）
             └─ LINE 通知 ≈ 8:17 JST
```

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `infrastructure/cloudflare/index.js` | `dispatchWorkflow()` 関数と `scheduled` ハンドラを追加 |
| `infrastructure/terraform/main.tf` | `GITHUB_TOKEN` Secret バインドと `cloudflare_workers_cron_trigger` リソースを追加 |
| `infrastructure/terraform/variables.tf` | `github_token` 変数を追加 |
| `infrastructure/terraform/terraform.tfvars.example` | `github_token` の雛形を追記 |
| `.github/workflows/daily-fetch.yml` | `schedule:` ブロックを削除（二重起動防止）、`workflow_dispatch:` のみに変更 |
| `README.md` | アーキ図とワークフロー説明を実態に合わせ更新 |

---

## 必要な手作業（コードでは完結しない）

1. **GitHub PAT の発行**: Fine-grained PAT、対象リポジトリ `ht311/tech-article-fetcher`、
   権限 `Actions: Read and write`。
   発行URL: https://github.com/settings/tokens?type=beta
   → これを `terraform.tfvars` の `github_token` に設定。

2. **`terraform apply`**: Worker 更新・Secret 登録・Cron Trigger 作成を反映。
   （CLOUDFLARE_API_TOKEN は Workers 編集権限が必要 — 既存で充足）

---

## 検証方針

1. **デプロイ前ローカル**: `terraform plan` で Cron Trigger と Secret バインドの差分を確認。
2. **dispatch の手動確認**: apply 後、Cloudflare ダッシュボード → Worker → Triggers で
   Cron が登録されていること、「Send test event」(scheduled) で daily-fetch run が起動することを確認。
   または `gh run list --workflow="Daily Tech Article Fetch"` で `workflow_dispatch` 起動を確認。
3. **本番タイミング**: 翌朝、run の `createdAt` が 23:15 UTC 付近（±数分）で、
   LINE 通知が 8:15〜8:30 JST に届くことを確認。`gh run view <id> --json createdAt,event` で
   `event: "workflow_dispatch"` と起動時刻をチェック。

---

## 確認事項

[Q1] cron 起動時刻 → `15 23 * * *`（JST 8:15、通知 ~8:17）で確定。
[Q2] weekly-conferences.yml も載せ替えるか → 今回は daily のみ対応。weekly は別途。
