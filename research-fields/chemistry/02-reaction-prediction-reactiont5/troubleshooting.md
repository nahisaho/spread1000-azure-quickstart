# トラブルシューティング

## セットアップ / RBAC

### `deploy.sh` が `AuthorizationFailed` で止まる
Bicep が Role Assignment を作成する権限は **User Access Administrator** または **Owner** が必要です。Contributor だけでは Role Assignment を作成できません。管理者に Owner ロールの一時付与を依頼してください。

### `The subscription is not registered to use namespace 'Microsoft.MachineLearningServices'`
Resource Provider が未登録です。[`docs/01-prerequisites.md`](docs/01-prerequisites.md) の**プロバイダー登録**手順を実行してください。

## クォータ

### `Operation could not be completed as it results in exceeding approved <Region> Cores quota`
Standard_NC4as_T4_v3 は **NCASv3_T4 Family Cluster Dedicated vCPUs** と **Total Cluster Dedicated Regional vCPUs** の両方の枠を消費します。両方が 4 以上あるか [`docs/01-prerequisites.md`](docs/01-prerequisites.md) で確認し、不足時はポータル (AML Studio → Manage → Quota) から Request quota increase を送信してください。承認まで数時間〜1 営業日。

### 別リージョンで再デプロイしたい
既存 RG のリージョンは変更できません。**新しい RG 名 (例: `spread-chem-react-eastus-rg`)** で `deploy.sh` を再実行してください。Workspace 名も一意に (例: `spread-chem-react-eastus-ws`)。

## ジョブ実行

### `azureml-mlflow` のプラグインが認識されない / conda.yml を変更した
Environment version は immutable です。conda.yml を編集したら `environment.yml` の `version:` を上げ (例: `1` → `2`)、`az ml environment create -f aml/environment.yml` を再実行し、ジョブ送信時に `--set environment=azureml:reaction-t5:2` で明示してください。

### `HuggingFace` からのダウンロードが遅い / タイムアウト
初回ジョブでは `snapshot_download` が ~0.8 GB を取得します。3〜5 分程度が目安。ネットワーク側で失敗する場合は `HF_HUB_ENABLE_HF_TRANSFER=1` を job-predict.yml の env に追加し `pip install hf-transfer` を conda.yml に加えると高速化できます。

### RDKit がインストール中に固まる
`rdkit-pypi` (旧パッケージ) は非推奨です。conda.yml では `rdkit==2024.3.6` (新パッケージ) を指定しています。書き換えないでください。

### `CUDA out of memory`
T4 (16 GB) は本モデルには十分ですが、他プロセスが GPU を掴んでいる場合があります。ジョブを再送するか、`aml/job-predict.yml` の `command` の `--num-beams 5` を `3` に減らしてください。

## 予測結果

### `top1_accuracy` が 0 になる
出力が SMILES として無効 (`INVALID`) だけの可能性があります。`predictions.csv` を開いて `pred_smiles` 列を確認。よくある原因:
- 反応物と試薬を逆に指定
- 反応物を `,` で分離 (正しくは `.` 区切り)
- 参照生成物 SMILES が無効 (RDKit で正規化できない)

### 予測 SMILES と参照 SMILES が同一化合物なのに `match=False`
RDKit で正規化して比較していますが、立体化学 (`/`, `\`, `@`) や電荷 (`+`, `-`) が違うと別化合物扱いです。`InChIKey` ベースの比較に切り替えるには `src/predict.py` の `canonicalize` を `Chem.MolToInchiKey(mol)` に変更してください。

### `training_args.bin` のダウンロードで警告
`snapshot_download` は `allow_patterns` で `.safetensors` と `.json` のみ許可しています。pickle ファイル (`training_args.bin`) は取得しません。警告が出ても無視して問題ありません。

## クリーンアップ

### `az group delete` で `Cannot delete resource ... because it has resources`
削除ロックが設定されている場合や Managed Identity の依存が残っている場合があります。ポータルで RG を開き、依存関係タブから孤立リソースを個別削除してから再実行してください。

### `--max-instances 0` が拒否される
AML CLI の `--max-instances` の最小値は 1 です。**課金停止には `min_instances: 0` (デフォルト) のままで十分**です (アイドル時にノード 0)。完全削除するなら `az ml compute delete -n gpu-cluster -y`。
