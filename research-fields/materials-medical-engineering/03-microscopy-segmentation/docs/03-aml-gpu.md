# 03 — Azure ML GPU (T4) で高速実行 (任意)

256×256 で 500 枚以上、または 20 epoch を超えた学習を回したい場合、Azure ML の Compute Instance に T4 GPU を割り当てて実行します。

> ⚠️ **CPU で十分な場合は Azure 不要です**。128×128 × 200 枚 × 10 epochs はローカル CPU で 1〜3 分（[02-cpu-quickstart.md](02-cpu-quickstart.md)）。GPU が必要か検討してから進んでください。

## 事前準備: GPU クォータ申請

同じフィールドの [D-2 の 03-aml-gpu.md](../../02-nnp-mace-mp/docs/03-aml-gpu.md) を参照してください。`Standard NCASv3_T4 Family vCPUs` を **4 vCPUs** 申請します。承認まで数時間〜2 営業日。

## Compute Instance の作成 (Studio UI)

1. Azure ML Studio → 「Compute」→ 「Compute instances」→ 「+ New」
2. **VM size**: `Standard_NC4as_T4_v3`
3. **⚠️ Idle shutdown**: 必ず「Enable idle shutdown」→ `60 minutes`
4. **Image**: 最新の `AzureML pytorch cuda12` 系
5. 起動 3〜5 分

## セットアップと実行

```bash
# Compute Instance に SSH または Jupyter Terminal から
python3.10 -m venv ~/microseg-env
source ~/microseg-env/bin/activate

# PyTorch 2.7.1 CUDA 12.1
pip install --upgrade pip
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu126

python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# → True Tesla T4

# 本リポジトリを clone
git clone https://github.com/<your-fork>/spread1000-azure-quickstart.git
cd spread1000-azure-quickstart/research-fields/materials-medical-engineering/03-microscopy-segmentation
pip install -r requirements.txt

# GPU で 256×256 x 500 枚 x 20 epochs
python src/train.py --task grains --image-size 256 \
  --n-train 500 --n-val 100 --epochs 20 \
  --batch-size 16 --device cuda --output data/
```

## GPU での期待時間 (T4, 256×256 x 500 枚)

| ステップ | 時間 |
|---|---:|
| 依存パッケージインストール | 2〜5 分 |
| データ生成 (500+100 枚, 256×256) | 30〜90 秒 |
| 1 エポック | 5〜15 秒 |
| **20 エポック合計** | **2〜5 分** |
| モンタージュ + JSON | < 10 秒 |
| **セッション合計** (セットアップ込み) | **10〜30 分** |
| **課金** (PAYG $0.71/hr) | **< $0.35** |

## Azure ML CommandJob 版 (バッチ実行)

**Compute Cluster を先に作る** (Compute Instance は CommandJob に使えません):
```bash
az ml compute create --type amlcompute --name gpu-cluster-nc4t4 \
  --size Standard_NC4as_T4_v3 --min-instances 0 --max-instances 1 \
  --idle-time-before-scale-down 300 \
  --workspace-name <ws-name> --resource-group <rg-name>
```

SDK で submit (出力を必ず `Output(type=URI_FOLDER)` にする):

```python
from azure.ai.ml import MLClient, command, Output
from azure.ai.ml.constants import AssetTypes
from azure.identity import DefaultAzureCredential

ml_client = MLClient.from_config(credential=DefaultAzureCredential())

job = command(
    code="./",
    command=(
        "pip install torch==2.7.1 torchvision==0.22.1 "
        "--index-url https://download.pytorch.org/whl/cu126 && "
        "pip install -r requirements.txt && "
        "python src/train.py --task grains --image-size 256 "
        "--n-train 500 --n-val 100 --epochs 20 --batch-size 16 "
        "--device cuda --output ${{outputs.results}}"
    ),
    outputs={
        "results": Output(type=AssetTypes.URI_FOLDER, mode="rw_mount"),
    },
    environment="AzureML-pytorch-2.2-ubuntu22.04-py310-cuda12@latest",
    compute="gpu-cluster-nc4t4",
    display_name="microscopy-unet-demo",
    experiment_name="microscopy-segmentation",
)
returned_job = ml_client.jobs.create_or_update(job)
print(returned_job.studio_url)
```

> ⚠️ **outputs を指定しないと**、コンピュートが解放されると `data/` に書いた結果が消えます。上記のように `${{outputs.results}}` を `--output` に渡してください。ジョブ完了後 Studio の Job details → Outputs から結果をダウンロードできます。

## コスト目安 (Japan East)

| 項目 | PAYG | Spot |
|---|---:|---:|
| `NC4as_T4_v3` VM | $0.71/hr | ~$0.21/hr |
| OS ディスク (128 GB Std SSD) | $0.009/hr | 同左 |
| **30 分セッション合計** | **~$0.36** | **~$0.11** |
| 1 日放置 (自動停止忘れ) | **$17.28** ⚠️ | **~$5** |

## 後片付け

[06-cleanup.md](06-cleanup.md) の手順で必ず Compute Instance を停止 or 削除してください。
