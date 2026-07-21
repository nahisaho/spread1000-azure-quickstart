# 04. 学習 → 評価 (AML command job)

## 1. Environment / Compute の作成

```bash
cd research-fields/clinical-science/03-biosignal-ecg-classification

# Environment (mcr openmpi5.0-cuda12.4 + conda.yml)
az ml environment create \
  -f aml/environment.yml \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME"

# Compute (T4 GPU) — quota 0 の場合は compute-cpu.yml を使う
az ml compute create \
  -f aml/compute-t4.yml \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME"
```

初回の Environment 作成 (image build) は 5〜10 分かかります。ジョブ実行時に build が始まるため、後続の `az ml job create` から待たされて OK です。

## 2. 学習ジョブを実行

```bash
az ml job create \
  -f aml/job-train.yml \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME" \
  --web
```

`--web` を付けると AML Studio のジョブ画面がブラウザで開きます。

**ジョブの内部フロー**:

1. `prepare_data.py` — MIT-BIH を 180-サンプル窓 × AAMI 5 クラスに整形 (record-level split)
2. `train.py` — 小型 1D CNN を 15 epoch 学習、best-val-macro-F1 チェックポイントを保存
3. Test set で macro-F1 / confusion matrix / classification report を計算し MLflow に記録
4. モデル (`model.pt` + `mlflow.pytorch.log_model`) を outputs に保存

## 3. GPU quota が無い場合 (CPU フォールバック)

`aml/compute-cpu.yml` で作成し、job 送信時に `--set` で compute を上書きします:

```bash
az ml compute create -f aml/compute-cpu.yml -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME"

# job YAML はそのまま。--set で compute のみ上書き。
az ml job create -f aml/job-train.yml \
  -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME" \
  --set compute=azureml:ecg-cpu \
  --web
```

## 4. 結果の確認

**AML Studio 上**:

- **Metrics** タブ: `train_loss`, `val_macro_f1`, `test_macro_f1`
- **Outputs + logs** タブ:
  - `outputs/user_logs/std_log.txt` — 学習ログ全文
  - job outputs → `model` (named output) → `model.pt`, `classification_report.json`, `confusion_matrix.csv`, `confusion_matrix.png`
  - MLflow artifacts → `model/` — MLflow pyfunc モデル
  - MLflow artifacts → `evaluation/confusion_matrix.png`, `evaluation/classification_report.json`

**CLI で確認**:

```bash
# 最新ジョブ ID を取得
JOB_NAME=$(az ml job list -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME" \
  --query "[?display_name=='mitbih-aami5-1dcnn'] | [0].name" -o tsv)

# 結果の verification
python scripts/verify-output.py "$JOB_NAME"

# outputs をローカルにダウンロード
az ml job download \
  --name "$JOB_NAME" \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME" \
  --output-name model \
  --download-path ./ecg-outputs
```

## 5. 期待される数値（参考）

MIT-BIH inter-patient 分割 + 単純な 1D CNN 15 epoch では（**44-record de Chazal 標準プロトコル**、paced records 102/104/107/217 を除外。records 201 / 202 は同一被験者由来のため厳密な患者非依存ではない点は `src/prepare_data.py` の冒頭コメントを参照）:

| 指標 | 目安 |
|---|---:|
| Test macro F1 | 0.50〜0.65 |
| N クラス F1 | 0.95+ |
| S クラス F1 | 0.30〜0.55 (最も難しい) |
| V クラス F1 | 0.75〜0.90 |
| F クラス F1 | 0.10〜0.30 (サンプル数が非常に少ない) |
| Q クラス F1 | 0.00〜0.20 (paced 除外のためほぼ観測されない — 定義上の期待動作) |

> [!NOTE]
> S (SVEB) と F (fusion) は本質的に難しく、公開ベンチマークでも macro F1 は 0.6 程度が一つの目安です。教育用途では accuracy だけで判断せず、必ず **class-wise F1 と confusion matrix** を確認してください。Q クラスは paced records を除外している標準プロトコル上、実質的にサンプルが数個しかありません。

## 次

[05-cleanup.md](05-cleanup.md) で課金を止めます。
