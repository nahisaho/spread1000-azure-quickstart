# トラブルシューティング

> [!IMPORTANT]
> 本ドキュメントのコマンドは特記なき限り **ローカル PC (もしくは Cloud Shell)** で、`deploy.sh` を実行した本人の Azure アカウントで実行してください。事前に環境変数を設定:
> ```bash
> export AZURE_RESOURCE_GROUP=rg-spread1000-rnaseq-tanaka  # ← 自分の値
> export AZURE_BATCH_ACCOUNT=batspread1000rnaseqtanaka     # ← 自分の値
> export AZURE_STORAGE_ACCOUNT=stspread1000rnaseqtanaka    # ← 自分の値
> ```

## タスクが pending のまま進まない

**症状**: `nextflow run` を実行しても Batch のタスクが数十分「Pending」で止まる。

**原因**: Batch アカウントの **dedicated core quota** または VM ファミリの capacity 不足。

**対処**:
```bash
az batch account show --resource-group "$AZURE_RESOURCE_GROUP" --name "$AZURE_BATCH_ACCOUNT" \
  --query '{ded:dedicatedCoreQuota,low:lowPriorityCoreQuota,family:dedicatedCoreQuotaPerVMFamily}' -o jsonc
```
- Dedicated (合計 or ファミリ別) が要求以下 → Portal → Batch アカウント → **クォータ** → **クォータの要求** (1〜3 営業日で承認)
- Capacity 不足 (`AllocationFailed`) → Japan West / East US 2 に切り替え

## コンテナ イメージ pull の失敗

**症状**: Batch task が `TaskFailed` で終了、`stderr.txt` に `manifest unknown` / `pull rate limit exceeded` / `unauthorized`。

**原因**:
- Docker Hub の anonymous pull rate limit (100 pull / 6 時間 / IP)
- Quay.io の一時的な障害
- ノードのディスク不足でイメージ layer が展開できない

**対処**:
1. **推奨 (public image のミラー + 匿名 pull)**: nf-core/rnaseq は工程ごとに `quay.io/biocontainers/<tool>:<tag>` などの **完全修飾イメージ名** を使うため、`process.container` を上書きするとパイプラインが壊れます。代わりに Azure Container Registry を使い、Nextflow の docker registry rewrite を効かせます:
   - **匿名 pull を有効化する場合は Standard tier ACR** が必要 (Basic tier は匿名 pull 非対応)。認証付きで良い場合は Basic でも可
   - `az acr import --source quay.io/biocontainers/star:...` などで必要イメージを **同じリポジトリパスのまま**インポート
   - `nextflow.azure.config` に以下を追加:
     ```groovy
     docker {
         registry = '<acr>.azurecr.io'
         registryOverride = true   // 完全修飾名の registry 部分を強制的に置き換える (Nextflow 25.10+)
     }
     ```
   - Standard tier で `az acr update --name <acr> --anonymous-pull-enabled true` を実行しておけば追加の credential は不要
2. **プライベート ACR (認証付き)**: `nextflow.azure.config` に registry credentials を指定します:
   ```groovy
   azure {
       registry {
           server = '<acr>.azurecr.io'
           userName = '<service-principal-id>'
           password = '<service-principal-password>'
       }
   }
   ```
   > **User-assigned Managed Identity を Batch pool に付けて `AcrPull` で pull する方式** は本テンプレートに含まれておらず、Bicep での UAMI 作成・pool への identity attach・`identityReference` を含む containerRegistry 設定など複数の追加作業が必要です。初心者向けでない用途では nf-azure と Batch pool schema の最新ドキュメントを参照してください。
3. **クイックフィックス**: E16ds_v5 (600 GiB temp SSD 付き) にプールを変更し、Docker data root を `/mnt/docker` へ移す (start-task で設定)
4. Azure Batch の Container Configuration で prefetch を指定

参考: [Batch containers](https://learn.microsoft.com/en-us/azure/batch/batch-docker-container-workloads)

## STAR が exit code 137 で落ちる (OOM)

**症状**: STAR プロセスが exit 137 で失敗、stderr に `Killed` / メッセージなし。

**原因**: RAM 不足。Human primary assembly の STAR は ~30 GB RAM 必要。D8ds_v5 (32 GB) では他プロセスと同居すると OOM。

**対処**:
- ノード SKU を **E16ds_v5 (128 GB RAM)** に変更 (`config/nextflow.azure.config` の `machineType`)
- ノード上で 1 STAR タスクのみ実行するように `process.STAR_ALIGN.maxForks = 1` を設定
- alternate contig / decoy を減らす (primary assembly のみ使用)

## `AuthorizationPermissionMismatch` / `AuthenticationFailed`

**症状**: Blob 読み書き時に `HTTP 403` / `AuthorizationPermissionMismatch`。

**原因**: RBAC 設定の反映遅延 (最大 5 分) または誤ったスコープ。

**対処** (以下 3 と 4 の `az role assignment list` は **ローカル PC**、Owner/User Access Administrator 権限のあるアカウントで実行):
1. 5〜10 分待つ
2. Controller VM 上で `az login --identity` した状態で `az storage blob list --account-name "$AZURE_STORAGE_ACCOUNT" --container-name omics --auth-mode login -o none` が通るか確認
3. Controller VM の system-assigned MI のロール割り当てを確認:
   ```bash
   CTRL_MI=$(az vm show -g "$AZURE_RESOURCE_GROUP" -n vm-nf-controller --query identity.principalId -o tsv)
   az role assignment list \
     --assignee "$CTRL_MI" \
     --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$AZURE_STORAGE_ACCOUNT" \
     -o table
   ```
   → `Storage Blob Data Contributor` が付与されていること
4. Batch data plane 権限も同様に確認:
   ```bash
   az role assignment list \
     --assignee "$CTRL_MI" \
     --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.Batch/batchAccounts/$AZURE_BATCH_ACCOUNT" \
     --query '[].roleDefinitionName' -o tsv
   ```
   → `Azure Batch Data Contributor` (pool 作成/更新/削除, autoscale, job/task) が出ること

## SAS トークン期限切れ (`AuthenticationFailed` after ~48h)

**症状**: 長時間 (>48h) ワークフローの後半で認証失敗。

**原因**: Nextflow が生成する SAS トークンの既定期限は 48 時間。長時間実行では超過する。

**対処**: `nextflow.azure.config` に以下追加:
```groovy
azure {
    storage {
        tokenDuration = '96h'  // または '168h'
    }
}
```

## `-resume` が効かず、最初からやり直しになる

**症状**: 失敗後 `-resume` を付けても、すべての process が再実行される。

**原因**:
- `-w` (workDir) が前回と異なる
- `-c` config を変更した (キャッシュキーが変わる)
- Nextflow revision (`-r`) を変えた
- Blob の workDir 内容が消えた (lifecycle 削除等)

**対処**: `-resume` は **同じ revision、config、workDir** の 3 つを揃えることが必須。`workDir` をタイムスタンプで生成する場合、再実行時は必ず前回と同じ値を使う。

## ノードが 0 に戻らず課金が続く

**症状**: 実行完了後もプールに数ノード残っている。

**原因**: `deleteJobsOnCompletion = false` または autoscale formula が間違っている。

**対処**: 緊急停止 (autoscale を先に無効化してから resize、**ローカル PC で実行**):
```bash
az batch account login --resource-group "$AZURE_RESOURCE_GROUP" --name "$AZURE_BATCH_ACCOUNT"
for POOL in $(az batch pool list --query "[].id" -o tsv); do
  az batch pool autoscale disable --pool-id "$POOL" 2>/dev/null || true
  az batch pool resize --pool-id "$POOL" \
    --target-dedicated-nodes 0 --target-low-priority-nodes 0
done
```
> autoscale を無効化しないまま `resize` すると `409 PoolBeingResized`/`OperationInvalidForCurrentState` が返ります。
恒久対策: `nextflow.azure.config` の `deleteJobsOnCompletion = true` かつ `deletePoolsOnCompletion = true` を確認。

## Cloud Shell で実行したら消えた

**症状**: Azure Cloud Shell で `nextflow run` を起動し、離れたら数十分後にセッションが切れて実行も止まっていた。

**原因**: Cloud Shell は 20 分の無操作で強制切断され、実行中プロセスも終了します。

**対処**: **必ず Controller VM (B2s) 上で `tmux` を使う**。Cloud Shell はリソース作成のみに使用してください。

参考: [Cloud Shell FAQ](https://learn.microsoft.com/en-us/azure/cloud-shell/faq-troubleshooting)

## Spot ノードが評価中に何度も evict される

**症状**: Spot ノードで実行中、eviction が数回発生し実行時間が想定を大きく超過。

**原因**: リージョン内 Spot 需給の逼迫。

**対処**:
- **短時間タスク (< 30 分)** のみ Spot に (`nextflow.azure.config` の `queue` を分割)
- 長時間 STAR は dedicated に固定
- 別リージョン (Japan West / East US 2) に一時的に切り替え

## MultiQC レポートが真っ白 / 未生成

**症状**: `results/*/multiqc/multiqc_report.html` が存在しない or 空。

**原因**:
- 前段のプロセスがすべて失敗し MultiQC に渡す入力がなかった
- ノード上のログ収集が完了する前に SAS 期限切れ

**対処**:
1. Nextflow の execution report を確認: `results/*/pipeline_info/` 配下の `execution_report_*.html`
2. 個々のプロセスの `.command.log` を Blob からダウンロードして stderr を確認
3. `-resume` で失敗タスクのみ再実行

## 費用の日次アラートを設定したい

Azure Portal → **コスト管理 + 請求** → **予算** → 新規予算作成:
- 期間: 月次
- しきい値: ¥10,000 (実績) / ¥50,000 (実績)
- スコープ: 対象リソースグループ
- 通知先: メールアドレス

CLI で作成する例 (JSON パラメータは Portal で参照):

```bash
az consumption budget create --help
```

## 参考リンク

- [nf-core/rnaseq usage](https://nf-co.re/rnaseq/3.26.0/docs/usage)
- [Nextflow Azure Batch](https://docs.seqera.io/nextflow/azure)
- [Azure Batch troubleshooting](https://learn.microsoft.com/en-us/azure/batch/best-practices)
- [Azure Batch quotas](https://learn.microsoft.com/en-us/azure/batch/batch-quota-limit)
