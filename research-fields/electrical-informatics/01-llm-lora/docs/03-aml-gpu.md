# 03: Azure ML T4 GPU での本番訓練

CPU スモークテストで動作を確認したら、Azure ML の T4 GPU (`Standard_NC4as_T4_v3`) で本番訓練を実行します。

> **参考値 (illustrative)**: Japan East PAYG 料金 約 $0.53/hr × 45 分 ≈ $0.40 (¥62)。
> 実際のコストは時期・リージョンにより変わります。[Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) で最新料金を確認してください。
> 料金日付基準: 2026-07、Japan East リージョン。

## 前提条件

- [01-prerequisites.md](01-prerequisites.md) の Azure 手順が完了していること
  - Azure サブスクリプション
  - **NCasT4_v3 の GPU クォータ ≥ 4 vCPU**（Japan East）
  - Azure ML ワークスペース（`infra/deploy.sh` で自動作成可）

## Step 0: インフラ自動プロビジョニング（推奨）

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/electrical-informatics/01-llm-lora"
cd "$SCENARIO_DIR"
bash infra/deploy.sh --prefix spread --location japaneast --rg rg-spread1000-e1
source .env   # RG, WS, LOC, KV_NAME, STORAGE_ACCOUNT
```

スクリプトは次を実行します:
1. リソースプロバイダ登録 (Microsoft.MachineLearningServices 他)
2. `infra/main.bicep` デプロイ (ワークスペース + Storage + KV + ACR + Log Analytics + App Insights)
3. GPU クォータ確認 (`az ml compute list-usage`)
4. カスタム AML 環境 `spread-lora-gpu:1` 登録
5. `.env` に接続情報を出力（シークレット無し、chmod 600）

## Step 1: Compute Cluster 作成

```bash
# infra/t4-cluster.yml を使用 (low_priority で約 50% 節約)
az ml compute create -f infra/t4-cluster.yml -g "$RG" -w "$WS"
```

または Azure ML Studio → **Compute → Compute clusters → + New**:

| 項目 | 値 |
|---|---|
| Location | Japan East |
| Virtual machine tier | **Low priority** (Spot; ≈50% 節約、ジョブが中断される場合あり) |
| Virtual machine type | GPU |
| Virtual machine size | `Standard_NC4as_T4_v3` (1× T4 16GB, 4 vCPU, 28 GB RAM) |
| Compute name | `t4-cluster` |
| Minimum number of nodes | **0** ← 使用しないときにゼロにして課金停止 |
| Maximum number of nodes | 1 |
| Idle time before scale down | 5 分（**注**: AML スキーマの既定値は 120 秒 = 2 分。ここでは 5 分に設定） |

> **Compute Instance vs Compute Cluster**:
> - **Compute Cluster** はジョブ実行時のみ起動し、アイドルで自動停止します（`min_instances=0`）。**本クイックスタートの推奨構成**です。Low-priority を設定でき、コストを下げられます。
> - **Compute Instance** は `CommandJob` のターゲットとしても指定可能ですが、スケールツーゼロせず、低優先度 (Spot) 設定も使えません。GPU クォータが不足していてインスタンスを常時起動する場合に使います。常時起動で放置すると ~$0.53/時間の課金が続きます。

## Step 2: カスタム環境の登録（deploy.sh 未使用の場合）

```bash
az ml environment create -f infra/environments/gpu/environment.yml -g "$RG" -w "$WS"
```

環境 `spread-lora-gpu:1` は以下を使用します:
- ベースイメージ: `mcr.microsoft.com/azureml/openmpi5.0-cuda12.4-ubuntu22.04:20260715.v1`
- 依存関係: `requirements-gpu.lock`（ハッシュ固定）

## Step 3: ジョブ提出 — 選択肢

### 方法 A: `az ml job` (CLI, おすすめ)

`train_job.yml` を確認:

```yaml
$schema: https://azuremlschemas.azureedge.net/latest/commandJob.schema.json
type: command

display_name: Phi-4-mini JP LoRA fine-tune
experiment_name: spread1000-e1-llm-lora

compute: azureml:t4-cluster
environment: azureml:spread-lora-gpu:1

code: ./
command: >-
  python src/prepare_data.py
  --builtin-dataset dolly-ja
  --dataset-revision 6391034b0126850543299cda071dc6281c31a6fb
  --n 1000
  --output train.jsonl &&
  python src/train_lora.py
  --model microsoft/Phi-4-mini-instruct
  --model-revision cfbefacb99257ffa30c83adab238a50856ac3083
  --dataset-revision 6391034b0126850543299cda071dc6281c31a6fb
  --data train.jsonl
  --epochs 3
  --batch-size 2
  --grad-accum 4
  --lr 2e-4
  --max-seq-length 512
  --lora-r 16
  --lora-alpha 32
  --output ${{outputs.adapter}}
  --max-gpu-hours 2.0
  --allow-long-run &&
  python src/verify.py
  --output ${{outputs.adapter}}

outputs:
  adapter:
    type: uri_folder
    mode: rw_mount

limits:
  timeout: 3600
```

> **YAML 注意**: `command: >-` の直後の行は必ず **同インデント** で続けてください（YAML folding 仕様）。追加の改行はスペースに折りたたまれ、インデントの深い行が別コマンドとして解釈されることはありません。

実行:
```bash
source .env   # RG, WS を読み込む
az ml job create --file train_job.yml -g "$RG" -w "$WS" --stream
```

`--stream` でリアルタイムログが確認できます（Ctrl+C で切断してもジョブは継続）。

**Low-priority (Spot) でジョブが中断された場合**: AML は自動リトライしません。以下でチェックポイントから再開できます:

```bash
# 最新チェックポイントを確認
az ml job download --name <JOB_NAME> --output-name adapter --all --download-path ./download/
# --resume-from-checkpoint を追加して再提出
# train_job.yml の command に --resume-from-checkpoint ${{inputs.checkpoint}} を追加して
# inputs.checkpoint に前回のアダプタ出力を渡す
```

### 方法 B: Notebook (`AzureML - PyTorch` カーネル)

```python
from azure.ai.ml import MLClient, command, Output
from azure.identity import DefaultAzureCredential

ml_client = MLClient.from_config(DefaultAzureCredential())

job = command(
    code="./",
    command=(
        "python src/prepare_data.py"
        " --builtin-dataset dolly-ja"
        " --dataset-revision 6391034b0126850543299cda071dc6281c31a6fb"
        " --n 1000 --output train.jsonl && "
        "python src/train_lora.py"
        " --model microsoft/Phi-4-mini-instruct"
        " --model-revision cfbefacb99257ffa30c83adab238a50856ac3083"
        " --dataset-revision 6391034b0126850543299cda071dc6281c31a6fb"
        " --data train.jsonl --epochs 3"
        " --output ${{outputs.adapter}}"
        " --max-gpu-hours 2.0 --allow-long-run && "
        "python src/verify.py --output ${{outputs.adapter}}"
    ),
    environment="azureml:spread-lora-gpu:1",
    compute="t4-cluster",
    outputs={"adapter": Output(type="uri_folder", mode="rw_mount")},
    display_name="phi4mini-ja-lora",
)

returned_job = ml_client.jobs.create_or_update(job)
print(f"Submitted: {returned_job.name}")
print(f"Studio URL: {returned_job.studio_url}")
```

## Step 4: 進捗確認

Azure ML Studio → **Jobs** → `phi4mini-ja-lora` → **Outputs + logs**

主要ログ:
- `std_log.txt` — `python src/train_lora.py` の全出力
- `70_driver_log.txt` — VM 側のドライバログ（GPU 認識、CUDA バージョン）

**成功パターン（参考値: T4 45 分の例）**:
```
[model] loading tokenizer for microsoft/Phi-4-mini-instruct @ cfbefacb...
[model] loading microsoft/Phi-4-mini-instruct (device=cuda, 4-bit=True)
[model] total parameters: 3,836,022,272
[data] train=900, eval=100 samples
[train] starting: epochs=3, batch=2x4, lr=0.0002, LoRA r=16
{'loss': 1.842, 'grad_norm': 1.98, 'learning_rate': 0.00019, 'epoch': 0.2}
...
{'eval_loss': 1.21, 'epoch': 1.0}
...
{'train_loss': 1.31, 'train_runtime': 2340.5, ...}
[verify] train_loss = 1.3100 — OK
[verify] ALL CHECKS PASSED
[train] saved LoRA adapter → outputs/adapter/final
```

## Step 5: アダプタのダウンロード

```bash
# outputs/adapter/ にアップロードされたファイルを取得
az ml job download --name <JOB_NAME> --output-name adapter --all --download-path ./download/
ls download/adapter/final/
# adapter_config.json  adapter_model.safetensors  tokenizer.json  manifest.json  metrics.json ...
```

## コスト目安

| 項目 | 単価 | 時間 | 参考費用 |
|---|---|---|---|
| Standard_NC4as_T4_v3 Low-priority (Japan East, PAYG) | 参考値 ~$0.27/hr | 45 分 | **参考値 ~$0.20** |
| Blob Storage (アダプタ 30MB, 1 日) | $0.02/GB/月 | — | <$0.01 |
| ネットワーク下り (30MB) | $0.087/GB (最初 100GB 無料枠) | — | $0 |
| **合計** | — | — | **参考値 ~$0.22 (¥34)** |

> ⚠️ **課金の落とし穴**: Compute Cluster の Idle scale-down（設定値 5 分; AML スキーマ既定は 120 秒）が効くまで課金は続きます。**必ずジョブ完了後にクラスタが 0 ノードに戻ったことを Studio で確認**してください。
> 詳細は [06-cleanup.md](06-cleanup.md) を参照。

## トラブルシューティング（GPU 特有）

| 症状 | 原因 | 対処 |
|---|---|---|
| `RuntimeError: bf16 is not supported on this GPU` | T4 で `bf16=True` を指定 | `train_lora.py` は `fp16=True, bf16=False` を強制済み。ログを確認 |
| CUDA OOM at batch step | 1000 サンプル + `batch=2` で稀に発生 | `--batch-size 1 --grad-accum 8` に、または `--max-seq-length 384` |
| `bitsandbytes not compiled with CUDA support` | 環境初期化が失敗 | `spread-lora-gpu:1` 環境を使用していることを確認。環境再ビルドを試みる |
| ジョブが Queued のまま | クォータ不足 or クラスタが 0 ノード | `az ml compute list-usage -g $RG -w $WS -l $LOC` でクォータ確認 |
| Low-priority ジョブが中断される | Spot VM のプリエンプション | `--resume-from-checkpoint` で再開。Dedicated tier への変更も検討 |
