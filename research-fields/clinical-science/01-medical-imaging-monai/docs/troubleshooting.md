# トラブルシューティング

このドキュメントで扱う典型的な問題と対処:

- [Job が Queued のまま進まない](#job-が-queued-のまま進まない)
- [`AllocationFailed` / SKU 在庫なし](#allocationfailed--sku-在庫なし)
- [GPU OOM (CUDA out of memory)](#gpu-oom-cuda-out-of-memory)
- [`monai.bundle download` が失敗](#monaibundle-download-が失敗)
- [Fine-tuning で事前学習重みがロードされない](#fine-tuning-で事前学習重みがロードされない)
- [Validation Dice が公称値に届かない](#validation-dice-が公称値に届かない)
- [Data Asset が Job から見えない](#data-asset-が-job-から見えない)
- [Cluster が 0 ノードに縮小されない](#cluster-が-0-ノードに縮小されない)
- [DICOM を直接 Bundle に渡すと失敗](#dicom-を直接-bundle-に渡すと失敗)

> [!IMPORTANT]
> すべてのコマンドは **ローカル PC (もしくは Cloud Shell)** で、以下の環境変数を export した状態で実行してください:
> ```
> AZURE_LOCATION, AZURE_RESOURCE_GROUP, AZURE_WORKSPACE_NAME, AZURE_STORAGE_ACCOUNT
> ```

## Job が Queued のまま進まない

**症状**: `az ml job show` の status が数十分〜数時間 `Queued` のまま。

**原因の切り分け**:

```bash
# GPU quota が承認済みか
az vm list-usage \
  --location "$AZURE_LOCATION" \
  --query "[?contains(name.value, 'NCADSA100v4')].{name:name.value,current:currentValue,limit:limit}" \
  -o table
```

- `limit: 0` → **quota 未申請/未承認** → docs/01 §5 の手順で申請
- `current == limit` → 他 Job が使用中 → 完了待ち or 別 SKU/リージョンへ

```bash
# Cluster の状態
az ml compute show \
  --name monai-a100 \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query "{state:provisioning_state,errors:errors}" \
  -o jsonc
```

- `errors` に `SkuNotAvailable` や `QuotaExceeded` があれば根本原因

## `AllocationFailed` / SKU 在庫なし

**症状**: Job status が `Failed`、エラーに `AllocationFailed` または `SkuNotAvailableForSubscription`。

**原因**: リージョンで SKU の物理在庫が枯渇、または Subscription 制限。

**対処**:

```bash
# 他リージョンでの SKU 可用性を確認
for region in japaneast southeastasia eastus westus2; do
  echo "=== $region ==="
  az vm list-skus \
    --location "$region" \
    --size Standard_NC24ads_A100_v4 \
    --query "[].{region:locationInfo[0].location,restrictions:restrictions[].reasonCode}" \
    -o table
done
```

- 別リージョンが空いていれば、AML ワークスペースを **同一リージョン**に作り直す (Storage も同じリージョンにする)
- どこも空きがなければ Spot (`tier: low_priority` の compute-a100-spot.yml を追加) を試す

## GPU OOM (CUDA out of memory)

**症状**: Job ログに `torch.cuda.OutOfMemoryError` または `RuntimeError: CUDA out of memory`.

**対処 (優先度順)**:

1. **`sw_batch_size` を 1 に**:
   ```bash
   "--inferer#sw_batch_size=1"
   ```

2. **training batch size を 1 に**:
   ```bash
   "--train#dataloader#batch_size=1"
   ```

3. **`cache_rate` を下げる** (RAM 不足の場合):
   ```bash
   "--train#dataset#cache_rate=0.3"
   ```

4. **AMP が有効か確認** (Bundle 標準では `amp: true`):
   ```bash
   grep -r amp bundles/spleen_ct_segmentation/configs/
   ```

5. **T4 (16GB) → A100 (80GB) に切り替え**: `compute:` を `azureml:monai-a100` に変更して再実行

6. **patch size (ROI) を小さくする** (性能低下の恐れあり):
   ```bash
   "--train#random_transforms#0#spatial_size=[64,64,64]"
   ```

## `monai.bundle download` が失敗

**症状**: Job ログに `ConnectionError`, `TimeoutError`, または `HTTP 403/404` (Model Zoo のリポジトリアクセス失敗)。

**原因**: AML の managed VNet や private endpoint 環境で outbound access が制限されている、または一時的な Model Zoo 側の問題。

**対処 (オフライン方式)**:

ローカル PC で Bundle を先に取得:

```bash
pip install 'monai[fire,huggingface_hub]==1.4.0'
python -m monai.bundle download \
  "spleen_ct_segmentation" \
  --version "0.6.1" \
  --source "huggingface_hub" \
  --repo "MONAI/spleen_ct_segmentation" \
  --bundle_dir ./bundle-asset
```

Blob にアップロード (workspaceblobstore の実体コンテナ名を動的に解決):

```bash
CONTAINER=$(az ml datastore show \
  --name workspaceblobstore \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query container_name -o tsv)

az storage blob upload-batch \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --auth-mode login \
  --destination "$CONTAINER" \
  --destination-path bundles/spleen_ct_segmentation \
  --source ./bundle-asset/spleen_ct_segmentation \
  --overwrite
```

Data Asset として登録:

```bash
cat > /tmp/bundle-asset.yml <<'YAML'
$schema: https://azuremlschemas.azureedge.net/latest/data.schema.json
name: monai-spleen-bundle
version: "0.6.1"
type: uri_folder
path: azureml://datastores/workspaceblobstore/paths/bundles/spleen_ct_segmentation/
YAML

az ml data create -f /tmp/bundle-asset.yml \
  -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME"
```

Job YAML の inputs に追加し、`monai.bundle download` の代わりに mount を使用:

```yaml
inputs:
  bundle:
    type: uri_folder
    path: azureml:monai-spleen-bundle:0.6.1
    mode: download

command: >-
  set -eux;
  mkdir -p bundles;
  cp -r "${{inputs.bundle}}" bundles/spleen_ct_segmentation;
  cd bundles/spleen_ct_segmentation;
  python -m monai.bundle run ...
```

## Fine-tuning で事前学習重みがロードされない

**症状**: 100 epoch fine-tuning したのに epoch 1 の loss が非常に大きい (~1.0)、または Dice がゼロから始まる。

**原因**: `configs/train.json` **単体で実行**した (Bundle の train config は checkpoint をロードしない設定)。

**対処**: `aml/finetune.json` を必ず重ねる:

```bash
--config_file "['configs/train.json','configs/finetune.json']"
```

Job ログで以下が出ていれば OK:

```
Restored all variables from ./models/model.pt
```

## Validation Dice が公称値に届かない

**症状**: fine-tuning 後の validation Dice が 0.85 以下。

**チェックポイント**:

1. **Bundle の想定前処理を上書きしていないか**:
   - `RAS` orientation、spacing `[1.5, 1.5, 2.0]`、CT window `[-57, 164]` は Bundle 学習時と揃える
2. **cache_rate=1.0 で全 volume が RAM に載っているか**:
   ```bash
   # A100 (220 GiB RAM) なら余裕。T4 (28 GiB RAM) では 0.3 程度に下げる
   ```
3. **epochs が少なすぎないか**: pretrained からの fine-tune なら 50〜100 epoch が目安
4. **learning rate**: Bundle 標準 (Novograd, lr=0.002) はゼロから学習用。fine-tune は 1/10 (2e-4) に下げるほうが安定:
   ```bash
   "--train#optimizer#lr=0.0002"
   ```
5. **dataset の split**: `configs/train.json` の split は再現性のため固定。異なる split で validation すると値が動く

## Data Asset が Job から見えない

**症状**: Job ログに `Path does not exist` や `azureml://datastores/... not found`.

**確認**:

```bash
# Data Asset が登録されているか
az ml data show \
  --name task09-spleen \
  --version 1 \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query "{path:path,type:type}" \
  -o jsonc

# Blob に実データがあるか (workspaceblobstore の実体コンテナ名を動的に解決)
CONTAINER=$(az ml datastore show \
  --name workspaceblobstore \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query container_name -o tsv)

az storage blob list \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --auth-mode login \
  --container-name "$CONTAINER" \
  --prefix "datasets/Task09_Spleen/" \
  --query "length(@)" -o tsv
# → 103 (imagesTr 41 + labelsTr 41 + imagesTs 20 + dataset.json 1) が期待値
```

不一致であれば `scripts/upload-dataset.sh` を再実行。

## Cluster が 0 ノードに縮小されない

**症状**: Job 完了後 5 分経ってもノードが残る。

**確認**:

```bash
az ml compute show \
  --name monai-a100 \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query "{min:min_instances,idle:idle_time_before_scale_down,current:current_node_count}" \
  -o jsonc
```

- `min: 0` かつ `idle: 120` (秒) → **120 秒 + AML の scale-down 周期 (数分)** で 0 になる
- `min: 1` になっている → docs/05 の update コマンドで 0 に戻す

**即時停止**: リソース削除 (`az ml compute delete`) が確実。

## DICOM を直接 Bundle に渡すと失敗

**症状**: Bundle 実行時に `nibabel` の読み込みエラー、または「dataset.json が見つからない」。

**原因**: Spleen Bundle は **NIfTI 前提**。DICOM シリーズはそのまま渡せません。

**対処**: **匿名化・仮名化を先に完了してから** `dcm2niix` で NIfTI に変換:

> [!CAUTION]
> **`dcm2niix` は匿名化ツールではありません。** 変換後の NIfTI にも patient/study
> 識別に転用可能な情報が残ります。施設 DICOM を扱う場合は以下を **変換前に完了**
> してください (詳細は README §「施設 DICOM を扱う場合」の 4 項目):
> 1. **DICOM PS3.15 Basic Application Confidentiality Profile** に沿った tag 除去
>    (PatientName/ID/BirthDate/BirthTime、SOPInstanceUID/StudyInstanceUID/SeriesInstanceUID の
>    pseudonymize、AccessionNumber、Institution/Physician 名、Private tag 全消去)
> 2. **JESRA TR-0045** 相当の日本国内向け拡張匿名化
> 3. **Burned-in text overlay の除去** (画素領域に焼き込まれた PatientID/日付 —
>    OCR + inpainting、または該当スライス除外)
> 4. **ファイル名の再命名** (`PatientID_...` を含めない中立名 e.g. `case001.nii.gz`)
> 5. **NIfTI/JSON sidecar のヘッダ検査** — `dcm2niix -z y -b y -ba y` (`-ba y` で
>    BIDS sidecar 匿名化を有効) を使い、生成された `.json` の PatientName/Study 系
>    フィールドが空か確認。`nifti_info` / `AFNI 3dinfo` でヘッダも確認
> 6. **アップロード時のファイル allowlist** — `.nii.gz` と `.json` (匿名化済み) のみ
>    アップロードし、生 DICOM や dcm2niix の中間ファイルは絶対にアップロードしない

```bash
# ローカル PC で (施設ネットワーク内の隔離環境を推奨)
sudo apt install dcm2niix  # または brew install dcm2niix

# 匿名化済み DICOM ディレクトリを対象に、中立ファイル名 + BIDS sidecar 匿名化で変換
mkdir -p ./nifti
dcm2niix -z y -b y -ba y -f "case%3s" -o ./nifti ./anonymized-dicom-series

# 変換後、sidecar 目視確認
for j in ./nifti/*.json; do
  python -c "import json; d=json.load(open('$j')); print('$j'); \
    [print(f'  {k}:', v) for k,v in d.items() if k in ('PatientName','PatientID','StudyID','InstitutionName','SeriesInstanceUID','StudyInstanceUID')]"
done
# 何か出力されたらそのフィールドが残っている → 元の DICOM 匿名化を見直す
```

Task09_Spleen と同じ構造 (`imagesTr/`, `labelsTr/`, `dataset.json`) に整えてから Blob にアップロードします。

参考: https://github.com/rordenlab/dcm2niix

## その他の役立つコマンド

```bash
# 直近の Job 一覧
az ml job list \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --max-results 10 \
  --query "[].{name:name,status:status,duration:duration}" \
  -o table

# Job のログを取得
az ml job stream \
  --name <job-name> \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME"

# 特定 Job のエラー詳細
az ml job show \
  --name <job-name> \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query "properties.status_transitions" -o jsonc
```

## 参考リンク

- Project MONAI: https://github.com/Project-MONAI/MONAI
- Model Zoo (Spleen Bundle): https://github.com/Project-MONAI/model-zoo/tree/dev/models/spleen_ct_segmentation
- Medical Segmentation Decathlon: http://medicaldecathlon.com/
- AzureML CLI reference: https://learn.microsoft.com/cli/azure/ml
- AzureML managed network: https://learn.microsoft.com/azure/machine-learning/how-to-managed-network
- NC A100 v4 series: https://learn.microsoft.com/azure/virtual-machines/sizes/gpu-accelerated/nca100v4-series
