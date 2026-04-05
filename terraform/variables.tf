variable "cloudflare_api_token" {
  description = "Cloudflare API トークン（Workers・KV の編集権限が必要）"
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare アカウント ID"
  type        = string
}

variable "line_channel_secret" {
  description = "LINE Channel Secret（webhook 署名検証に使用）"
  type        = string
  sensitive   = true
}
