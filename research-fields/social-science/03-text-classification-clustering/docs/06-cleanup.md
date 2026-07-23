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

Bicep で管理している場合、モデルデプロイだけを消すのは推奨しません (Bicep と実状態が乖離します)。テンプレートから該当デプロイを削除して再適用してください:

```bash
# 例: label deployment だけ消したい場合
# infra/main.bicep から labelDeployment リソースを削除して再デプロイ
az deployment group create \
  --resource-group rg-spread-social-03 \
  --template-file infra/main.bicep \
  --parameters @infra/parameters.json principalId=$(az ad signed-in-user show --query id -o tsv)
```

## ローカル成果物のクリーンアップ

```bash
rm -rf data/output data/embeddings/*.npy data/embeddings/*.csv .env
```

## コスト確認

過去 30 日の課金:

```bash
az consumption usage list \
  --start-date $(date -u -d '30 days ago' +%Y-%m-%d) \
  --end-date $(date -u +%Y-%m-%d) \
  --query "[?contains(instanceName, 'aoai-social-03')].[usageStart, meterDetails.meterName, pretaxCost, currency]" \
  -o table
```

Azure Portal の Cost Analysis で `Tag: <your-tag>` / RG フィルタで確認する方が視覚的にわかりやすいです。

> [!TIP]
> 本シナリオの想定コストは 1 回のフルデモで **$0.03〜0.05** です。それ以上の金額が計上されている場合、削除忘れのリソースがないか確認してください。
