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
