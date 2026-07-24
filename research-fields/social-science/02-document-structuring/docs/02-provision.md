# 02 — プロビジョニング

Bicep で **Document Intelligence** + **Azure OpenAI アカウント + gpt-5.4-mini デプロイ** + **RBAC (両方への `Cognitive Services User` / `OpenAI User`)** を一括作成します。

## パラメータファイル

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/social-science/02-document-structuring"
cd "$SCENARIO_DIR"
cp infra/parameters.example.json infra/parameters.json
```

`infra/parameters.json` の中身：

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "namePrefix":             { "value": "spr-soc02" },
    "location":               { "value": "japaneast" },
    "aoaiDeploymentName":     { "value": "extract-gpt54mini" },
    "aoaiModelName":          { "value": "gpt-5.4-mini" },
    "aoaiModelVersion":       { "value": "2026-03-17" },
    "aoaiDeploymentCapacity": { "value": 10 }
  }
}
```

> [!NOTE]
> リソース名は `namePrefix` + `uniqueString(subscription().id, resourceGroup().id)` で自動生成され、グローバル一意性を保ちます。デプロイを繰り返しても同じ名前が使われます。

環境変数：

```bash
export DOC_RG="spread-social-doc-rg"
# リソース名は deploy.sh が .env に書き出します。手動で確認したい場合:
# export DOC_INTEL_NAME="spr-soc02-di-<suffix>"  # ← Bicep outputs.docIntelName を参照
# export AOAI_ACCOUNT_NAME="spr-soc02-oai-<suffix>"
export AOAI_DEPLOYMENT_NAME="extract-gpt54mini"     # ← parameters.json と一致
```

## デプロイ

```bash
az account show --query "{name:name, id:id}" -o table

./infra/deploy.sh "$DOC_RG" infra/parameters.json
```

`deploy.sh` の動作：
- Microsoft.CognitiveServices プロバイダーを確認・登録
- リソースグループが無ければ自動作成
- 現ユーザーの Object ID を取得
- `az deployment group create` で Bicep 適用 (3〜5 分)
- 出力から `.env` を自動生成 (`chmod 600`)

## 環境変数として保存

`deploy.sh` が `.env` を書き出すため、以降は以下で読み込むだけです：

```bash
set -a; source .env; set +a
```

> [!WARNING]
> `.env` はコミットしないでください。`.gitignore` に既に含まれています。

## デプロイの確認

```bash
az cognitiveservices account list -g "$DOC_RG" -o table

az account get-access-token --resource https://cognitiveservices.azure.com \
  --query "{expiresOn:expiresOn,tenant:tenant}" -o table
```

## パブリックネットワークアクセスと Private Endpoint

`infra/parameters.json` に `enablePublicNetworkAccess: false` を設定すると、パブリックアクセスを無効にできます：

```json
"enablePublicNetworkAccess": { "value": false }
```

> [!WARNING]
> `enablePublicNetworkAccess=false` を使う場合は Private Endpoint と VNet 構成が別途必要です（本クイックスタートには実装されていません）。実際の研究データを扱う場合は、このオプションと Private Endpoint の設定を強く推奨します。

次: [`03-prepare-documents.md`](03-prepare-documents.md)
