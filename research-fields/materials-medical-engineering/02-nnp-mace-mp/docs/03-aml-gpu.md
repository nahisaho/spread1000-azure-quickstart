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

代替 SKU: `Standard_NC8as_T4_v3`, `Standard_NC24ads_A100_v4`, および NCads H100 v5 系（キャパシティに空きがある場合のフォールバック）も同時申請しておくと通りやすいことがあります。**リージョンの実在 SKU は必ず現地確認**してください:

```bash
az vm list-skus --location japaneast --all \
  --query "[?contains(name,'NC') || contains(name,'ND')].[name, restrictions]" -o table
```

> 💡 **T4 / L4 は推論・小規模ジョブ向け、A100 / H100 はモデル学習用**。本クイックスタートは推論のみなので T4 で十分です。

### AML と Compute の両クォータを両方確認する

AML の workspace-scoped 割当と、`Microsoft.Compute` の core クォータは**別枠**です。両方確認してください:

```bash
set -a && source .env && set +a
az ml compute list-usage -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME" -l "$AZURE_LOCATION" -o table
az vm list-usage --location "$AZURE_LOCATION" -o table
az quota list --scope "/subscriptions/$(az account show --query id -o tsv)/providers/Microsoft.Compute/locations/$AZURE_LOCATION" -o table
```

## Azure ML ワークスペースの作成 (Bicep)

本シナリオはワークスペース・Key Vault・Storage・ACR・RBAC を自動作成する Bicep を同梱しています。

```bash
cd research-fields/materials-medical-engineering/02-nnp-mace-mp
./infra/deploy.sh          # rg-spread-materials-02 を japaneast に作成
set -a && source .env && set +a
```

`.env` にワークスペース名 (`AML_WORKSPACE_NAME`) が書き出されます。以降のコマンドはこれを参照します。

## Compute Instance の作成 (CLI)

```bash
az ml compute create --type computeinstance \
  --name "ci-mace-${USER}" \
  --size Standard_NC4as_T4_v3 \
  --workspace-name "$AML_WORKSPACE_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --idle-time-before-shutdown PT60M
```

> 💡 **`--idle-time-before-shutdown PT60M` は必須**。忘れると 1 日で $17 の課金が発生します。

## セットアップと実行（Compute Instance 上の Jupyter または SSH）

Compute Instance には既定で curated conda/venv 環境が用意されています。以下では追加の pinned venv を作ります (**AzureML Studio 作成 UI に「curated base image を選ぶ」項目はありません** — 現在の CI は managed base image を使い、ジョブ側でカスタム/キュレーテッド環境を指定します)。

```bash
python3.10 -m venv ~/mace-env
source ~/mace-env/bin/activate

pip install --upgrade pip
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121

python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# → True Tesla T4

git clone https://github.com/<your-fork>/spread1000-azure-quickstart.git
cd spread1000-azure-quickstart/research-fields/materials-medical-engineering/02-nnp-mace-mp
pip install -r requirements.txt

# --device auto は CUDA が使えれば自動で cuda を選びます。
python src/relax.py --system Si --supercell 2 2 2 --device auto --dtype float32
python src/run_md.py --input data/relaxed.extxyz --steps 10000 --device auto --dtype float32 \
  --equilibration-steps 1000

# 検証 (fail-fast)
python src/verify.py --relax data/relax_metrics.json --md data/md_metrics.json \
  --expected-lattice-a-Ang 5.43
```

## GPU での期待時間（T4, 64 原子 Si）

| ステップ | 時間 |
|---|---:|
| モデルダウンロード（初回, GitHub Releases） | 30 秒 |
| 構造緩和（BFGS 収束まで） | 10〜30 秒 |
| MD 10000 ステップ (10 ps) | 5〜10 分 |
| MD 100000 ステップ (100 ps) | 50〜100 分 |

> ⚠️ **MD の物理時間と GPU 時間の関係を必ず把握してから `--steps` を増やしてください。** 本スクリプトは `--steps × --timestep-fs` が 100 ps を超える場合、`--allow-long-run` なしでは実行を拒否します。10 ns (10,000,000 steps) は T4 で概算 83–167 GPU-hours = **$59–$119** です。

## Azure ML CommandJob 版（バッチ実行）

Compute Instance も CommandJob の compute ターゲットとして利用できます（開発・小規模ジョブ向け）。スケーラビリティ・Spot が必要な場合は **Compute Cluster** を作成し、Spot 相当の低優先度を使うために **`--tier low_priority`** を指定してください:

```bash
# Compute Cluster (Spot / low-priority)
az ml compute create --type amlcompute --name gpu-cluster-nc4t4 \
  --size Standard_NC4as_T4_v3 --min-instances 0 --max-instances 1 \
  --tier low_priority \
  --idle-time-before-scale-down 300 \
  --workspace-name "$AML_WORKSPACE_NAME" --resource-group "$AZURE_RESOURCE_GROUP"
```

> ⚠️ Spot / low-priority は**Compute Cluster でのみ利用可能**です。Compute Instance には Spot 相当のオプションはありません (本 README のコスト表を参照)。Spot はプリエンプション時にジョブが強制終了されるため、`Output(mode="rw_mount")` で結果を Blob に永続化し、コード側で checkpoint / resume に対応してください。

### AML SDK でのジョブ投入

```bash
# ローカルで依存を入れておく
python -m pip install azure-ai-ml==1.19.0 azure-identity==1.17.1
```

```python
import os
from azure.ai.ml import MLClient, command, Output
from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import Environment, BuildContext
from azure.identity import DefaultAzureCredential

ml_client = MLClient(
    DefaultAzureCredential(),
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
    resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
    workspace_name=os.environ["AML_WORKSPACE_NAME"],
)

# 1) Register the pinned custom environment (built from infra/environments/gpu/).
env = Environment(
    name="macemp02-gpu",
    version="1",
    build=BuildContext(path="infra/environments/gpu"),
)
ml_client.environments.create_or_update(env)

# 2) Submit the job. Use the CI as the compute target for quick dev runs.
job = command(
    code="./",
    command=(
        "python src/relax.py --system Si --supercell 2 2 2 --device auto "
        "--output ${{outputs.results}} && "
        "python src/run_md.py --input ${{outputs.results}}/relaxed.extxyz "
        "--output ${{outputs.results}} --steps 10000 --equilibration-steps 1000 --device auto && "
        "python src/verify.py --relax ${{outputs.results}}/relax_metrics.json "
        "--md ${{outputs.results}}/md_metrics.json --expected-lattice-a-Ang 5.43"
    ),
    outputs={
        "results": Output(type=AssetTypes.URI_FOLDER, mode="rw_mount"),
    },
    environment=f"macemp02-gpu@1",
    compute=os.environ.get("AML_COMPUTE", "ci-mace-" + os.environ.get("USER", "me")),
    display_name="mace-mp-si-demo",
    experiment_name="mace-quickstart",
)
returned_job = ml_client.jobs.create_or_update(job)
print(returned_job.studio_url)
```

> ⚠️ **outputs を指定しないと**、コンピュートが解放された時点で `data/` に書いた結果が消えます。上記のように `Output(type=URI_FOLDER)` を宣言し、`${{outputs.results}}` を `--output` に渡してください。

### 出力のダウンロード

Studio UI だけでなく CLI からも取得できます:

```bash
JOB=$(az ml job list -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME" \
  --query "[?display_name=='mace-mp-si-demo'].name | [0]" -o tsv)
az ml job download -n "$JOB" -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME" \
  --output-name results --download-path ./downloaded-results
az ml job download -n "$JOB" -g "$AZURE_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME" \
  --all --download-path ./job-artifacts
```

## コスト目安（Japan East）

| 項目 | PAYG | Low-priority (Cluster のみ) |
|---|---:|---:|
| `NC4as_T4_v3` VM | $0.71/hr | ~$0.21/hr |
| OS ディスク (128 GB Std SSD) | $0.009/hr | 同左 |
| 停止中の CI (OS ディスク + LB) | ~$0.32/day | — |
| **1 時間セッション合計** | **~$0.72** | **~$0.22** (Cluster) |
| 1 日放置（自動停止忘れ） | **$17.28** ⚠️ | — |

## 後片付け

必ず [06-cleanup.md](06-cleanup.md) の手順で Compute Instance を停止 or 削除してください。
