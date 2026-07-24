# 02 — Azure リソース準備

## IaC で作成 (推奨)

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
cd "$SCENARIO_DIR"

# parameters.example.json を編集して deployerObjectId を設定
YOUR_OID=$(az ad signed-in-user show --query id -o tsv)
sed -i "s/<YOUR-AAD-OBJECT-ID>/$YOUR_OID/" infra/parameters.example.json

bash infra/deploy.sh            # 本番デプロイ
# bash infra/deploy.sh --what-if  # 変更確認のみ
```

`infra/main.bicep` で作成されるリソース:
- `Microsoft.CognitiveServices/accounts@2026-05-01` (`kind: SpeechServices`, `sku: S0`)
- SystemAssigned マネージド ID、ローカル認証無効 (Entra のみ)
- Cognitive Services User ロール割り当て (`a97b65f3-24c7-4388-baec-2e87135dc908`)
- Log Analytics + Application Insights (診断ログ)

## Portal で作成 (手動)

1. Azure Portal で [Create a resource] → `Speech services` を検索
2. 設定:
   - **Resource group**: 新規作成 (例: `rg-speech-demo`)
   - **Region**: `Japan East`
   - **Pricing tier**: `Standard S0`
     - F0: 1 同時リアルタイム接続; Batch は F0 では利用不可 (S0 が必要)
3. 作成完了後、`Access control (IAM)` → ユーザーに `Cognitive Services User` ロールを付与

## 認証の設定

### 推奨: Entra (DefaultAzureCredential)

```bash
az login
# サービスプリンシパル/ワークロード ID の場合は AZURE_CLIENT_ID 等を設定
export AZURE_CLIENT_ID=<workload-identity-client-id>
```

`infra/deploy.sh` を使用した場合、`.env` には Key は含まれず Entra 認証のみ有効です。

### フォールバック: キー認証 (enableLocalAuth=true の場合のみ)

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
cd "$SCENARIO_DIR"

# キーをファイルに書き出す (シェル履歴に残さない)
KEY=$(az cognitiveservices account keys list --name "$NAME" --resource-group "$RG" --query key1 -o tsv)
printf 'AZURE_SPEECH_KEY=%s\nAZURE_SPEECH_REGION=%s\n' "$KEY" "$LOC" > .env
chmod 600 .env
unset KEY
```

> **注意**: `cat .env` で確認せず、`stat -c '%a %n' .env` でパーミッションのみ確認。  
> キーのローテーション: `az cognitiveservices account keys regenerate -n $NAME -g $RG --key-name key1`

## 料金 (参考値: 2026-07 時点、japaneast、S0)

| 機能 | 単価 |
|---|---|
| STT Standard | $1.00 / 音声時間 |
| STT Batch | $0.60 / 音声時間 |
| TTS Neural | $16 / 100 万文字 |
| Custom Neural Voice (学習) | $52 / hour |

最新の料金: https://azure.microsoft.com/pricing/details/cognitive-services/speech-services/

**存在するだけでは無課金**、実際に使ったぶんのみ。

