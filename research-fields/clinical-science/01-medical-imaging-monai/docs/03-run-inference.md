# 03. 推論 Job (T4 GPU, 事前学習 Bundle)

事前学習済み `spleen_ct_segmentation` Bundle を Task09_Spleen の `imagesTs` に対して実行し、予測 mask (`.nii.gz`) を生成します。

所要時間: **15〜25 分** (T4)
コスト目安: **約 ¥50〜100** (Japan East, `Standard_NC4as_T4_v3` PAYG ¥114.83/h)

## 1. Job 内容の確認

`aml/monai-infer.yml` の主要設定:

| 項目 | 値 |
|---|---|
| Compute | `azureml:monai-t4` (autoscale, min=0) |
| Environment | `azureml:monai-spleen-1-4@latest` |
| Data | `azureml:task09-spleen@latest` (ro_mount) |
| Bundle | `spleen_ct_segmentation` v0.6.1 (Job 内で `monai.bundle download`) |
| Config | `configs/inference.json` (sliding window, RAS, spacing 1.5×1.5×2.0) |
| Timeout | 1 時間 |

コマンドの実体:

```bash
python -m monai.bundle download spleen_ct_segmentation --version 0.6.1 --source huggingface_hub --repo MONAI/spleen_ct_segmentation --bundle_dir bundles
cd bundles/spleen_ct_segmentation
python -m monai.bundle run \
  --config_file configs/inference.json \
  --dataset_dir=<ro_mount path> \
  --output_dir=<output mount> \
  "--inferer#sw_batch_size=1"
```

> [!NOTE]
> `sw_batch_size=1` は T4 (16 GB) 向けの安全側の値です。A100 (80 GB) 上で動かす場合は 4〜8 に上げてスループットを向上できます。

## 2. Job の投入

```bash
cd research-fields/clinical-science/01-medical-imaging-monai

az ml job create \
  --file aml/monai-infer.yml \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --stream
```

`--stream` でログをリアルタイム表示します (`Ctrl-C` で切っても Job は継続)。

Job 名 (例: `patient_wall_abc123`) を控えておきます:

```bash
JOB_NAME=<出力された Job 名>
```

## 3. Job 進捗の確認

別ターミナルで:

```bash
az ml job show \
  --name "$JOB_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query "{name:name,status:status,duration:duration}" \
  -o jsonc
```

期待される遷移:

| Status | 経過時間目安 |
|---|---|
| `Queued` | 0〜1 分 |
| `Preparing` (Environment / Docker 準備) | 1〜3 分 (キャッシュ済みなら数十秒) |
| `Starting` (ノード起動) | 3〜8 分 (T4 コールドスタート) |
| `Running` (Bundle download + inference) | 5〜10 分 |
| `Completed` | — |

> [!TIP]
> 初回のみ ACR からの image pull で余分に時間がかかります。2 回目以降のノードでもコールドスタートは避けられませんが、pipeline execution 自体は 5 分以内で完了します。

## 4. 出力物のダウンロード

Job artifacts は AML の default blobstore に自動保存されます。

```bash
mkdir -p ./results/inference
az ml job download \
  --name "$JOB_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --output-name predictions \
  --download-path ./results/inference
```

`./results/inference/named-outputs/predictions/` 以下に予測 mask が展開されます:

```
predictions/
├── spleen_1/
│   └── spleen_1_trans.nii.gz
├── spleen_13/
│   └── spleen_13_trans.nii.gz
└── ...
```

## 5. 予測 mask の検証

```bash
python scripts/verify-output.py \
  ./results/inference/named-outputs/predictions \
  --expected-count 20 \
  --images-dir ./msd-data/Task09_Spleen/imagesTs
```

期待出力例:

```
==== 20 ファイルを検証 ====
File                                    Shape                Labels          Voxels(spleen)
----------------------------------------------------------------------------------------------------
spleen_1/spleen_1_trans.nii.gz          (512, 512, 55)       [0, 1]                 145,320  ✓
...
----------------------------------------------------------------------------------------------------
✓ すべての予測 mask に spleen ラベルが含まれています (20 files)
```

各 mask のラベルは **`0 = background`, `1 = spleen`** です。

## 6. 可視化 (ローカル PC)

**3D Slicer** または **ITK-SNAP** で NIfTI を開いて可視化します:

- 元画像: `msd-data/Task09_Spleen/imagesTs/spleen_1.nii.gz`
- 予測 mask: `results/inference/named-outputs/predictions/spleen_1/spleen_1_trans.nii.gz`

3D Slicer では:
1. **File → Add Data** で両方読み込み
2. mask を **Segmentation** として表示
3. **Volume Rendering** で 3D 表示

## 7. コスト実測

```bash
# Job 完了後 6〜12 時間待ってから
az consumption usage list \
  --start-date $(date -d '1 day ago' +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --query "[?tags.scenario=='monai-3d-seg'].{svc:instanceName,cost:pretaxCost,unit:usageQuantity}" \
  -o table
```

> [!NOTE]
> このコマンドは **ローカル PC** の元アカウント (Cost Management 参照権限あり) で実行してください。Compute Cluster の system-assigned MI には Cost Management 参照権限はありません。

## チェックリスト

- [ ] `az ml job show` の status が `Completed`
- [ ] `az ml job download --output-name predictions` が成功
- [ ] `scripts/verify-output.py` がすべての mask で spleen ラベルを確認
- [ ] 予測 mask の shape が対応する元 CT と同じ
- [ ] Compute Cluster が idle に戻り (`az ml compute show monai-t4 --query "current_node_count"` = 0)

## 次のステップ

**A** [`docs/04-fine-tuning.md`](04-fine-tuning.md) — A100 で 100 epoch fine-tuning し、validation Dice を測定
**B** [`docs/05-cleanup.md`](05-cleanup.md) — ここで終了する場合、リソース削除
