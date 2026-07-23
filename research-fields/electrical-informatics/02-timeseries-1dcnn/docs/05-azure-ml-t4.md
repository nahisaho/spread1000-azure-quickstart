# 05 — Azure ML T4 で GPU 実行 (任意)

> [!NOTE]
> このシナリオはローカル CPU で完結します。この文書は **同じスクリプトを GPU で速く回してみたい** 場合の発展編です。E-1 (LLM LoRA) と違い、UCI HAR に GPU は必須ではありません。

## いつ Azure ML を使うか

| ケース | 推奨 |
|---|---|
| UCI HAR (5〜10 分, 32K params) | ローカル CPU で十分 |
| WISDM 全窓、より大きな 1D-CNN、複数 seed × 複数 fold | Azure ML T4 が快適 |
| ハイパラ探索 | AML の [sweep job](https://learn.microsoft.com/azure/machine-learning/how-to-tune-hyperparameters) |

## 事前準備

すでに Azure ML ワークスペースを持っている前提です。まだの場合は [Azure ML 公式チュートリアル](https://learn.microsoft.com/azure/machine-learning/tutorial-create-secure-workspace) を参照してください。

- `az` CLI と ML 拡張 (`az extension add -n ml`)
- `az login && az account set --subscription <SUB_ID>`
- ワークスペース設定: `az configure --defaults group=<RG> workspace=<WS>`
- T4 クォータ確認: `az vm list-usage --location <REGION> --query "[?contains(name.value, 'NCasT4')]"`

## Compute cluster 作成 (min-instances=0 で待機コスト 0)

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

`min-instances=0` により、ジョブが無い時は 0 ノードに縮小され、**アイドル料金は発生しません**。

## CommandJob YAML

`train_job.yml`:

```yaml
$schema: https://azuremlschemas.azureedge.net/latest/commandJob.schema.json
type: command

display_name: uci-har-1dcnn-t4
experiment_name: spread1000-biosignal

code: .

command: |
  python -m pip install --no-cache-dir scikit-learn==1.7.2 && \
  python src/prepare_data.py && \
  python src/train.py --device cuda --epochs 15 --batch-size 128 --seed 42 --output-dir ${{outputs.artifacts}} && \
  python src/evaluate.py --device cuda --output-dir ${{outputs.artifacts}}

environment: azureml://registries/azureml/environments/acpt-pytorch-2.8-cuda12.6/labels/latest

compute: azureml:gpu-t4

resources:
  instance_count: 1

outputs:
  artifacts:
    type: uri_folder

tags:
  dataset: uci-har
  model: compact-1d-cnn
  split: subject-independent-official-test
```

投入:

```bash
az ml job create -f train_job.yml
```

`labels/latest` は AzureML 側が随時更新するタグです。ジョブで追加インストールする `scikit-learn==1.7.2` は、キュレーション環境の Python バージョン (2026-07 現在 3.10) と互換な系列です。教材公開直前に以下で最新環境名と Python バージョンを確認してください:

```bash
az ml environment list --registry-name azureml \
  --query "[?contains(name, 'acpt-pytorch')].{name:name, latest:latest_version}" \
  --output table
```

## 費用の目安 (2026-07-23 現在)

Japan East の `Standard_NC4as_T4_v3` (Linux 従量課金) は **約 $0.71/時**（[Azure Retail Prices API 実測値](https://prices.azure.com/api/retail/prices?$filter=armRegionName%20eq%20%27japaneast%27%20and%20armSkuName%20eq%20%27Standard_NC4as_T4_v3%27%20and%20priceType%20eq%20%27Consumption%27)）。

1 USD = 155 円換算で:

| ステップ | 目安 |
|---|---:|
| ノード起動 + 環境準備 | 3〜5 分 |
| データ準備 | 1〜2 分 |
| 学習 (T4, 15 epoch) | 2〜4 分 |
| 評価 | < 1 分 |
| **合計 (概算)** | **10 分程度、約 18〜37 円** |
| ジョブ完了後アイドル (300 秒後スケールダウン) | 追加 5 分ぶん (**約 9 円**) |

**安全側の見積: 1 回あたり 20〜60 円**。為替、税、Spot 有無、初回イメージ Pull 時間により変動します。

## Spot でさらに節約

`Standard_NC4as_T4_v3` は Spot 対応です。学習が短時間なので中断されても影響が小さく、料金は 60〜90% オフになります。CommandJob 側で指定する場合:

```yaml
queue_settings:
  job_tier: spot
```

または compute cluster 側で低優先度を既定にする場合:

```bash
az ml compute create --name gpu-t4-spot --type amlcompute \
  --size Standard_NC4as_T4_v3 --min-instances 0 --max-instances 1 \
  --tier low_priority
```

中断されたら再投入するだけです。

## 後片付け

```bash
# compute を削除 (min-instances=0 なら残しても良い)
az ml compute delete --name gpu-t4 --yes
```

## Azure ML を選ぶ理由 (発展編)

- 完全なジョブ履歴と再現性 (image, code snapshot, environment 全部保存)
- 複数 seed / 複数 fold を **並列実行** できる
- MLflow で自動ロギング (`--report_to mlflow` 相当)
- モデルレジストリで版管理

これらは本教材のスコープ外ですが、SPReAD-1000 のように長期の研究プロジェクトでは早期に Azure ML に移行する価値があります。
