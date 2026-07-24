# 06 — 後片付け

> ⚠️ **Compute Instance は停止中でも課金が続きます** — OS ディスク (P10 Std SSD) と Standard Load Balancer で約 $0.33/日。完全に不要なら Delete してください。

## 準備: .env を読み込む

```bash
# infra/deploy.sh が生成した .env を使用 (グローバルな az configure --defaults は使わない)
source .env
```

## ローカル環境の掃除

```bash
# 生成データ・予測・チェックポイントを削除
rm -rf data/*.png data/samples data/predictions data/checkpoints data/*.json data/train data/val data/test

# 仮想環境ごと削除
deactivate
rm -rf .venv
```

## Azure ML Compute Instance

### 停止 (再利用予定)

```bash
az ml compute stop --name <ci-name> \
  -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME"
```

> ⚠️ **停止中もOS ディスク (P10) と Standard Load Balancer で ~$0.33/日 課金されます。**  
> 完全に不要な場合は「削除」手順に進んでください。

### 削除 (完全に不要)

```bash
az ml compute delete --name <ci-name> \
  -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME" --yes
```

### GPU クラスター (CommandJob 用)

```bash
az ml compute delete --name gpu-cluster-nc4t4 \
  -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME" --yes
```

## Azure ML ジョブアーカイブ (任意)

ジョブ一覧を整理したい場合 (課金影響なし):

```bash
# 実行中ジョブ一覧を確認
az ml job list -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME" \
  --query "[?status!='Archived'].{name:name,status:status}" -o table

# 個別アーカイブ (削除はできないためアーカイブで非表示化)
az ml job archive --name <job-name> \
  -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME"
```

## デプロイメント削除

```bash
az deployment group delete \
  --name <deployment-name> \
  -g "$AZURE_RESOURCE_GROUP"
```

## Key Vault の完全削除

```bash
# 名前を厳密に確認してから削除 (誤削除防止)
KV_CHECK=$(az keyvault list -g "$AZURE_RESOURCE_GROUP" \
  --query "[?name=='$AML_KEY_VAULT_NAME'].name | [0]" -o tsv)

if [[ -n "$KV_CHECK" && "$KV_CHECK" == "$AML_KEY_VAULT_NAME" ]]; then
  az keyvault delete --name "$AML_KEY_VAULT_NAME" \
    -g "$AZURE_RESOURCE_GROUP"
  echo "Deleted Key Vault: $AML_KEY_VAULT_NAME"
  # ソフト削除期間 (kvSoftDeleteDays) 経過後に完全削除が可能
  # purgeProtection が無効なら即時パージも可:
  # az keyvault purge --name "$AML_KEY_VAULT_NAME" -l "$AZURE_LOCATION"
else
  echo "Key Vault '$AML_KEY_VAULT_NAME' not found — skipping"
fi
```

## リソースグループ全体の削除

> ⚠️ **このシナリオ専用の RG のみ削除してください。**  
> 他のリソースと共有している RG の場合は、個別リソース削除を使用してください。

```bash
# RG 内のリソースを確認してから削除
az resource list -g "$AZURE_RESOURCE_GROUP" \
  --query "[].{name:name, type:type}" -o table

# 削除 (非同期; 完了まで数分)
az group delete --name "$AZURE_RESOURCE_GROUP" --yes --no-wait
echo "Resource group deletion initiated: $AZURE_RESOURCE_GROUP"
```

## コスト確認

```bash
# 当月の RG 別コスト (Azure Cost Management CLI)
az cost management query \
  --scope "subscriptions/$AZURE_SUBSCRIPTION_ID" \
  --type ActualCost \
  --timeframe MonthToDate \
  --query 'properties.rows' -o table 2>/dev/null || \
  echo "Azure Portal → コスト管理 → コスト分析 で確認してください"
```

## チェックリスト

- [ ] `data/` 以下の生成物 (NPZ/PNG/JSON/PTH) を削除
- [ ] Compute Instance を Stop または Delete
  - 停止中も OS ディスク + LB で ~$0.33/日 課金継続
- [ ] CommandJob 用 GPU クラスターを Delete
- [ ] `.env` ファイルに機密情報がある場合は削除: `rm -f .env`
- [ ] Azure ML 全体不要ならリソースグループを削除
  - 共有 RG の場合は個別リソース削除のみ実施
- [ ] Azure Portal のコスト分析で当月請求額を確認
- [ ] 予算アラートを設定 ($10 など):  
  `Portal → サブスクリプション → 予算 → + 追加`
