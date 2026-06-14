terraform {
  required_version = ">= 1.5"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# -------------------------------------------------------------------
# KV Namespace
# フィードバック履歴（preferences）と当日の記事リスト（last_articles）を格納する
# -------------------------------------------------------------------
resource "cloudflare_workers_kv_namespace" "preferences" {
  account_id = var.cloudflare_account_id
  title      = "tech-article-fetcher-preferences"
}

# -------------------------------------------------------------------
# Worker スクリプト
# cloudflare/src/index.js を読み込んでデプロイする
# -------------------------------------------------------------------
resource "cloudflare_workers_script" "webhook" {
  account_id = var.cloudflare_account_id
  name       = "tech-article-fetcher-webhook"
  content    = file("${path.module}/../cloudflare/index.js")

  # ES Modules 形式を使用する
  module = true

  # KV Namespace をバインド
  kv_namespace_binding {
    name         = "KV"
    namespace_id = cloudflare_workers_kv_namespace.preferences.id
  }

  # LINE_CHANNEL_SECRET を Secret として設定
  secret_text_binding {
    name = "LINE_CHANNEL_SECRET"
    text = var.line_channel_secret
  }

  # LINE_CHANNEL_ACCESS_TOKEN を Secret として設定（Reply API 用）
  secret_text_binding {
    name = "LINE_CHANNEL_ACCESS_TOKEN"
    text = var.line_channel_access_token
  }

  # GITHUB_TOKEN を Secret として設定（Cron Trigger から workflow_dispatch を呼ぶ用）
  secret_text_binding {
    name = "GITHUB_TOKEN"
    text = var.github_token
  }
}

# -------------------------------------------------------------------
# Cloudflare Workers Cron Trigger — 日次フェッチ定時起動
# GitHub Actions の schedule 遅延（毎日 40〜70 分）を回避するため、
# Cron Trigger から workflow_dispatch で daily-fetch.yml を起動する。
# -------------------------------------------------------------------
resource "cloudflare_workers_cron_trigger" "daily_fetch" {
  account_id  = var.cloudflare_account_id
  script_name = cloudflare_workers_script.webhook.name
  schedules   = ["15 23 * * *"] # 23:15 UTC = JST 8:15（dispatch 起動なので遅延なし、通知 ~8:17）
}

# -------------------------------------------------------------------
# Cloudflare Pages プロジェクト（ダッシュボード）
# dashboard/ ディレクトリを Wrangler でデプロイする
# -------------------------------------------------------------------
resource "cloudflare_pages_project" "dashboard" {
  account_id        = var.cloudflare_account_id
  name              = "tech-article-fetcher-dashboard"
  production_branch = "main"

  deployment_configs {
    production {
      kv_namespaces = {
        KV = cloudflare_workers_kv_namespace.preferences.id
      }
    }
  }
}

# 注: ダッシュボード認証は Pages Functions の HTTP Basic Auth (_middleware.ts) で実装。
# DASHBOARD_SECRET 環境変数は terraform apply 後に Cloudflare Pages ダッシュボード
# (Settings → Environment variables → Add variable → Encrypt) で手動設定してください。
