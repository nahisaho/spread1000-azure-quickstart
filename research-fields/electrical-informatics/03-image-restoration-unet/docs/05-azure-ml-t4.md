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

- `az` CLI + ML 拡張 (`az extension add -n ml`)
- `az login && az account set --subscription <SUB_ID>`
- ワークスペース設定: `az configure --defaults group=<RG> workspace=<WS>`
- T4 クォータ確認: `az vm list-usage --location <REGION> --query "[?contains(name.value, 'NCasT4')]"`

## Compute cluster 作成 (min-instances=0)

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

## CommandJob YAML

`train_job.yml`:

```yaml
$schema: https://azuremlschemas.azureedge.net/latest/commandJob.schema.json
type: command

display_name: image-restoration-unet-t4
experiment_name: spread1000-image-restoration

code: .

command: |
  python -m pip install --no-cache-dir \
    scikit-image==0.24.0 scipy==1.13.1 numpy==1.26.4 \
    matplotlib==3.9.2 torchmetrics==1.4.3 && \
  python src/generate_data.py --n-train 500 --n-val 100 --seed 42 && \
  python src/train.py --device cuda --epochs 30 --batch-size 32 --seed 42 --output-dir ${{outputs.artifacts}} && \
  python src/evaluate.py --device cuda --output-dir ${{outputs.artifacts}}

environment: azureml://registries/azureml/environments/acpt-pytorch-2.8-cuda12.6/labels/latest

compute: azureml:gpu-t4

resources:
  instance_count: 1

outputs:
  artifacts:
    type: uri_folder

tags:
  task: image-restoration
  model: mini-unet
  degradation: gaussian-noise-sigma-0.10
```

投入:

```bash
az ml job create -f train_job.yml
```

キュレーション環境の Python バージョンは (2026-07 現在) 3.10 なので、追加インストールするパッケージは Python 3.10 互換のバージョンを指定しています。

環境名 (`labels/latest`) はマイクロソフト側の更新で変わり得るので、公開直前に以下で最新名と Python バージョンを確認してください:

```bash
az ml environment list --registry-name azureml \
  --query "[?contains(name, 'acpt-pytorch')].{name:name, latest:latest_version}" \
  --output table
```

## 費用の目安 (2026-07-23 現在)

Japan East `Standard_NC4as_T4_v3` (Linux 従量課金) 約 $0.71/時。1 USD = 155 円換算:

| ステップ | 目安 |
|---|---:|
| ノード起動 + 環境準備 | 3〜5 分 |
| データ生成 (500 train + 100 val) | 30 秒 |
| 学習 (T4, 30 epoch) | 3〜5 分 |
| 評価 | 30 秒 |
| **合計 (概算)** | **10 分程度、約 18〜37 円** |

**安全側の見積: 1 回あたり 20〜60 円**。

## Spot でさらに節約

```yaml
queue_settings:
  job_tier: spot
```

学習時間が短いので中断されても影響は限定的です。

## 後片付け

```bash
az ml compute delete --name gpu-t4 --yes
```
