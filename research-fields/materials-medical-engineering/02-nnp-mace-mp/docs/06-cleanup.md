# 06 — 後片付け

## ローカル環境の場合

```bash
# 生成データを削除（venv とキャッシュは残す）
rm -rf data/*.traj data/*.extxyz data/*.cif data/*.log data/*.json data/*.png

# MACE モデルキャッシュも消したい場合（次回再ダウンロード ~80 MB）
rm -rf ~/.cache/mace/

# 仮想環境ごと削除
deactivate
rm -rf .venv
```

## Azure ML Compute Instance の場合

### ⚠️ 最重要: 停止するのを忘れないでください

**Compute Instance は起動しているだけで課金されます。** セッション終了時に必ず停止 or 削除してください。

### 停止（あとで再利用する場合）

Azure ML Studio → 「Compute」→ 「Compute instances」→ 該当インスタンスを選択 → 「Stop」

停止中はコンピュート自体の課金は 0 になりますが、以下は**継続して課金**されます:

- **OS ディスク** (128 GB Std SSD, P10 相当): 月 ~$7
- **Standard Load Balancer** (CI に紐づく): ~$0.33/日 ≒ 月 ~$10
- **AML compute quota** は解放されない (再起動を待ちながら他のジョブに割り当てられない)

「停止 = ほぼ無料」ではありません。**長期間使わないなら削除**することを推奨します。

CLI から:
```bash
set -a && source .env && set +a
az ml compute stop --name <ci-name> \
  --workspace-name "$AML_WORKSPACE_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP"
```

### 削除（完全に不要な場合）

Azure ML Studio → 「Compute」→ 該当インスタンスを選択 → 「Delete」

CLI から:
```bash
az ml compute delete --name <ci-name> \
  --workspace-name "$AML_WORKSPACE_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" --yes
```

### Azure ML ワークスペース全体の削除

もう Azure ML 自体を使わない場合、リソースグループごと削除するのが最も確実です:

```bash
set -a && source .env && set +a
az group delete --name "$AZURE_RESOURCE_GROUP" --yes --no-wait
```

削除には 5〜15 分程度かかります。

### Key Vault のソフト削除 (soft-delete) を purge する

本シナリオの Bicep は Key Vault の soft-delete を 7 日にしています。**同名 (`AML_KEY_VAULT_NAME`) で即座に再デプロイしたい場合**は purge が必要です。**必ず `AML_KEY_VAULT_NAME` と完全一致することを確認してから** purge してください:

```bash
set -a && source .env && set +a
DELETED_NAME=$(az keyvault list-deleted --query "[?name=='$AML_KEY_VAULT_NAME'].name | [0]" -o tsv)
if [ "$DELETED_NAME" = "$AML_KEY_VAULT_NAME" ]; then
  az keyvault purge --name "$AML_KEY_VAULT_NAME" --location "$AZURE_LOCATION"
else
  echo "No soft-deleted vault with exact name $AML_KEY_VAULT_NAME — nothing to purge."
fi
```

> ⚠️ `az keyvault list-deleted --query "contains(name,'kv-macemp02')"` のような**部分一致**で purge しないでください。他ユーザ / 他プロジェクトの vault を消す事故につながります。

## コスト確認

Azure Portal → 「コスト管理」→ 「コスト分析」で当月の請求額を確認できます。**サブスクリプション予算アラート**を $10 などに設定しておくと、想定外の請求を早期発見できます:

```
Portal → サブスクリプション → 予算 → + 追加
```

## チェックリスト

- [ ] `data/*.traj`, `data/*.extxyz`, `data/*.cif`, `data/*.png` を削除した
- [ ] Azure を使った場合、Compute Instance を「Stop」または「Delete」した
- [ ] Azure ML ワークスペースが不要なら `az group delete` した
- [ ] 同名で再デプロイする予定なら Key Vault を purge した (exact-name)
- [ ] Azure Portal のコスト分析で当月の請求額を確認した
