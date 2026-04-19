output "kv_namespace_id" {
  description = "KV Namespace ID。GitHub Secrets の CLOUDFLARE_KV_NAMESPACE_ID に登録する。"
  value       = cloudflare_workers_kv_namespace.preferences.id
}

output "worker_url" {
  description = "Worker のデフォルト URL。LINE Developers の Webhook URL に設定する。workers.dev サブドメインは Cloudflare ダッシュボード → Workers & Pages で確認。"
  value       = "https://tech-article-fetcher-webhook.<your-subdomain>.workers.dev"
}

output "dashboard_url" {
  description = "ダッシュボードの URL（Cloudflare Access 認証あり）"
  value       = "https://${cloudflare_pages_project.dashboard.name}.pages.dev"
}

