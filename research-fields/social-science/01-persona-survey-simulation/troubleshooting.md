# トラブルシューティング

## デプロイ

### `deploy.sh` が `AuthorizationFailed` で止まる
Bicep が Role Assignment (Cognitive Services OpenAI User) を作成する権限は **User Access Administrator** または **Owner** が必要です。Contributor だけでは不足です。

### `The subscription is not registered to use namespace 'Microsoft.CognitiveServices'`
Resource Provider が未登録です。[`docs/01-prerequisites.md`](docs/01-prerequisites.md) の**プロバイダー登録**手順を実行してください。

### `Model 'gpt-4.1-mini' version '2025-04-14' is not available in region 'japaneast'`
モデルバージョンは月次で更新されます。最新の [Azure Foundry モデル利用可能性マトリックス](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability?pivots=standard) を確認し、`infra/parameters.json` の `modelVersion` を書き換えてください。

### `SpecialFeatureOrQuotaIdRequired` (Azure OpenAI 未申請)
2026 年時点でも一部のサブスクリプションでは Azure OpenAI 利用登録が必要です。<https://aka.ms/oai/access> から申請してください（通常は自動承認）。

## 認証

### `DefaultAzureCredential failed to retrieve a token`
- `az login` が完了しているか
- **AAD** から Cognitive Services OpenAI User ロールが自分に割り当てられているか (`deploy.sh` が実行済みか)
- ローカルで動かす場合は `az account show` でサブスクリプションが期待通りか

### `401 PermissionDenied` (API 呼び出し時)
Bicep で `disableLocalAuth: true` を設定しているため、**API キーは使えません**。必ず AAD トークンで認証してください。ロール割り当ての反映に最大 5 分かかります。

### `insufficient permissions on resource` on inference
Cognitive Services OpenAI **User** (5e0bd9bd-7b93-4f28-af87-19fc36ad61bd) が必要です。**Contributor** ではモデル管理はできても推論エンドポイントは呼べません。

## 実行 (シミュレーション)

### `429 Too Many Requests`
gpt-4.1-mini Standard の TPM/RPM 上限に達しています。以下を試してください：
1. `--concurrency` を減らす (デフォルト 4)
2. `infra/parameters.json` の `deploymentCapacity` を上げる (デフォルト 10 → 30 等)
3. Azure Portal → AI Foundry → デプロイ → Rate Limit を確認

### `response_format` エラー / `strict mode` failure
Structured Outputs は次を要求します：
- すべてのプロパティが `required` に含まれる
- すべてのオブジェクトが `additionalProperties: false`
- `enum` の値のみを返す（範囲外はエラー）
`src/simulate.py` の `LikertResponse` Pydantic モデルを勝手に変更する場合は上記に注意してください。

### `content_filter` refusal
Azure OpenAI コンテンツフィルタが質問文をブロックした可能性があります。ログの `refusal` 欄を確認し、質問文を書き換えるか、[コンテンツフィルタ設定](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/content-filters) をカスタマイズしてください（企業アカウントのみ）。

### `seed=42` を指定しても回答が変わる
`seed` は再現性を**近似**するだけで保証しません。同じ `system_fingerprint` の場合のみ再現期待。詳細は [Reproducible output](https://learn.microsoft.com/en-us/azure/foundry-classic/openai/how-to/reproducible-output)。

## 分析

### `chi2_contingency` が警告 `Some expected frequencies are less than 5`
サンプル数不足です。ペルソナ数を増やすか、`age_group` などの区分を粗くしてください。5 ペルソナ × 10 質問のデモでは統計的検定は**参考値**に留まります。

### `test_r2` が非常に高すぎる / 低すぎる
本シナリオは回帰ではなく分類的分析なので `r2` は使いません。χ² 統計量、p 値、Cramér's V を見てください。

## クリーンアップ

### `az group delete` で `Cannot delete resource`
Azure OpenAI の削除には数分かかります。`--no-wait` で開始し、しばらく後に `az group show -n <RG>` で確認してください。

### 削除後もコストが発生している
Log Analytics の**論理削除保持期間** (90 日) がありますが、追加課金は発生しません。もしトークン使用が請求書に残っている場合、削除前の呼び出し分です。
