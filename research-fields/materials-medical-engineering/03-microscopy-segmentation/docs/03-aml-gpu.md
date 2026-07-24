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

> **注**: スポットインスタンスは AML では `--tier low_priority` (Compute Cluster) で表現します。`job_tier: spot` は無効です。Compute Instance は CommandJob のターゲットとしても使用できますが、低優先度はクラスターのみです。

**Compute Cluster を先に作る** (low_priority クラスター):
```bash
source .env  # infra/deploy.sh が生成した .env を読み込む

az ml compute create --type amlcompute --name gpu-cluster-nc4t4 \
  --size Standard_NC4as_T4_v3 --min-instances 0 --max-instances 1 \
  --tier low_priority \
  --idle-time-before-scale-down 300 \
  -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME"
```

**環境を登録する** (カスタム Docker イメージ、浮動 `@latest` 不使用):
```bash
az ml environment create \
  --file infra/environments/gpu/environment.yml \
  -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME"
```

**ジョブを投入する** (YAML を使用):
```bash
az ml job create --file azureml/train_job.yml \
  -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME"
```

> ⚠️ **outputs を指定しないと**、コンピュートが解放されると `data/` に書いた結果が消えます。`train_job.yml` では `${{outputs.results}}` を `--output` に渡しているので安全です。

## コスト目安 (Japan East)

| 項目 | Dedicated | Low-priority (クラスター) |
|---|---:|---:|
| `NC4as_T4_v3` VM | $0.71/hr | ~$0.21/hr |
| OS ディスク (128 GB Std SSD) | $0.009/hr | 同左 |
| **30 分セッション合計** | **~$0.36** | **~$0.11** |
| 1 日放置 (自動停止忘れ) | **$17.28** ⚠️ | **~$5** |

> ※ 低優先度ノードは AML が容量不足時に中断 (プリエンプション) する場合があります。重要な長時間実験には Dedicated を使用してください。  
> ※ 価格は変動します。最新価格は [Azure Retail Prices API](https://prices.azure.com/api/retail/prices?$filter=armRegionName%20eq%20%27japaneast%27%20and%20serviceName%20eq%20%27Virtual%20Machines%27) で確認してください（取得日確認が必要）。

## 後片付け

[06-cleanup.md](06-cleanup.md) の手順で必ず Compute Instance を停止 or 削除してください。
