# 03 — Azure ML GPU (T4) で高速実行 (任意)

大きな系（100+ 原子）や長時間 MD（10+ ps）を回したい場合、Azure ML の Compute Instance に T4 GPU を割り当てて実行します。

> ⚠️ **CPU で十分な場合は Azure 不要です。** 8〜32 原子 Si の緩和・短時間 MD はローカル CPU（[02-cpu-quickstart.md](02-cpu-quickstart.md)）で完結します。GPU が本当に必要か検討してから進んでください。

## 事前準備: GPU クォータ申請

**新規 Azure サブスクリプションでは GPU クォータがゼロ**です。以下を先に申請します。

1. Azure Portal → 「サブスクリプション」→ 対象サブスクリプション → 「使用量 + クォータ」
2. プロバイダー: **Machine Learning**、リージョン: **Japan East**、SKU ファミリ: **Standard NCASv3_T4 Family vCPUs** を選択
3. 「割り当ての増加を要求」→ **4 vCPUs** を要求（`NC4as_T4_v3` に必要）
4. **承認までに数時間〜2 営業日** かかることがあります

参考: https://learn.microsoft.com/ja-jp/azure/machine-learning/how-to-manage-quotas

代替 SKU: `Standard_NC8as_T4_v3`（同じ T4、8 vCPU）や `Standard_NC24ads_A100_v4`（より高性能）も同時申請しておくと通りやすい場合があります。

## Azure ML ワークスペース + Compute Instance の作成

**Azure ML ワークスペースが未作成の場合**、`life-pharma-science/01-molecular-generation-tamgen/infra/` の Bicep が同等の構成（ワークスペース + Compute Instance）を提供しています。それを参考にしてください。

**Azure Portal / Studio UI から手動作成する場合**:

1. Azure ML Studio → 「Compute」→ 「Compute instances」→ 「+ New」
2. **VM size**: `Standard_NC4as_T4_v3`
3. **Idle shutdown**: ⚠️ **必ず「Enable idle shutdown」にチェック**し、`60 minutes` を設定（デフォルトは無効で、放置すると課金され続けます）
4. **Image**: 最新の `AzureML pytorch cuda12` 系イメージを選択
5. Create → 起動まで 3〜5 分

> 💡 **`idleTimeBeforeShutdown="PT60M"` の設定は最重要です。** 忘れると 1 日で $17 の課金が発生します。

## セットアップと実行（Compute Instance 上の Jupyter または SSH）

```bash
# 1. Python 3.10 の venv (Compute Instance のデフォルト Python)
python3.10 -m venv ~/mace-env
source ~/mace-env/bin/activate

# 2. PyTorch 2.4.0 CUDA 12.1 版を先にインストール
pip install --upgrade pip
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121

# 3. GPU が見えているか確認
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# → True Tesla T4

# 4. 本リポジトリを clone
git clone https://github.com/<your-fork>/spread1000-azure-quickstart.git
cd spread1000-azure-quickstart/research-fields/materials-medical-engineering/02-nnp-mace-mp
pip install -r requirements.txt

# 5. GPU で緩和 + MD
python src/relax.py --system Si --supercell 2 2 2 --device cuda --dtype float32
python src/run_md.py --input data/relaxed.extxyz --steps 10000 --device cuda --dtype float32
```

## GPU での期待時間（T4, 64 原子 Si）

| ステップ | 時間 |
|---|---:|
| モデルダウンロード（初回） | 30 秒 |
| 構造緩和（BFGS 収束まで） | 10〜30 秒 |
| MD 10000 ステップ (10 ps) | 5〜10 分 |
| MD 100000 ステップ (100 ps) | 50〜100 分 |

## Azure ML CommandJob 版（バッチ実行）

インタラクティブでなく、**ジョブとして submit** したい場合。まず **Compute Cluster** を別途作成する必要があります（Compute Instance はインタラクティブ用で、CommandJob からは使えません）:

```bash
az ml compute create --type amlcompute --name gpu-cluster-nc4t4 \
  --size Standard_NC4as_T4_v3 --min-instances 0 --max-instances 1 \
  --idle-time-before-scale-down 300 \
  --workspace-name <ws-name> --resource-group <rg-name>
```

その後 SDK で submit（出力を Azure ML の Blob ストレージに永続化する `Output` を必ず指定）:

```python
from azure.ai.ml import MLClient, command, Output
from azure.ai.ml.constants import AssetTypes
from azure.identity import DefaultAzureCredential

ml_client = MLClient.from_config(credential=DefaultAzureCredential())

job = command(
    code="./",
    command=(
        "pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121 && "
        "pip install -r requirements.txt && "
        "python src/relax.py --system Si --supercell 2 2 2 --device cuda --output ${{outputs.results}} && "
        "python src/run_md.py --input ${{outputs.results}}/relaxed.extxyz --output ${{outputs.results}} --steps 10000 --device cuda"
    ),
    outputs={
        "results": Output(type=AssetTypes.URI_FOLDER, mode="rw_mount"),
    },
    environment="AzureML-pytorch-2.2-ubuntu22.04-py310-cuda12@latest",
    compute="gpu-cluster-nc4t4",   # 上で作成したクラスタ名
    display_name="mace-mp-si-demo",
    experiment_name="mace-quickstart",
)
returned_job = ml_client.jobs.create_or_update(job)
print(returned_job.studio_url)
```

> ⚠️ **outputs を指定しないと**、コンピュートが解放された時点で `data/` に書いた結果が消えます。上記のように `Output(type=URI_FOLDER)` を宣言し、`${{outputs.results}}` を `--output` に渡してください。ジョブ完了後 Studio の Job details → Outputs から結果をダウンロードできます。

> ⚠️ **キュレーテッド環境の PyTorch バージョンに注意。** 環境によっては PyTorch 2.4.1（mace 非対応）が含まれます。上のように `command` の中で明示的に 2.4.0 を再インストールしてください。

## コスト目安（Japan East）

| 項目 | PAYG | Spot |
|---|---:|---:|
| `NC4as_T4_v3` VM | $0.71/hr | ~$0.21/hr |
| OS ディスク (128 GB Std SSD) | $0.009/hr | 同左 |
| **1 時間セッション合計** | **~$0.72** | **~$0.22** |
| 1 日放置（自動停止忘れ） | **$17.28** ⚠️ | **~$5** |

## 後片付け

必ず [06-cleanup.md](06-cleanup.md) の手順で Compute Instance を停止 or 削除してください。
