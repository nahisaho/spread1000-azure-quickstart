# 03: Azure ML T4 GPU での本番訓練

CPU スモークテストで動作を確認したら、Azure ML の T4 GPU (`Standard_NC4as_T4_v3`) で本番訓練を実行します。所要時間 30〜45 分、コスト約 $0.40 (¥62)。

## 前提条件

- [01-prerequisites.md](01-prerequisites.md) の Azure 手順が完了していること
  - Azure サブスクリプション
  - **NCasT4_v3 の GPU クォータ ≥ 4 vCPU**（Japan East）
  - Azure ML ワークスペース

## Step 1: Compute Cluster 作成

Azure ML Studio → **Compute → Compute clusters → + New**

| 項目 | 値 |
|---|---|
| Location | Japan East |
| Virtual machine tier | Dedicated |
| Virtual machine type | GPU |
| Virtual machine size | `Standard_NC4as_T4_v3` (1× T4 16GB, 4 vCPU, 28 GB RAM) |
| Compute name | `t4-cluster` |
| Minimum number of nodes | **0** ← 使用しないときにゼロにして課金停止 |
| Maximum number of nodes | 1 |
| Idle time before scale down | 5 分 (推奨) |

> **重要**: Compute Instance（常時起動）ではなく、必ず **Compute Cluster**（ジョブ実行時のみ起動、アイドルで自動停止）を使ってください。誤って Compute Instance を作ると、放置で $0.53/時間の課金が続きます。

## Step 2: ジョブ提出 — 選択肢

### 方法 A: `az ml job` (CLI, おすすめ)

`train_job.yml` を作成:

```yaml
$schema: https://azuremlschemas.azureedge.net/latest/commandJob.schema.json
type: command
name: phi4mini-ja-lora
display_name: Phi-4-mini JP LoRA fine-tune
description: QLoRA 4-bit SFT on databricks-dolly-15k-ja (1000 samples, 3 epochs)

compute: azureml:t4-cluster
environment: azureml://registries/azureml/environments/acpt-pytorch-2.2-cuda12.1/labels/latest
  # 現行の curated 環境名を確認するには:
  #   az ml environment list --registry-name azureml --query "[?contains(name,'pytorch')].name" -o tsv
  # 詳細: https://learn.microsoft.com/azure/machine-learning/resource-curated-environments

code: ./
command: >-
  pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu126 &&
  pip install -r requirements-gpu.txt &&
  python src/prepare_data.py --n 1000 --output /tmp/train.jsonl &&
  python src/train_lora.py
    --model microsoft/Phi-4-mini-instruct
    --data /tmp/train.jsonl
    --epochs 3
    --batch-size 2 --grad-accum 4
    --lr 2e-4
    --max-seq-length 512
    --lora-r 16 --lora-alpha 32
    --output ${{outputs.adapter}}

outputs:
  adapter:
    type: uri_folder
    mode: rw_mount
```

実行:
```bash
az login
az account set --subscription <YOUR_SUBSCRIPTION_ID>
az configure --defaults workspace=<YOUR_WORKSPACE> group=<YOUR_RG>
az ml job create --file train_job.yml --stream
```

`--stream` でリアルタイムログが確認できます（Ctrl+C で切断してもジョブは継続）。

### 方法 B: Notebook (`AzureML - PyTorch` カーネル)

Azure ML Studio → **Notebooks** で新規 `.ipynb` を作成し、以下を実行:

```python
from azure.ai.ml import MLClient, command, Input, Output
from azure.ai.ml.entities import Environment
from azure.identity import DefaultAzureCredential

ml_client = MLClient.from_config(DefaultAzureCredential())

job = command(
    code="./",
    command=(
        "pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu126 && "
        "pip install -r requirements-gpu.txt && "
        "python src/prepare_data.py --n 1000 --output /tmp/train.jsonl && "
        "python src/train_lora.py --data /tmp/train.jsonl --epochs 3 "
        "--output ${{outputs.adapter}}"
    ),
    environment="azureml://registries/azureml/environments/acpt-pytorch-2.2-cuda12.1/labels/latest",
    compute="t4-cluster",
    outputs={"adapter": Output(type="uri_folder", mode="rw_mount")},
    display_name="phi4mini-ja-lora",
)

returned_job = ml_client.jobs.create_or_update(job)
print(f"Submitted: {returned_job.name}")
print(f"Studio URL: {returned_job.studio_url}")
```

## Step 3: 進捗確認

Azure ML Studio → **Jobs** → `phi4mini-ja-lora` → **Outputs + logs**

主要ログ:
- `std_log.txt` — `python src/train_lora.py` の全出力
- `70_driver_log.txt` — VM 側のドライバログ（GPU 認識、CUDA バージョン）

**成功パターン（T4 45 分の例）**:
```
[model] loading tokenizer for microsoft/Phi-4-mini-instruct
[model] loading microsoft/Phi-4-mini-instruct (device=cuda, 4-bit=True)
[model] total parameters: 3,836,022,272
[data] loading /tmp/train.jsonl
[data] 1000 prompt/completion samples
[train] starting: epochs=3, batch=2x4, lr=0.0002, LoRA r=16
{'loss': 1.842, 'grad_norm': 1.98, 'learning_rate': 0.00019, 'epoch': 0.2}
{'loss': 1.523, 'grad_norm': 1.62, 'learning_rate': 0.00017, 'epoch': 0.6}
...
{'loss': 1.104, 'grad_norm': 0.94, 'learning_rate': 0.00001, 'epoch': 2.8}
{'train_runtime': 2340.5, 'train_samples_per_second': 1.28, 'train_loss': 1.31, ...}
[train] saved LoRA adapter → outputs/adapter/final
```

## Step 4: アダプタのダウンロード

```bash
# outputs/adapter/ にアップロードされたファイルを取得
az ml job download --name <JOB_NAME> --output-name adapter --download-path ./download/
ls download/adapter/final/
# adapter_config.json  adapter_model.safetensors  tokenizer.json  ...
```

## コスト目安

| 項目 | 単価 | 時間 | 費用 |
|---|---|---|---|
| Standard_NC4as_T4_v3 (Japan East, PAYG) | ~$0.53/hr | 45 分 | **$0.40** |
| Blob Storage (アダプタ 30MB, 1 日) | $0.02/GB/月 | — | <$0.01 |
| ネットワーク下り (30MB) | $0.087/GB (最初 100GB無料枠) | — | $0 |
| **合計** | — | — | **~$0.42 (¥65)** |

> ⚠️ **課金の落とし穴**: Compute Cluster の Idle scale-down（既定 5 分）が効くまで課金は続きます。**必ずジョブ完了後にクラスタが 0 ノードに戻ったことを Studio で確認**してください。手動で確実に停止するには [06-cleanup.md](06-cleanup.md) を参照。

## トラブルシューティング（GPU 特有）

| 症状 | 原因 | 対処 |
|---|---|---|
| `RuntimeError: bf16 is not supported on this GPU` | T4 で `bf16=True` を指定 | `train_lora.py` は `fp16=True, bf16=False` を強制済み。ログを確認 |
| CUDA OOM at batch step | 1000 サンプル + `batch=2` で稀に発生 | `--batch-size 1 --grad-accum 8` に、または `--max-seq-length 384` |
| `bitsandbytes not compiled with CUDA support` | curated 環境の初期化が失敗 | `pip install bitsandbytes==0.49.2 --force-reinstall` を command に追加 |
| ジョブが Queued のまま | クォータ不足 or クラスタが 0 ノード | Quota 画面で NCasT4v3 vCPU 使用量を確認 |
