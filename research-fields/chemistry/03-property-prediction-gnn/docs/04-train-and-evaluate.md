# 04 — 学習ジョブの実行と評価

## Environment を作成

```bash
cd research-fields/chemistry/03-property-prediction-gnn

az ml environment create -f aml/environment.yml
```

初回はコンテナビルド (5〜10 分) が走ります。2 回目以降はキャッシュヒットで数秒。

## GPU コンピュートクラスタを作成

```bash
az ml compute create -f aml/compute-gpu.yml
```

- `Standard_NC4as_T4_v3` (T4 16GB, 4 vCPU)
- `min_instances: 0`, `max_instances: 1`, idle 120 秒でスケールダウン → **待機中は $0**
- `identity: system_assigned` で ACR からイメージを pull

## 学習ジョブを送信

```bash
az ml job create -f aml/job-train.yml --stream
```

`--stream` でリアルタイムログを表示。初回は次の順で 15〜25 分かかります：
1. コンピュートノード起動 (5〜10 分, T4 は在庫次第)
2. コンテナ pull (2〜3 分)
3. データセット処理 (PyG が SMILES → グラフ変換、数秒)
4. 学習ループ (最大 150 エポック、早期停止あり、T4 で 1〜3 分)
5. テスト評価 + MLflow ログ

## 結果の確認

ジョブ完了後、コンソールに表示された `Name:` 行のジョブ名 (例 `patient_ocean_abc123`) を控えてください。

```bash
python scripts/verify-output.py <RUN_NAME>
```

期待される出力例：

```
Job status: Completed
MLflow metrics:
  test_rmse       = 0.85
  test_mae        = 0.62
  test_r2         = 0.76
  epochs_run      = 87.0
Output files:
  ✓ metrics.json        (156 bytes)
  ✓ best_model.pt       (48123 bytes)
```

## 期待値の目安

| メトリック | 期待値 | 合格ライン |
|---|---:|---:|
| `test_rmse` | 0.70〜0.95 | ≤ 1.0 |
| `test_mae` | 0.50〜0.75 | ≤ 0.8 |
| `test_r2` | 0.60〜0.85 | ≥ 0.5 |

合格ライン未達の場合は [`troubleshooting.md`](../troubleshooting.md#test_rmse-が-15-以上になる) を確認し、seed を変えるか hidden dim / epochs を増やしてください。

## Studio UI で確認

<https://ml.azure.com/> → Workspace → Jobs から実行履歴・MLflow メトリクス (`train_loss`, `val_rmse` の学習曲線含む) を閲覧できます。

## 自分のデータで試す

`torch_geometric.datasets.MoleculeNet` の `"ESOL"` ローダーは、CSV の**末尾列を SMILES、末尾から 2 番目の列を目的変数** (`y`) として固定で読み込みます（列名は無視されます）。したがって自分のデータで試すには次のいずれか：

**A) 同じスキーマで CSV を作る (推奨)**

`delaney-processed.csv` と同じ列順にして、末尾から 2 番目に目的変数、末尾に SMILES を配置：

```csv
Compound ID,...,my_property,smiles
mol_001,...,-2.15,CCO
```

`az ml data create --name my-molecules --version 1 --type uri_file --path data/my.csv` で登録し、`aml/job-train.yml` の `inputs.esol_csv.path` を `azureml:my-molecules:1` に差し替えれば動きます。

> [!WARNING]
> **カスタムデータで機密情報や被験者データを含む場合は本テンプレートを使用しないでください。** 現状の Bicep は `publicNetworkAccess: 'Enabled'` かつ HBI (High Business Impact) ワークスペースではありません。実際のジョブでは PyG のキャッシュを job-local scratch に置いて `./outputs` への流出を防いでいますが、Data Asset として登録したファイル自体は Storage account 上に保持され、公開ネットワーク経由でアクセス可能です。規制データを扱う場合は Private Endpoint + `hbiWorkspace: true` に変更した専用テンプレートを用意してください。

**B) train.py を編集する**

任意の列名で使いたい場合は `src/train.py` の `load_esol` を独自ローダーに書き換え、pandas で CSV を読んで `torch_geometric.utils.smiles.from_smiles` で `Data` オブジェクトを作ってください。

## ハイパーパラメータの変更

`aml/job-train.yml` の `command:` に以下のフラグを追加できます：

- `--hidden 128` (デフォルト 64)
- `--layers 4` (デフォルト 3)
- `--epochs 300` (デフォルト 150)
- `--patience 40` (デフォルト 20)
- `--lr 5e-4` (デフォルト 1e-3)
- `--batch-size 128` (デフォルト 64)
- `--seed 7` (デフォルト 42)

次: [`05-cleanup.md`](05-cleanup.md)
