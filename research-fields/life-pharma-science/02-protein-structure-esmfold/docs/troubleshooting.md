# トラブルシューティング

## デプロイ関連

### エラー: `The requested VM size is not available` / `SkuNotAvailable`

**原因**: 選んだリージョンで指定 GPU SKU が枯渇しています。

**対処**:
1. T4 (`Standard_NC8as_T4_v3` / `Standard_NC4as_T4_v3`) にダウングレード
2. または `LOCATION` を `eastus2` / `swedencentral` に変更（deploy.sh または Bicep パラメータ）

利用可能な Azure ML GPU SKU を確認：

```bash
SUB_ID=$(az account show --query id -o tsv)
az rest --method get \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.MachineLearningServices/locations/japaneast/vmSizes?api-version=2024-04-01" \
  --query "value[?gpus > \`0\`].{Name:name, GPUs:gpus, vCPU:vCPUs, RAM_GB:memoryGB}" \
  -o table
```

> [!NOTE]
> **`Standard_NC6s_v3`（V100）は 2025-09-30 に廃止済み** です。旧手順で見かけても選ばないでください。

### エラー: `assignedUser is required`（Bicep デプロイ時）

**原因**: Bicep で Compute Instance を作るには「担当ユーザー」を明示指定する必要があります。

**対処**: `parameters.json` に以下を設定：

```bash
MY_OID=$(az ad signed-in-user show --query id -o tsv)
MY_TID=$(az account show --query tenantId -o tsv)
```

## 環境構築関連

### エラー: `ImportError: Using low_cpu_mem_usage=True or a device_map requires Accelerate: pip install accelerate`

**原因**: `accelerate` パッケージ未インストール。

**対処**:

```bash
conda activate esmfold
pip install accelerate
# カーネル再起動が必要
```

`setup-esmfold.sh` は `accelerate` を自動でインストールしますが、独自に conda 環境を作った場合はここに落ちます。

### エラー: `ModuleNotFoundError: No module named 'openfold'`

**原因**: 古いドキュメントやスクリプトで `from openfold_utils.protein import ...` を使っている。

**対処**: `transformers>=4.25` では openfold が **バンドル済み** です。以下のパスに変更してください：

```python
# ❌ 古い
from openfold_utils.protein import to_pdb

# ✅ 正しい
from transformers.models.esm.openfold_utils.protein import to_pdb, Protein as OFProtein
from transformers.models.esm.openfold_utils.feats import atom14_to_atom37
```

### エラー: `pip install fair-esm[esmfold]` で `deepspeed==0.5.9` 依存衝突

**原因**: `fair-esm[esmfold]` は古い deepspeed をピン留めしており、PyTorch 2.x / CUDA 12.x と衝突します。

**対処**: **`fair-esm` は使わないでください**。本クイックスタートは HuggingFace `transformers` パスを採用しています（openfold バンドル済みで依存も少ない）。

## 推論関連

### エラー: `torch.cuda.OutOfMemoryError: CUDA out of memory`

**原因**: GPU VRAM 不足。ESMFold はメモリが配列長 N に対して O(N²) で増加します。

**対処**（強い順）:

```python
# 1. chunk_size を下げる（最も効果的）
model.trunk.set_chunk_size(32)   # デフォルト 64、OOM 時は 32 → 16 → 8

# 2. ESM stem を FP16 化
model.esm = model.esm.half()

# 3. TF32 有効化（Ampere 以降のみ）
import torch
torch.backends.cuda.matmul.allow_tf32 = True

# 4. メモリ断片化対策
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# 5. 各推論後にキャッシュ解放
torch.cuda.empty_cache()
```

推奨対応表：

| GPU | 対応配列長（絶対上限 1024 aa） | 推奨オプション |
|---|---|---|
| T4 16GB | ≤ 600 aa | `--half-precision --chunk-size 64` |
| T4 16GB | ≤ 1024 aa | `--half-precision --chunk-size 16`（時間 3〜5 倍） |
| A100 80GB | ≤ 700 aa | オプション不要 |
| A100 80GB | ≤ 1024 aa | `--half-precision --chunk-size 32` |

**1024 aa は ESMFold の位置埋め込みの絶対上限** です。ドメイン分割するか AlphaFold2/3 を検討してください。

### 予測構造が破綻している / 明らかにおかしい

**原因の 90%**: `add_special_tokens=False` を指定し忘れている。

**対処**:

```python
# ✅ 正しい
tokens = tokenizer(sequence, return_tensors="pt", add_special_tokens=False)

# ❌ ダメ（BOS/EOS トークンが混入し座標が破綻）
tokens = tokenizer(sequence, return_tensors="pt")
```

その他の破綻要因：
- 配列に非標準アミノ酸（X, B, Z, U, O 等）が含まれている → **標準 20 種類のみ** にする
- 配列長が 1024 aa を超えている → 分割する
- pLDDT が全体的に < 50 → 新規/短すぎる/低複雑度配列の可能性。AlphaFold2 でも試す

### `model.output_to_pdb()` で `AttributeError`

**原因**: 古い transformers（< 4.25）。

**対処**: `pip install -U transformers` して 4.25 以上に。

## HuggingFace キャッシュ関連

### 起動のたびに 8.44 GB を再ダウンロードしてしまう

**原因**: `HF_HOME` が Compute Instance の OS ディスク（`~/.cache/huggingface/`）を指しており、Compute Instance を削除すると消える。

**対処**: **必ず `~/cloudfiles/hf_cache` を使う**（Workspace 共有 Storage にマウントされる永続領域）。

```bash
# .bashrc に追記
echo 'export HF_HOME=/home/azureuser/cloudfiles/hf_cache' >> ~/.bashrc
source ~/.bashrc

# または Python 側で明示
import os
os.environ["HF_HOME"] = "/home/azureuser/cloudfiles/hf_cache"
```

`setup-esmfold.sh` は自動でこの設定を行います。

### ダウンロードが遅い / タイムアウト

**対処**:

```bash
# 通信タイムアウトを延長
export HF_HUB_DOWNLOAD_TIMEOUT=600

# 進捗表示
export HF_HUB_ENABLE_HF_TRANSFER=1
pip install hf_transfer

# 再開
python -c "from transformers import EsmForProteinFolding; EsmForProteinFolding.from_pretrained('facebook/esmfold_v1', low_cpu_mem_usage=True)"
```

## Jupyter / ノートブック関連

### ノートブックからカーネル `Python 3.10 (esmfold)` が選べない

**対処**:

```bash
conda activate esmfold
python -m ipykernel install --user --name esmfold --display-name "Python 3.10 (esmfold)"
# JupyterLab を再読み込み
```

## Compute Instance 停止関連

### 自動停止（idle shutdown）が働かない

**原因**: Bicep API 2024-04-01 では `idleTimeBeforeShutdown` が正式スキーマ外で、サーバー側では受理されるが反映されないケースがあります。また、Workspace のマネージド ID にロール割当がないと反映されていても停止が実行されません（[02-provision-aml.md](02-provision-aml.md) の重要事項を参照）。

**対処**: Azure ML Studio → **コンピューティング** → 該当 CI 選択 → **アクション** → **アイドル シャットダウンの編集** で 30 分を設定。

CLI から既存 CI の idle time を書き換える方法は Azure ML CLI v2 では公式サポートされていません。設定が入っていない場合は Studio か、対応するプライベート REST エンドポイント (`updateIdleShutdownSetting`) を使ってください。

## ネットワーク / 認証関連

### Jupyter に接続できない（Compute Instance の URL がタイムアウト）

**原因の可能性**:
1. Compute Instance の `state` が `Stopped` → `az ml compute start` で起動
2. VNet 統合 Workspace を使っており、社内 Proxy が Jupyter へのアクセスを遮断
3. `assignedUser` が自分ではない（サービスプリンシパルが所有）

**対処**:
```bash
az ml compute show --name ci-esmfold-$(whoami) \
  --resource-group rg-esmfold-jp \
  --workspace-name mlw-esmfold-<suffix> \
  --query "{state:state, assignedUser:personalComputeInstanceSettings.assignedUser.objectId}"
```

`assignedUser.objectId` が自分の Object ID (`az ad signed-in-user show --query id -o tsv`) と一致しない場合は、CI を削除して deploy.sh を再実行してください。
