# 04. Fine-tuning Job (A100 GPU, 100 epoch)

事前学習 checkpoint を起点に Task09_Spleen (`imagesTr/labelsTr`) で fine-tuning し、validation Dice を測定します。

所要時間: **2〜3 時間** (A100 1 台, 100 epoch, 32/9 split)
コスト目安 (Japan East, PAYG):

| 方式 | 2 時間 | 3 時間 |
|---|---:|---:|
| A100 Dedicated (¥861.40/h) | ¥1,723 | ¥2,584 |
| A100 3-year Savings Plan (¥531/h) | ¥1,063 | ¥1,594 |
| A100 Spot (¥159.19/h) | ¥318 | ¥478 |

## 1. Fine-tuning config の意義

Bundle 標準の `configs/train.json` は **事前学習重みをロードしない** (`initialize` は seed 設定だけ) ため、**そのまま実行するとゼロから学習**になります。

本テンプレートでは `aml/finetune.json` を追加で読ませて `models/model.pt` を loader で読み込みます:

```json
{
  "pretrained_loader": {
    "_target_": "CheckpointLoader",
    "load_path": "$@bundle_root + '/models/model.pt'",
    "load_dict": { "model": "@network" }
  },
  "initialize": [
    "$monai.utils.set_determinism(seed=123)",
    "$@pretrained_loader(@train#trainer)"
  ]
}
```

MONAI の Bundle 設定は複数 JSON を `['a.json','b.json']` の順で重ねると、後ろが前を上書きします。`initialize` セクションが `finetune.json` の内容で置き換わり、事前学習重みが Ignite trainer に注入されます。

## 2. Job 内容

`aml/monai-train.yml` の要点:

| 項目 | 値 |
|---|---|
| Compute | `azureml:monai-a100` (A100 80GB, autoscale, min=0) |
| Environment | `azureml:monai-spleen-1-4@latest` |
| Data | `azureml:task09-spleen@latest` |
| Finetune config | `./aml/finetune.json` を uri_file として mount |
| Epochs | 100 (override) |
| Batch size | 2 (override) |
| Cache rate | 1.0 (全 41 volumes を CPU RAM に展開) |
| Timeout | 6 時間 |

コマンドの実体:

```bash
python -m monai.bundle download spleen_ct_segmentation --version 0.6.1 --source huggingface_hub --repo MONAI/spleen_ct_segmentation --bundle_dir bundles
cp <finetune.json mount> bundles/spleen_ct_segmentation/configs/finetune.json
cd bundles/spleen_ct_segmentation
python -m monai.bundle run \
  --config_file "['configs/train.json','configs/finetune.json']" \
  --dataset_dir=<data mount> \
  --output_dir=<output>/eval \
  --ckpt_dir=<output>/models \
  --epochs=100 \
  "--train#dataloader#batch_size=2" \
  "--train#dataset#cache_rate=1.0"
```

## 3. パイロット実行 (5 epoch、必須)

いきなり 100 epoch は不経済です (¥1,700〜2,600)。**まず 5 epoch で GPU 挙動と Bundle 動作を確認**し、成功を確認してから本番投入してください。

パイロット用に `aml/monai-train-pilot.yml` を作成 (`--epochs=100` の行を `--epochs=5` に置き換え):

```bash
cd quickstarts/medical-imaging/monai-3d-segmentation

sed 's/--epochs=100/--epochs=5/' aml/monai-train.yml > aml/monai-train-pilot.yml

az ml job create \
  --file aml/monai-train-pilot.yml \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --stream
```

> [!NOTE]
> `az ml job create --set command='...'` で複雑な shell/引用符を含む command を上書きすると、YAML の複数階層 quote と CLI の shell escape が組み合わさって高確率で壊れます。**`sed` で epochs だけ差し替えたパイロット yml を別途生成する**のが最も確実です。

パイロットで確認する項目:
- Bundle download 成功
- CUDA available = True, GPU = `NVIDIA A100`
- Epoch 1 が完了し、artifacts/eval/, artifacts/models/ にファイルが生成
- 1 epoch あたりの経過時間 (100 epoch の見積もりに使用)
- pretrained checkpoint がロードされたログ (`Restored all variables from ...`)

**パイロット費用目安**: 30〜45 分 × ¥861/h = 約 ¥430〜650 (Dedicated)。Spot なら ¥80〜120。

> [!IMPORTANT]
> パイロットが失敗した場合は **必ず原因を解消**してから本番 100 epoch を投入してください。docs/troubleshooting.md を参照。

## 4. 本番 100 epoch Job 投入

パイロット成功後:

```bash
az ml job create \
  --file aml/monai-train.yml \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --stream
```

Job 名を控えます:

```bash
JOB_NAME=<出力された Job 名>
```

## 5. 進捗確認

### AML Studio (推奨)

```bash
az ml job show \
  --name "$JOB_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query "studio_url" -o tsv
```

Studio では **Outputs + Logs** タブから Job のリアルタイムログと生成ファイル (`artifacts/eval/`, `artifacts/models/`) を確認できます。

> [!NOTE]
> Bundle 標準の `train.json` は MONAI の `TensorBoardStatsHandler` を使用し、TensorBoard event ファイルを `output_dir` に書き出します。**AML Studio の Metrics タブに自動でグラフ表示されるのは MLflow に log されたメトリクスのみ**で、TensorBoard event はここには自動反映されません。トレーニングカーブは Job 完了後にダウンロードして TensorBoard で開いてください (§6)。MLflow への同時ログを希望する場合は Bundle 設定に MONAI `MLFlowHandler` を追加する必要があります。

### CLI で概要のみ

```bash
watch -n 60 "az ml job show --name $JOB_NAME \
  -g $AZURE_RESOURCE_GROUP -w $AZURE_WORKSPACE_NAME \
  --query '{status:status,duration:duration}' -o jsonc"
```

## 6. Job 完了後 — 結果のダウンロード

```bash
mkdir -p ./results/finetune
az ml job download \
  --name "$JOB_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --output-name artifacts \
  --download-path ./results/finetune
```

主要ファイル:

```
results/finetune/named-outputs/artifacts/
├── eval/
│   └── events.out.tfevents.*        # TensorBoard event (train/val loss, Dice)
└── models/
    └── model.pt                     # ベスト checkpoint (validation Dice 最良の 1 個)
```

> [!NOTE]
> Bundle 標準の `train.json` は `CheckpointSaver` を **best-metric only** で動かします。中間 epoch checkpoint (`epoch_*.pt`) や集計 metrics ファイルは **生成されません**。各 epoch の Dice/loss は TensorBoard event に記録されます。集計サマリが必要な場合は §7 の evaluation Job を実行してください (evaluate.json は `MetricsSaver` で CSV — `metrics.csv`, `val_mean_dice_raw.csv`, `val_mean_dice_summary.csv` — を出力します)。

TensorBoard で確認:

```bash
pip install tensorboard
tensorboard --logdir ./results/finetune/named-outputs/artifacts/eval --port 6006
# ブラウザで http://localhost:6006 を開く
```

## 7. Evaluation

fine-tuning 済みの `model.pt` で validation split を再評価:

```yaml
# 別途 aml/monai-eval.yml として作成 (テンプレート)
# 注意: Bundle の evaluate.json は bundle_root/models/model.pt をロードするため、
# 事前に fine-tune 済み checkpoint をその位置へコピーする。
inputs:
  data:
    type: uri_folder
    path: azureml:task09-spleen@latest
    mode: ro_mount
  checkpoint:
    type: uri_file
    path: <fine-tune 出力の model.pt を Data Asset 化したもの>
    mode: ro_mount
outputs:
  eval:
    type: uri_folder
    mode: upload

command: >-
  set -eux;
  python -m monai.bundle download "spleen_ct_segmentation" --version "0.6.1" --source "huggingface_hub" --repo "MONAI/spleen_ct_segmentation" --bundle_dir bundles;
  cp "${{inputs.checkpoint}}" bundles/spleen_ct_segmentation/models/model.pt;
  cd bundles/spleen_ct_segmentation;
  python -m monai.bundle run
  --config_file "['configs/train.json','configs/evaluate.json']"
  --dataset_dir="${{inputs.data}}"
  --output_dir="${{outputs.eval}}";
```

## 8. 期待される Dice

Bundle の公称 validation mean Dice: **0.961**

Task09_Spleen (41 volumes, 32/9 split) を 100 epoch fine-tune した場合、Dice は 0.94〜0.97 の範囲に落ち着くことが多いです。乱数 seed、GPU、MONAI/PyTorch バージョンに依存するため、**Bundle 公称値の完全再現は保証されません**。

## 9. コスト管理

Job 完了後、A100 クラスターが自動で 0 ノードに縮小 (`idle_time_before_scale_down: 120` 秒) されることを確認:

```bash
az ml compute show \
  --name monai-a100 \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query "{state:provisioning_state,current:current_node_count,min:min_instances,max:max_instances}" \
  -o jsonc
```

`current: 0` を確認 → 以後 idle 課金 0。

## チェックリスト

- [ ] パイロット (5 epoch) 実行で GPU が A100 と表示
- [ ] 本番 100 epoch Job が Completed
- [ ] `model.pt` が artifacts/models/ にダウンロード
- [ ] TensorBoard で train/val loss、Dice のカーブが減少・増加傾向
- [ ] Validation Dice が 0.90 以上 (下振れなら epochs, cache_rate, LR を再検討)
- [ ] `az ml compute show monai-a100` の current_node_count が 0

## 次のステップ

→ [`docs/05-cleanup.md`](05-cleanup.md) — Cluster 縮小 & リソース削除
