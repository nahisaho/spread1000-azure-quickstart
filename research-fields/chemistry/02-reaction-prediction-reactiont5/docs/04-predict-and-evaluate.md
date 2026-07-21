# 04 — 予測ジョブの実行と評価

## Environment を作成

```bash
cd research-fields/chemistry/02-reaction-prediction-reactiont5

az ml environment create -f aml/environment.yml
```

初回はコンテナビルド (5〜10 分) が走ります。2 回目以降はキャッシュヒットで数秒。

## GPU コンピュートクラスタを作成

```bash
az ml compute create -f aml/compute-gpu.yml
```

- `Standard_NC4as_T4_v3` (T4 16GB, 4 vCPU)
- `min_instances: 0`, `max_instances: 1`, idle 120 秒でスケールダウン → **待機中は $0**

## 予測ジョブを送信

```bash
az ml job create -f aml/job-predict.yml --stream
```

`--stream` でリアルタイムログを表示。初回は次の順で 15〜30 分かかります：
1. コンピュートノード起動 (5〜10 分, T4 は在庫次第)
2. コンテナ pull (2〜3 分)
3. Hugging Face から model (~0.8 GB) を初回ダウンロード (3〜5 分)
4. 5 反応の推論 (数秒)
5. スコアリング (数秒)

## 結果の確認

ジョブ完了後、コンソールに表示された `Name:` 行のジョブ名 (例 `bright_ocean_abc123`) を控えてください。次のスクリプトで内容を検証できます：

```bash
python scripts/verify-output.py <RUN_NAME>
```

期待される出力例：

```
Job status: Completed
MLflow metrics:
  num_reactions   = 5.0
  valid_ratio     = 1.0
  top1_accuracy   = 0.8
Output files:
  ✓ predictions.csv     (5 rows)
```

## 期待値の目安

| メトリック | 期待値 (デモ 5 反応) | 意味 |
|---|---|---|
| `top1_accuracy` | 0.6〜1.0 | 予測 SMILES が参照と正規化後に一致した割合 |
| `valid_ratio` | 0.9〜1.0 | 予測が有効な SMILES である割合 |
| `num_reactions` | 5 | 処理した反応数 |

top-1 精度が期待より低い場合は [`troubleshooting.md`](../troubleshooting.md#top1_accuracy-が-0-になる) を確認してください（多くは入力フォーマット違反）。

## 自分のシナリオで試す

反応 CSV を変更する場合：

1. [`docs/03-prepare-data.md`](03-prepare-data.md) の手順で新しい Data Asset を登録 (例 `--name my-reactions --version 1`)
2. `aml/job-predict.yml` の `inputs.reactions.path` を `azureml:my-reactions:1` に変更
3. `az ml job create -f aml/job-predict.yml --stream` を再送

ビームサーチのビーム幅を変える (精度と速度のトレードオフ)：

- `aml/job-predict.yml` の `command:` の `--num-beams 5` を `--num-beams 3` などに変更

## Studio UI で確認

<https://ml.azure.com/> → Workspace → Jobs から実行履歴・MLflow メトリクス・出力ファイル (`predictions.csv`) を閲覧できます。

次: [`05-cleanup.md`](05-cleanup.md)
