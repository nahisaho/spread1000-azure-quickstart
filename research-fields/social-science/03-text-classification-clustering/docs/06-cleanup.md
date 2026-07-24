# 06. クリーンアップ

## リソースを完全に削除する (最推奨)

デモが終わったらリソースグループごと削除すると、無駄な課金が発生しません。

```bash
az group delete -n rg-spread-social-03 --yes --no-wait
```

削除は非同期で数分〜十数分かかります。完了確認:

```bash
az group exists -n rg-spread-social-03
```

## モデルデプロイだけを消す (アカウントは残す)

Bicep で管理している場合、モデルデプロイだけを消すのは推奨しません (Bicep と実状態が乖離します)。ただしアカウントを次のシナリオで再利用したい、料金メーターを一時停止したい等の理由で個別に消したい場合は、以下のコマンドで削除できます:

```bash
# .env を読み込んでいる前提
set -a && source ../.env && set +a

# embedding デプロイを削除
az cognitiveservices account deployment delete \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --name "$AZURE_OPENAI_ACCOUNT_NAME" \
  --deployment-name "$AZURE_OPENAI_EMBED_DEPLOYMENT"

# label 生成用デプロイを削除
az cognitiveservices account deployment delete \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --name "$AZURE_OPENAI_ACCOUNT_NAME" \
  --deployment-name "$AZURE_OPENAI_LABEL_DEPLOYMENT"
```

Bicep を再適用する際は `infra/main.bicep` から該当リソースも削除してから `deploy.sh` を再実行してください。テンプレートを更新せずに再適用すると削除したデプロイが復活します。

Bicep でまとめて再適用する場合の例:

```bash
az deployment group create \
  --resource-group rg-spread-social-03 \
  --template-file infra/main.bicep \
  --parameters @infra/parameters.json principalId=$(az ad signed-in-user show --query id -o tsv)
```

## ローカル成果物のクリーンアップ

```bash
rm -rf data/output data/embeddings/*.npy data/embeddings/*.csv data/embeddings/*.manifest.json .env
```

## コスト確認

過去 30 日の課金 (メーター詳細つき):

```bash
az consumption usage list \
  --start-date $(date -u -d '30 days ago' +%Y-%m-%d) \
  --end-date $(date -u +%Y-%m-%d) \
  --include-meter-details \
  --query "[?contains(instanceName, 'aoai-social-03') || contains(instanceName, 'spread-social-03')].[usageStart, meterDetails.meterName, pretaxCost, currency]" \
  -o table
```

Azure Portal の Cost Analysis で `Tag: <your-tag>` / RG フィルタで確認する方が視覚的にわかりやすいです。

> [!TIP]
> 本シナリオの想定コストは 1 回のフルデモで **$0.03〜0.05** です。それ以上の金額が計上されている場合、削除忘れのリソースがないか確認してください。
