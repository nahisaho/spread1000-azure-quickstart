# 05 — Azure ML T4 で GPU 実行 (任意)

> [!NOTE]
> このシナリオはローカル CPU で完結します。この文書は **同じスクリプトを GPU で速く回したい** 場合の発展編です。

## 事前準備

- `az login && az account set --subscription <SUB_ID>`
- `az extension add -n ml`
- Resource Group / Workspace をまだ作っていない場合は `./infra/deploy.sh`
- 既存ワークスペースの既定値設定: `az configure --defaults group=<RG> workspace=<WS>`
- AML クォータ確認:

```bash
az ml compute list-usage --resource-group "$RG" --workspace-name "$WS" -o table
```

## Compute cluster 作成

通常課金の Dedicated を使う場合:

```bash
az ml compute create \
  --name gpu-t4 \
  --type amlcompute \
  --size Standard_NC4as_T4_v3 \
  --min-instances 0 \
  --max-instances 1 \
  --idle-time-before-scale-down 300 \
  --tier Dedicated
```

低優先度 Spot 相当でさらに節約したい場合は、リポジトリ付属の `azureml/compute-low-priority.yml` を使います。

```bash
az ml compute create -f azureml/compute-low-priority.yml
```

## ジョブ定義

ジョブ定義は `azureml/train_job.yml` を使います。ポイント:

- `python src/prepare_data.py` → `train.py` → `evaluate.py` → `verify.py` を直列実行
- `timeout: 3600`
- custom environment: `azureml:spread-timeseries-gpu:1`
- verify step で SHA-256 / finite / macro-F1 を最終確認

投入:

```bash
az ml job create -f azureml/train_job.yml
```

## カスタム環境

GPU ベースイメージは検証済みの以下を使います。

- `mcr.microsoft.com/azureml/openmpi5.0-cuda12.4-ubuntu22.04:20260715.v1`

関連ファイル:

- `infra/environments/gpu/Dockerfile`
- `infra/environments/gpu/environment.yml`
- `infra/environments/gpu/requirements-gpu.in`

> [!IMPORTANT]
> `openmpi5.0-ubuntu22.04:*` は存在しません。GPU 環境は上記 CUDA 付きイメージを使ってください。

## Spot でさらに節約

CommandJob YAML の `queue_settings.job_tier: spot` は使わず、**compute 側を low priority で作る** 方針に統一します。`azureml/compute-low-priority.yml` を使って `tier: low_priority` のクラスターを作成してください。

## 費用の考え方

- `min_instances: 0` ならアイドル時の compute 料金は発生しません
- 課金対象は主に **ノード起動中 + ジョブ実行中**
- 短時間ジョブでも初回イメージ pull の待ち時間が上乗せされます

## 後片付け

- compute だけ消したい: `az ml compute delete --name gpu-t4 -g "$RG" -w "$WS" --yes`
- Resource Group ごと消したい: `./infra/cleanup.sh`
