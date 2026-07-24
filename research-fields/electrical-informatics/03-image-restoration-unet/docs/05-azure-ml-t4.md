# 05 — Azure ML T4 で GPU 実行 (任意)

> [!NOTE]
> このシナリオはローカル CPU で完結します。この文書は **同じスクリプトを GPU で速く回してみたい** 場合の発展編です。117K params の MiniUNet に GPU は必須ではありません。

## いつ Azure ML を使うか

| ケース | 推奨 |
|---|---|
| 128×128, 200 サンプル, 20 epoch | ローカル CPU で十分 |
| 512×512, 数千サンプル、ハイパラ探索 | Azure ML T4 が快適 |
| 実データ (RAW / 磁気光学) 数万枚 | Azure ML A100 sweep job |

## 事前準備

```bash
# 1. インフラ展開 (Bicep + deploy.sh)
RG=my-rg LOC=japaneast PREFIX=e3unet SUB_ID=<your-sub-id> \
  bash infra/deploy.sh
source .env   # AML_WORKSPACE_NAME, AML_RESOURCE_GROUP 等を読み込む

# 2. GPU 環境を AML に登録 (初回のみ)
az ml environment create \
  -f infra/environments/gpu/environment.yml \
  -g "$AML_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME"

# 3. T4 クォータ確認 (AML ワークスペースの quota を使う; az vm list-usage とは別)
az ml compute list-usage \
  -g "$AML_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME" \
  -l "$AML_LOCATION" -o table
```

## Compute cluster 作成 (low_priority, min-instances=0)

```bash
az ml compute create \
  --name gpu-t4 \
  --type amlcompute \
  --size Standard_NC4as_T4_v3 \
  --min-instances 0 \
  --max-instances 1 \
  --idle-time-before-scale-down 300 \
  --tier low_priority \
  -g "$AML_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME"
```

> [!IMPORTANT]
> `--tier low_priority` がスポット割引を有効にします。`--tier Dedicated` では割引なし。
> ジョブ YAML に `queue_settings.job_tier: spot` は**不要かつ誤り** — cluster tier は作成時に確定します。

## CommandJob YAML

`azureml/train_job.yml` に committed な schema-valid YAML があります。投入:

```bash
az ml job create \
  -f azureml/train_job.yml \
  -g "$AML_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME"
```

> **環境について**: `azureml:e3-unet-gpu:1` は `infra/environments/gpu/` で定義した
> immutable な カスタム環境です (上記ステップ 2 で登録)。
> `labels/latest` のような浮動参照は使いません。
>
> 使用 MCR ベースイメージ:
> - GPU: `mcr.microsoft.com/azureml/openmpi5.0-cuda12.4-ubuntu22.04:20260715.v1`
> - CPU: `mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04:20260715.v1`
> `openmpi5.0-ubuntu22.04:*` (CUDA なし) は存在しません。

## 費用の目安

Japan East `Standard_NC4as_T4_v3` (Linux、low_priority) の最新料金は
[Azure Retail Prices API](https://prices.azure.com/api/retail/prices) で確認できます
(下記は参考値; 最終確認日 2026-07-24):

| ステップ | 目安 |
|---|---:|
| ノード起動 + 環境準備 | 3〜5 分 |
| データ生成 (500 train + 100 val + 50 test) | 30 秒 |
| 学習 (T4, 20 epoch) | 3〜5 分 |
| 評価 | 30 秒 |
| **合計 (概算)** | **10 分程度** |

low_priority は市場価格の約 60〜80% 引きで利用できますが、中断される可能性があります。
20 epoch の学習は短時間のため、中断されてもコスト影響は限定的です。

## 後片付け

詳細な手順は [docs/06-cleanup.md](06-cleanup.md) を参照してください。

```bash
source .env
az ml compute delete --name gpu-t4 \
  -g "$AML_RESOURCE_GROUP" -w "$AML_WORKSPACE_NAME" --yes
```
