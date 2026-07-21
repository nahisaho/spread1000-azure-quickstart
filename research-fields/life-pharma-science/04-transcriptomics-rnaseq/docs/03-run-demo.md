# 03. デモ実行 (nf-core/rnaseq test プロファイル)

このドキュメントでは、nf-core が公開している **小型のテストデータセット** を使い、パイプラインが Azure Batch で通しで動くことを確認します。実データを使うのは `docs/04-real-data.md` です。

> [!IMPORTANT]
> 以下すべての操作は **Controller VM 上で** 実行します (`ssh azureuser@<Controller IP>`)。ローカル PC ではありません。

## 1. 環境変数の設定

Controller VM 上で:

```bash
# Bicep デプロイ時に表示された値を設定
export AZURE_LOCATION=japaneast
export AZURE_BATCH_ACCOUNT=batspread1000rnaseqtanaka   # ← 自分の値
export AZURE_STORAGE_ACCOUNT=stspread1000rnaseqtanaka  # ← 自分の値
export AZURE_RESOURCE_GROUP=rg-spread1000-rnaseq-tanaka  # ← 自分の値 (deploy.sh 出力を参照)

# 永続化: ~/.bashrc に追加
cat >> ~/.bashrc <<EOF
export AZURE_LOCATION=${AZURE_LOCATION}
export AZURE_BATCH_ACCOUNT=${AZURE_BATCH_ACCOUNT}
export AZURE_STORAGE_ACCOUNT=${AZURE_STORAGE_ACCOUNT}
export AZURE_RESOURCE_GROUP=${AZURE_RESOURCE_GROUP}
export NXF_VER=26.04.6
EOF
```

## 2. Nextflow 設定ファイルの取得

```bash
mkdir -p ~/nf-rnaseq && cd ~/nf-rnaseq

# このリポジトリの config を取得
curl -sSL -o nextflow.azure.config \
  https://raw.githubusercontent.com/nahisaho/spread1000-azure-quickstart/main/research-fields/life-pharma-science/04-transcriptomics-rnaseq/config/nextflow.azure.config

# 内容を確認 (envsubst で $AZURE_* が正しく展開されることを確認)
envsubst < nextflow.azure.config | head -40
```

## 3. デモ実行

```bash
cd ~/nf-rnaseq

# ログを tmux 内で残す (SSH 切断に強い)
tmux new -s rnaseq-demo

# tmux 内で実行:
nextflow run nf-core/rnaseq \
  -r 3.26.0 \
  -profile test \
  -c <(envsubst < nextflow.azure.config) \
  -w "az://omics/nf-work/demo-$(date +%Y%m%d-%H%M%S)" \
  --outdir "az://omics/results/demo-$(date +%Y%m%d-%H%M%S)"

# tmux から抜ける: Ctrl-b d
# 戻る: tmux attach -t rnaseq-demo
```

### 期待される動作

- 実行開始から **5〜10 分**: Nextflow が Azure Batch にプールを新規作成し (D8ds_v5 × 2 dedicated)、コンテナイメージを pull
- **10〜25 分**: FastQC → TrimGalore → STAR → Salmon → MultiQC の各プロセスが順次実行
- **25〜40 分以内に完了**: `Pipeline completed successfully` が表示され、autoscale で自動的にプールが 0 ノードに縮小

> [!TIP]
> **初回はコンテナ pull で 10 分以上かかる場合があります**。`deletePoolsOnCompletion = true` の設定ではプールが実行後に削除されるためノードのローカルキャッシュは保持されませんが、`nextflow run -resume` を使うと Blob 上の work ディレクトリのキャッシュから未変更プロセスをスキップできるため、パラメータ変更後の再実行は大幅に高速化されます。

### 正常終了の確認

Nextflow の最終出力に以下が含まれていれば成功:

```
Completed at: 2026-07-21T02:34:56.789Z
Duration    : 32m 15s
CPU hours   : 1.5
Succeeded   : 47
```

## 4. 結果の確認

```bash
# Blob 上の results ディレクトリを一覧
STORAGE=${AZURE_STORAGE_ACCOUNT}
LATEST_RESULT=$(az storage blob list \
  --account-name "$STORAGE" \
  --auth-mode login \
  --container-name omics \
  --prefix "results/demo-" \
  --query "[?ends_with(name,'multiqc_report.html')].name" -o tsv | tail -1)

echo "MultiQC report: az://omics/${LATEST_RESULT}"

# ローカルにダウンロード
az storage blob download \
  --account-name "$STORAGE" \
  --auth-mode login \
  --container-name omics \
  --name "$LATEST_RESULT" \
  --file /tmp/multiqc_report.html

# scp でローカル PC に転送してブラウザで開く (別ターミナル、ローカル PC から実行)
# scp azureuser@<Controller IP>:/tmp/multiqc_report.html ./
```

## 5. プールの状態確認

デモが完了したら、プールが 0 ノードに縮小されているか、削除されていることを確認:

```bash
az batch account login \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --name "$AZURE_BATCH_ACCOUNT"

az batch pool list \
  --query '[].{id:id,currentDedicated:currentDedicatedNodes,currentSpot:currentLowPriorityNodes,state:allocationState}' \
  -o table
```

- **プール一覧が空** (nf-azure 1.23.1 は `deletePoolsOnCompletion=true` により正常終了時にプールを削除します) → 課金停止 ✅
- **`currentDedicated: 0` かつ `currentSpot: 0` かつ `state: steady`** → 課金停止 ✅
- **`currentDedicated > 0` または `currentSpot > 0`** → 数十分経ってもノードが残っていれば `docs/05-cleanup.md` の緊急停止手順を参照 (Spot も dedicated と同じく課金対象です)

## 6. デモ実行のコスト実測

> [!NOTE]
> 以下は **ローカル PC (もしくは Cloud Shell)** で、Cost Management 参照権限のある元アカウントで実行してください。Controller VM の Managed Identity には Cost Management 参照権限はありません。

```bash
# 完了時点で 6-12 時間経過を待つ (Cost API 反映のため)
az consumption usage list \
  --start-date $(date -d '1 day ago' +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --query "[?tags.scenario=='rnaseq-nextflow'].{svc:instanceName,cost:pretaxCost,unit:usageQuantity}" \
  -o table
```

## チェックリスト

- [ ] `Pipeline completed successfully` メッセージが出た
- [ ] MultiQC HTML が Blob に生成された
- [ ] Batch プールの `currentDedicatedNodes: 0` かつ `currentLowPriorityNodes: 0` を確認 (Spot ノードも課金対象)
- [ ] 実行時間が 40 分以内 (初回は 60 分まで許容)

## 次のステップ

→ [04-real-data.md](04-real-data.md) — Human GRCh38 + 実 FASTQ で本番解析

## トラブルシューティング

問題が起きたら [troubleshooting.md](troubleshooting.md) を参照:

- コンテナ pull 失敗
- Batch pool `resizeTimeout` エラー
- SAS トークン期限切れ (`AuthenticationFailed`)
- ノードが 0 に戻らない (課金継続中)
