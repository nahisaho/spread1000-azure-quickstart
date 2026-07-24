# 05. クリーンアップ

**AI for Science で最も忘れやすいのは「片付け」です**。BioEmu Job 完了後は必ずこのページを実行してください。

## 1. 段階的クリーンアップ (推奨)

### Step 1: Compute のみ削除 (Job 結果と workspace は保持)

まだ結果を解析中で、後日 Job を追加投入する予定がある場合:

```bash
az ml compute show --name gpu-a100 --query "current_node_count" -o tsv
# → 0 なら現時点で課金なし。急ぐ必要はない。
```

`min_instances: 0` かつ 2 分アイドルで縮小する設定なので、**GPU 時間の課金はほぼ発生しません**。ただし managed workspace の Key Vault / Storage / Log Analytics には少額の維持費 (概ね ¥数十〜数百/月) が発生し続けます。長期休止するなら compute リソース自体を削除:

```bash
az ml compute delete --name gpu-a100 --yes
```

### Step 2: Workspace のみ削除 (RG と storage は残す)

複数のクイックスタートを同じ RG に相乗りさせている場合:

```bash
az ml workspace delete \
  --name "$AZURE_WORKSPACE_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --permanently-delete \
  --yes
```

⚠️ `--permanently-delete` を指定しない場合、workspace は soft-delete で 14 日間 (Key Vault と同期) 保持されます。同名で再作成する予定がなければ `--permanently-delete` 推奨。

### Step 3: Resource Group ごと削除 (全消し)

もう BioEmu を触らないなら:

```bash
az group delete \
  --name "$AZURE_RESOURCE_GROUP" \
  --yes \
  --no-wait
```

## 2. Storage に残ったデータの取り扱い

削除前に、必要な出力を必ずローカルに退避:

```bash
# Job 出力を全てダウンロード
# --all で code/logs/output 全部を落とすと Spot 中断 job の途中データも保存できる。
# 実験ノート運用では code snapshot を欲しがるケースが多いので、意識的に外さない。
mkdir -p ~/bioemu-results
for JOB in $(az ml job list --query "[?tags.scenario=='bioemu' && (status=='Completed' || status=='Failed' || status=='Canceled')].name" -o tsv); do
  az ml job download --name "$JOB" --all --download-path ~/bioemu-results/$JOB
done

# HuggingFace + AlphaFold キャッシュ (workspaceblobstore に staging した場合)
CONTAINER=$(az ml datastore show --name workspaceblobstore --query container_name -o tsv)
az storage blob download-batch \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --auth-mode login \
  --source "$CONTAINER" \
  --pattern "bioemu-cache/*" \
  --destination ~/bioemu-cache 2>/dev/null || true
```

## 3. 削除前の最終チェック

```bash
# RG 配下に残っているリソース
az resource list \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query "[].{name:name, type:type}" -o table

# Public IP / Disk / NAT Gateway など「見落としがち」なものが無いか
az resource list -g "$AZURE_RESOURCE_GROUP" --query "[?type=='Microsoft.Network/publicIPAddresses']" -o table
az resource list -g "$AZURE_RESOURCE_GROUP" --query "[?type=='Microsoft.Compute/disks']" -o table
```

## 4. Key Vault の完全削除

Key Vault は soft-delete が有効のため、RG を削除しても 7〜90 日間残ります。同名で再デプロイ予定がなければ purge:

> [!WARNING]
> `contains(name,'kv-bioemu') | head -1` の従来スニペットは、**別のクイックスタート/ユーザーが作った BioEmu 系 KV** を誤って purge する事故を招きます。必ずデプロイ時に出力された **完全一致 の Key Vault 名** を控え、その名前を指定して purge してください。

```bash
# デプロイ時 output に表示された Key Vault 名を厳密指定 (fuzzy match 禁止)
KV_NAME="<infra/deploy.sh 出力の keyVaultName>"

# 存在確認 (deleted リストに厳密一致で 1 件のみ)
FOUND=$(az keyvault list-deleted \
  --query "[?properties.location=='japaneast' && name=='${KV_NAME}'].name" -o tsv)
if [ "$FOUND" = "$KV_NAME" ]; then
  az keyvault purge --name "$KV_NAME"
  echo "Purged: $KV_NAME"
else
  echo "Key Vault '$KV_NAME' not found in deleted list (safe: nothing to purge)."
fi
```

## 5. Cost Management で最終確認 (翌日)

削除の翌日、Azure Portal → Cost Management → Cost analysis で `rg-spread1000-bioemu` に課金が発生していないことを確認。稀に:

- Storage の遅延削除 (~24h)
- 削除失敗した private endpoint
- 独立して作成した Log Analytics workspace

が残ることがあります。

## 6. 予算アラート・Budget の削除 (任意)

```bash
az consumption budget delete \
  --budget-name "bioemu-quickstart" \
  --resource-group "$AZURE_RESOURCE_GROUP" 2>/dev/null || true
```

## チェックリスト

- [ ] Job 出力をローカル退避済み
- [ ] Compute node count が 0 (または compute 削除済み)
- [ ] Workspace 削除済み (または RG ごと削除)
- [ ] Key Vault purge 済み (再デプロイ予定なしの場合)
- [ ] 翌日 Cost Management で課金 0 を確認
- [ ] 予算アラート削除 (任意)

## トラブル時

削除中にエラーが出た場合や、リソースが残り続ける場合は [Troubleshooting §リソース削除失敗](troubleshooting.md#リソース削除が失敗する) を参照。

## 次のステップ

- 別の分野・別のシナリオへ: [クイックスタート一覧](../../../README.md)
- BioEmu を本格運用する場合: `AZURE_AI_FOUNDRY.md` (Microsoft 公式 managed endpoint 手順) を参照
