# トラブルシューティング

## Bicep

### `az deployment group create` が RBAC で失敗

**症状**: `AuthorizationFailed: The client does not have authorization to perform action 'Microsoft.Authorization/roleAssignments/write'`

**原因**: サブスクリプションで **User Access Administrator** ロールが不足

**対処**: Owner 権限を持つ管理者に依頼するか、既存 RG に対する User Access Administrator を付与してもらう。

### Bicep 検証エラー: `ContainerRegistryNameNotAvailable`

**原因**: ACR 名はグローバル一意で、`uniqueString(resourceGroup().id)` でもたまに衝突する

**対処**: `parameters.example.json` に `acrName` を明示指定し、`crmolgen<yourinitials><yyyymmdd>` のような固有名を渡す

## Prior ダウンロード

### `download-priors.sh` が HTML を保存してしまう

**原因**: Zenodo が一時的に 5xx を返した / rate limit

**対処**: 5〜10 分待って再実行。`priors/` を空にしてから再度スクリプト実行:

```bash
rm -f priors/*.prior && bash scripts/download-priors.sh
```

`wc -c < priors/libinvent.prior` で各ファイルが 1 MB 以上あることを確認 (期待は ~40 MB)。

## Blob アップロード

### `az storage blob upload-batch` が Forbidden

**原因**: `az login` セッションに Storage Blob Data Contributor が反映されていない

**対処**:

```bash
az account clear && az login
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
# 直接 RBAC 確認
DEPLOYER_OID=$(az ad signed-in-user show --query id -o tsv)
az role assignment list \
  --assignee "$DEPLOYER_OID" \
  --scope "/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$AZURE_STORAGE_ACCOUNT" \
  -o table
```

## AML Job

### `Preparing` から進まない (10 分以上)

**原因**: Environment image build 中（初回のみ 5〜10 分）

**対処**: AML Studio のジョブ画面 → Outputs + logs → `20_image_build_log.txt` で build 進行を確認。build ログでエラーが出ていなければ待つ。

### ジョブが `Failed` で `ModuleNotFoundError: No module named 'reinvent'`

**原因**: Environment に `reinvent` が含まれていない、または PyPI に無いバージョンを pin している

**対処**: `aml/conda.yml` は `reinvent` を `git+https://github.com/MolecularAI/REINVENT4.git@v4.8` から取得する形になっています。GitHub 側でタグが変更/削除された場合は `main` に切り替えるか、[Releases](https://github.com/MolecularAI/REINVENT4/releases) から最新タグを確認して差し替えてください。Environment version は immutable のため、変更したら `aml/environment.yml` の `version:` をインクリメント:

```bash
# 1) aml/environment.yml の version を "2" に上げる
# 2) aml/conda.yml を修正 (reinvent の入手経路を GitHub に変更)
# 3) 新バージョン登録
az ml environment create -f aml/environment.yml -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME"
# 4) ジョブ送信時にバージョン明示
az ml job create -f aml/job-generate.yml \
  --set environment=azureml:reinvent4-cpu:2 \
  -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME"
```

### ジョブが `Failed` で `reinvent` CLI が exit code != 0

**原因**: scaffold SMILES が LibInvent 要件を満たしていない ([*:1]/[*:2] 無し、3 点以上、不正 SMILES など)

**対処**: `outputs/user_logs/std_log.txt` の `reinvent.log` セクションを確認。scaffold は必ず以下の形式:

- 2 attachment points: `Cc1ccc([*:1])cc1[*:2]`
- attachment 記号は `[*:1]`, `[*:2]` の**番号付き**アスタリスク
- 3 点以上必要な場合は LinkInvent (別 prior) を使用

### 生成されたが `valid_ratio` が極端に低い (< 0.3)

**原因**: scaffold が prior の訓練分布と大きく乖離している / attachment 点が不足している

**対処**:

- scaffold を drug-like な小分子 (BRICS フラグメントなど) に変更
- `[*:1]`, `[*:2]` の 2 点が明示的に含まれているか確認
- `--num-smiles` を増やして統計を安定させる (デフォルト 100 → 500 など)

## コスト

### 予想より高い課金

**確認手順**:

1. Azure Portal > Cost Management + Billing > Cost analysis
2. Scope: 本 quickstart の Resource Group
3. Group by: Resource

**よくある原因**:

- ACR Basic (月 $5) が丸ごと計上されている → 一時的な使い捨てなら RG ごと削除
- Compute cluster を `min_instances >= 1` にしていた → `min_instances=0` へ変更

詳細は [`../../../../docs/01-cost-management.md`](../../../../docs/01-cost-management.md)。
