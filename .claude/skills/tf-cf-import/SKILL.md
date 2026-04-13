---
name: tf-cf-import
description: Terraform Cloudflare既存リソースのインポート手順。`terraform apply`で`already exists`エラーが発生した場合、または既存CloudflareリソースをTerraform state管理下に取り込む必要がある場合に使用する。KV Namespace、Workers Scriptなどのリソース種別ごとのインポートコマンドを提供する。CloudflareとTerraformが関わる作業でこのスキルを積極的に使用すること。
---

# Terraform Cloudflare Import

`terraform apply` で `already exists` エラーが出た場合、既存リソースをTerraform stateにインポートする。

## 必要な環境変数

```bash
CLOUDFLARE_ACCOUNT_ID=<アカウントID>
CLOUDFLARE_API_TOKEN=<APIトークン>
```

## 手順

### 1. KV Namespaceのインポート

名前空間IDを取得:
```bash
curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/storage/kv/namespaces" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  | jq '.result[] | select(.title == "<TITLE>") | .id'
```

インポート:
```bash
terraform import cloudflare_workers_kv_namespace.<RESOURCE_NAME> <ACCOUNT_ID>/<NAMESPACE_ID>
```

### 2. Workers Scriptのインポート

```bash
terraform import cloudflare_workers_script.<RESOURCE_NAME> <ACCOUNT_ID>/<SCRIPT_NAME>
```

### 3. 再apply

```bash
terraform apply
```

## トラブルシューティング

- `RESOURCE_NAME`: Terraformコード内の `resource "cloudflare_workers_kv_namespace" "<RESOURCE_NAME>"` のラベル
- `SCRIPT_NAME`: Cloudflare Dashboard上のWorkers名
- APIトークンに `Account:KV Storage:Edit` と `Account:Workers Scripts:Edit` 権限が必要
