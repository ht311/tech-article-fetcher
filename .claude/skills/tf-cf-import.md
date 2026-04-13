# Terraform Cloudflare Import

`terraform apply` で `already exists` エラーが出た場合、既存リソースをTerraform stateにインポートする。

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
