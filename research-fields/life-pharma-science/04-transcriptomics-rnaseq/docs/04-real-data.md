# 04. 本番実行 (実データ + Human GRCh38 + GENCODE v50)

デモが通ったら、実データ (自分の FASTQ) と実リファレンス (Human GRCh38 + GENCODE v50) を使った本番解析に進みます。

## 1. リファレンスの準備 (初回のみ、約 1〜2 時間)

nf-core/rnaseq は STAR/Salmon などのインデックスを、実行時に必要なら自動生成します。ここでは **最初の本番実行時に `--save_reference` フラグでインデックスを生成し Blob に保存**、以降の実行では再利用します (追加のダミー実行は不要)。

### 1.1 GENCODE から FASTA/GTF をダウンロード

```bash
# Controller VM 上で
mkdir -p ~/refs/human-grch38 && cd ~/refs/human-grch38

# Primary assembly FASTA (~3 GB gzipped)
wget https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_50/GRCh38.primary_assembly.genome.fa.gz

# GTF annotation (v50、~50 MB gzipped)
wget https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_50/gencode.v50.primary_assembly.annotation.gtf.gz

# Blob にアップロード
az storage blob upload \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --auth-mode login \
  --container-name omics \
  --name "references/human-grch38/genome.fa.gz" \
  --file GRCh38.primary_assembly.genome.fa.gz

az storage blob upload \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --auth-mode login \
  --container-name omics \
  --name "references/human-grch38/gencode.v50.annotation.gtf.gz" \
  --file gencode.v50.primary_assembly.annotation.gtf.gz
```

出典・ライセンス: GENCODE データは open access。研究論文では **release 番号 (v50) と取得日** を必ず記録してください。参考: https://www.gencodegenes.org/pages/data_access.html

### 1.2 インデックス生成の方針

nf-core/rnaseq では以下のいずれかを選びます:

- **方針 A (推奨)**: 最初の本番解析 (手順 4) で `--save_reference` を付けて実行すると、STAR/Salmon インデックスが `results/${RUN_ID}/genome/index/` に自動保存されます。2 回目以降は `--star_index` / `--salmon_index` で再利用可能。
- **方針 B**: 完全に別実行としてインデックスを構築 (手順 4 に進む前にインデックスを揃えたい場合)。この場合は 1 サンプル分の小さな FASTQ を使い、`--save_reference` で実行してください。

初回だけ index 構築を含めた実行時間 (方針 A): E16ds_v5 × 6 で 3.5〜4.5 時間 (通常運転 +1 時間)、追加費用 約 +¥1,350。

## 2. 実データ (FASTQ) のアップロード

> [!CAUTION]
> **本テンプレートの既定構成は「公開可能な非個人情報 RNA-Seq」向けです。**
>
> ヒト由来 FASTQ は個人識別可能情報 (PHI) に該当する可能性があり、以下いずれかに
> 該当する場合は本テンプレートを **そのまま使ってはなりません**:
> - **dbGaP controlled-access** データ (Data Use Certification が必要、NIH Trusted Partner 環境が推奨)
> - 患者由来検体で **次世代医療基盤法 / GDPR / HIPAA 等の対象**
> - 未同意の患者データ、あるいは検体番号→患者 ID を復元可能な状態
>
> 該当する場合は次のいずれかを実施してください:
> 1. **所属機関 IRB / 倫理委員会** および **セキュリティ委員会** の事前承認を取得
> 2. **Azure Landing Zone (Confidential compute / Private endpoints only)** を構築し、
>    - Storage account は `publicNetworkAccess: 'Disabled'` + Private Endpoint
>    - Controller VM は Bastion 経由アクセスのみ (`infra/main.bicep:117-133` の SSH 公開を無効化)
>    - Batch pool は VNet 内 subnet 配置 + NSG で送受信を制限
>    - 顧客管理鍵 (CMK) による Storage 暗号化
> 3. **Controller VM の `~/raw-fastq/` を解析完了後に必ず削除** (残置防止スクリプトは
>    cleanup 手順 05 に含まれるが、controlled data では追加で監査ログを取得)
> 4. 生 FASTQ ではなく **de-identified counts のみ** をクラウドにアップロード
>
> 判断に迷う場合は **アップロード前に** 所属機関 IRB へ相談してください。

```bash
# Controller VM 上で作業ディレクトリを作る
mkdir -p ~/raw-fastq && cd ~/raw-fastq

# ローカル PC から scp で送る (別ターミナル)
# scp *.fastq.gz azureuser@<Controller IP>:~/raw-fastq/

# Blob にアップロード (並列転送、失敗を検出)
pids=()
for f in *.fastq.gz; do
  az storage blob upload \
    --account-name "$AZURE_STORAGE_ACCOUNT" \
    --auth-mode login \
    --container-name omics \
    --name "raw-fastq/project-001/$f" \
    --file "$f" \
    --overwrite &
  pids+=($!)
done

fail=0
for pid in "${pids[@]}"; do
  wait "$pid" || fail=$((fail + 1))
done
if [[ $fail -gt 0 ]]; then
  echo "ERROR: $fail 件のアップロードが失敗しました。再実行してください。" >&2
  exit 1
fi
```

## 3. サンプルシート作成

このリポジトリの `examples/samplesheet.csv` をテンプレートとして `~/nf-rnaseq/samplesheet.csv` を作成し、Blob の `az://` URL を編集します。

```bash
# 03-run-demo.md で ~/nf-rnaseq を作成済みの前提
cd ~/nf-rnaseq
curl -fsSL -o samplesheet.csv \
  https://raw.githubusercontent.com/nahisaho/spread1000-azure-quickstart/main/research-fields/life-pharma-science/04-transcriptomics-rnaseq/examples/samplesheet.csv
$EDITOR samplesheet.csv
```

内容例:

```csv
sample,fastq_1,fastq_2,strandedness
CTRL_1,az://omics/raw-fastq/project-001/CTRL_1_R1.fastq.gz,az://omics/raw-fastq/project-001/CTRL_1_R2.fastq.gz,auto
CTRL_2,az://omics/raw-fastq/project-001/CTRL_2_R1.fastq.gz,az://omics/raw-fastq/project-001/CTRL_2_R2.fastq.gz,auto
CTRL_3,az://omics/raw-fastq/project-001/CTRL_3_R1.fastq.gz,az://omics/raw-fastq/project-001/CTRL_3_R2.fastq.gz,auto
TREAT_1,az://omics/raw-fastq/project-001/TREAT_1_R1.fastq.gz,az://omics/raw-fastq/project-001/TREAT_1_R2.fastq.gz,auto
TREAT_2,az://omics/raw-fastq/project-001/TREAT_2_R1.fastq.gz,az://omics/raw-fastq/project-001/TREAT_2_R2.fastq.gz,auto
TREAT_3,az://omics/raw-fastq/project-001/TREAT_3_R1.fastq.gz,az://omics/raw-fastq/project-001/TREAT_3_R2.fastq.gz,auto
```

- `strandedness=auto` は Salmon が自動判定 (推奨)
- 同じ `sample` の複数行は technical replicate として結合されます

Blob にアップロード:

```bash
az storage blob upload \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --auth-mode login \
  --container-name omics \
  --name "samplesheets/project-001.csv" \
  --file ~/nf-rnaseq/samplesheet.csv
```

## 4. 本番解析実行 (初回は index 構築込み)

```bash
cd ~/nf-rnaseq

# tmux セッションを起動 (以降のコマンドは tmux 内で実行)
tmux new -s rnaseq-prod

# tmux 内で RUN_ID を定義 (外側のシェル変数は tmux に引き継がれないため、
# 必ず tmux 内で定義する)
RUN_ID=project-001-$(date +%Y%m%d-%H%M%S)

# (初回実行 — index を保存)
# nextflow.azure.config で process.executor='azurebatch' を設定済みのため
# -profile azurebatch (nf-core 側のリモートプロファイル) は指定しません。
nextflow run nf-core/rnaseq \
  -r 3.26.0 \
  -c <(envsubst < nextflow.azure.config) \
  --input "az://omics/samplesheets/project-001.csv" \
  --fasta "az://omics/references/human-grch38/genome.fa.gz" \
  --gtf "az://omics/references/human-grch38/gencode.v50.annotation.gtf.gz" \
  --gencode \
  --aligner star_salmon \
  --save_reference \
  -w "az://omics/nf-work/${RUN_ID}" \
  --outdir "az://omics/results/${RUN_ID}"

# tmux から抜ける: Ctrl-b d
# 進捗確認: tmux attach -t rnaseq-prod
```

> [!IMPORTANT]
> **`--gencode` は GENCODE FASTA/GTF を使う場合は必須**です。付けないと featureCounts が `gene_biotype` を探して失敗し、Salmon 用の GENCODE 命名規則も適用されません。

初回実行後、`az://omics/results/${RUN_ID}/genome/index/star/` と `genome/index/salmon/` にインデックスが保存されます。

### 2 回目以降 (index 再利用)

```bash
REF_RUN_ID=project-001-20260721-...   # 初回の RUN_ID
NEW_RUN_ID=project-002-$(date +%Y%m%d-%H%M%S)

nextflow run nf-core/rnaseq \
  -r 3.26.0 \
  -c <(envsubst < nextflow.azure.config) \
  --input "az://omics/samplesheets/project-002.csv" \
  --fasta "az://omics/references/human-grch38/genome.fa.gz" \
  --gtf "az://omics/references/human-grch38/gencode.v50.annotation.gtf.gz" \
  --gencode \
  --star_index "az://omics/results/${REF_RUN_ID}/genome/index/star/" \
  --salmon_index "az://omics/results/${REF_RUN_ID}/genome/index/salmon/" \
  --aligner star_salmon \
  -w "az://omics/nf-work/${NEW_RUN_ID}" \
  --outdir "az://omics/results/${NEW_RUN_ID}"
```

### 期待される実行時間 (dedicated)

| ノード構成 | サンプル数 | 完了時間目安 |
|---|---:|---|
| E16ds_v5 × 4 | 6 samples × 40M PE | 3〜4 時間 |
| E16ds_v5 × 6 | 6 samples × 40M PE | 2〜3 時間 |
| E16ds_v5 × 8 | 12 samples × 40M PE | 3〜4 時間 |

Spot インスタンスの場合、eviction による再実行を考慮して +30〜60% の時間バッファを見込んでください。

## 5. Spot ノードでコストを抑える

`nextflow.azure.config` の `pools.auto` セクションに以下を追加すると、**auto-pool のノードをすべて Spot (low-priority) にできます**:

```groovy
azure {
    batch {
        pools {
            auto {
                autoScale = true
                vmCount = 1
                maxVmCount = 6
                lowPriority = true    // ← このプールの全ノードが Spot になる
            }
        }
    }
}
```

> [!IMPORTANT]
> `lowPriority = true` は **auto-pool の全ノードを Spot に切り替える**設定で、「dedicated と Spot の混在」ではありません。
>
> **nf-azure の auto-pool モード (`autoPoolMode = true`) では `process.queue` は無視されます。**
> STAR など長時間タスクだけ dedicated にしたい場合は、次のように **auto-pool を無効化して
> 名前付きプールを 2 つ定義** し、`process.<NAME>.queue` でルーティングしてください:
>
> ```groovy
> azure.batch {
>     autoPoolMode = false
>     allowPoolCreation = true       // 存在しなければ Nextflow が作る
>     deletePoolsOnCompletion = false // 手動 cleanup を推奨 (下記の共存問題も回避)
>     pools {
>         'spot-pool' {
>             vmType = 'Standard_E16ds_v5'
>             autoScale = true; maxVmCount = 6; lowPriority = true
>         }
>         'dedicated-pool' {
>             vmType = 'Standard_E16ds_v5'
>             autoScale = true; maxVmCount = 2; lowPriority = false
>         }
>     }
> }
> process {
>     queue = 'spot-pool'                    // 既定
>     withName: 'STAR_ALIGN' { queue = 'dedicated-pool' }
> }
> ```
>
> `autoPoolMode = true` のまま `process.queue` を書いても効かない点に注意。

Spot のメリット/デメリット:

- **メリット**: 6 サンプル本番が dedicated ¥4,053 → Spot 約 ¥800 に削減
- **デメリット**: 数時間のうちに予告なく evict される可能性あり (再実行される)
- **推奨用途**: FastQC / Salmon など短時間タスク。長時間 STAR は dedicated のほうが安全

## 6. 結果の解釈

パイプライン完了後、以下のファイルを確認:

- `results/${RUN_ID}/multiqc/multiqc_report.html` — 全サンプルの QC サマリ
- `results/${RUN_ID}/star_salmon/salmon.merged.gene_counts_length_scaled.tsv` — **DE 解析入力に推奨** (tximport で transcript-length scaling 済みの gene-level counts)
- `results/${RUN_ID}/star_salmon/salmon.merged.gene_counts.tsv` — raw counts (length scaling なし、通常は上記を優先)
- `results/${RUN_ID}/star_salmon/salmon.merged.gene_tpm.tsv` — TPM (可視化・比較用)
- `results/${RUN_ID}/star_salmon/deseq2_qc/` — DESeq2 による PCA/sample-to-sample プロット (QC のみ、統計 p 値なし)

> [!IMPORTANT]
> **差次的発現解析 (DE, log2FC/adj.p) はこのパイプラインには含まれません**。別途以下のいずれかを実行:
>
> - [nf-core/differentialabundance](https://nf-co.re/differentialabundance) パイプライン (推奨、同じ Azure Batch で流せます)
> - 自分の R/Python 環境で DESeq2 / edgeR / limma-voom を `salmon.merged.gene_counts_length_scaled.tsv` に対して実行
>
> DESeq2 の入力は **`salmon.merged.gene_counts_length_scaled.tsv`** (tximport で length-scaled 済み gene counts) と対応するメタデータ (condition 列) を推奨します。生の `gene_counts.tsv` は transcript 長オフセットを含まないため、遺伝子間比較でバイアスが出る可能性があります。参考: [nf-core/rnaseq output docs](https://nf-co.re/rnaseq/3.26.0/docs/output)

## 7. コスト実測

> [!NOTE]
> このセクションのコマンドは **ローカル PC (もしくは Cloud Shell)** で、Cost Management に権限のある元アカウントで実行してください。Controller VM の Managed Identity には Cost Management 参照権限はありません。

Cost Management API はリソースグループ単位でクエリするのが確実です:

```bash
# 実行完了から 12〜24 時間後 (Cost Management API 反映後)
export AZURE_RESOURCE_GROUP=rg-spread1000-rnaseq-tanaka  # ← 自分の値
SUB=$(az account show --query id -o tsv)
az costmanagement query \
  --type ActualCost \
  --timeframe MonthToDate \
  --scope "/subscriptions/$SUB/resourceGroups/$AZURE_RESOURCE_GROUP" \
  --dataset-granularity None \
  --dataset-aggregation '{"totalCost":{"name":"PreTaxCost","function":"Sum"}}' \
  --dataset-grouping name=ServiceName type=Dimension \
  -o table
```

または Azure Portal → **コスト管理 + 請求** → **コスト分析** で当該リソースグループにスコープを絞って確認してください。

## 8. 差次的発現解析 (DE) を続ける場合

RNA-Seq パイプライン自体は counts/TPM のみ出力します。DE 解析を Azure 上で続ける場合は、**クリーンアップ (docs/05) を実行する前に** 以下のいずれかを実施してください。

### 選択肢 A: nf-core/differentialabundance (Controller VM 上、同じ Batch アカウント)

nf-core/differentialabundance には別途 samplesheet と contrasts CSV が必要です。詳しくは [公式 usage](https://nf-co.re/differentialabundance/1.5.0/docs/usage) を参照。

`samplesheet_de.csv` (最低限):
```csv
sample,condition
CTRL_1,ctrl
CTRL_2,ctrl
CTRL_3,ctrl
TREAT_1,treat
TREAT_2,treat
TREAT_3,treat
```

`contrasts.csv` は §8 で `blocking` カラム込みの完全な形式を示します。詳しくは [公式 usage](https://nf-co.re/differentialabundance/1.5.0/docs/usage) を参照。

```bash
上記を `az://omics/de-inputs/` にアップロードしたうえで、**Controller VM 上で**:

> [!WARNING]
> **同一 Batch アカウントで rnaseq 解析と DE 解析を同時に走らせてはいけません。**
>
> nf-azure の auto-pool ID は「VM SKU + オプション」で決まるため、同じ SKU を要求する
> 2 実行が同一 Batch アカウント上で並行すると **同じプールを共有**します。
> かつ `deletePoolsOnCompletion=true` (auto-pool の既定) では、
> **どちらかが完了した瞬間にもう片方の実行中プールも削除されます**。
> 対策:
> - **serialize** して片方が完全に完了してから次を走らせる (最も安全)
> - もしくは **別の Batch アカウント** を用意して独立させる
> - もしくは auto-pool を無効化し (上記 §5 参照)、`deletePoolsOnCompletion=false` にして
>   pool 名を明示的に分離 (`spot-pool-rnaseq`, `spot-pool-de` 等)

`contrasts.csv` (nf-core/differentialabundance 1.5.0 は `blocking` カラムを要求 -
未指定でも empty を含めないと `.replace()` で AttributeError になる):
```csv
id,variable,reference,target,blocking
treat_vs_ctrl,condition,ctrl,treat,
```

```bash
# 事前に固定 RUN_ID を定義 (再実行時に -resume で同じ work dir を再利用可能に)
export DE_RUN_ID="de-$(date +%Y%m%d-%H%M%S)"
# Controller VM 上で実行 (必ず前実行が完了してから!)
cd ~/nf-rnaseq
nextflow run nf-core/differentialabundance \
  -r 1.5.0 \
  -c <(envsubst < nextflow.azure.config) \
  --input "az://omics/de-inputs/samplesheet_de.csv" \
  --matrix "az://omics/results/project-001-.../star_salmon/salmon.merged.gene_counts_length_scaled.tsv" \
  --contrasts "az://omics/de-inputs/contrasts.csv" \
  -profile rnaseq \
  -w "az://omics/nf-work/${DE_RUN_ID}" \
  --outdir "az://omics/results/${DE_RUN_ID}"
# -resume で再開したいときは同じ DE_RUN_ID を export してから -resume を付けて再実行
```

### 選択肢 B: ローカルで DESeq2 (R) を実行

`salmon.merged.gene_counts_length_scaled.tsv` をローカル PC にダウンロードし、R で DESeq2 workflow を実行 (length-scaled counts は tximport 済みで DESeq2 に安全に渡せます)。

```r
library(DESeq2)
# nf-core/rnaseq 3.26 の出力には gene_id (行名) と gene_name (メタデータ列) が含まれる。
# DESeq2 に渡すのは数値列のみにする必要がある。
tbl <- read.table(
  "salmon.merged.gene_counts_length_scaled.tsv",
  header = TRUE, sep = "\t", check.names = FALSE
)
rownames(tbl) <- tbl$gene_id
counts <- as.matrix(tbl[, setdiff(names(tbl), c("gene_id", "gene_name"))])
counts <- round(counts)             # まず四捨五入
storage.mode(counts) <- "integer"   # そのうえで整数化 (DESeq2 の入力要件)

coldata <- data.frame(
  row.names = colnames(counts),
  condition = factor(c("ctrl","ctrl","ctrl","treat","treat","treat"),
                     levels = c("ctrl","treat"))
)
dds <- DESeqDataSetFromMatrix(countData = counts, colData = coldata, design = ~condition)
dds <- DESeq(dds)
res <- results(dds)
write.csv(as.data.frame(res), "de_results.csv")
```

## 次のステップ

→ [05-cleanup.md](05-cleanup.md) — プール停止、Blob ライフサイクル、リソース削除
