# 03 — 反応データの準備

## 反応データ (デモ)

このシナリオでは 5 反応のデモデータを同梱しています ([`data/demo-reactions.csv`](../data/demo-reactions.csv))。列は：

- `reactants` — 反応物の SMILES（複数は `.` で連結）
- `reagents` — 試薬・触媒・溶媒の SMILES（無い場合は空欄可）
- `reference_product` — 参照生成物（精度比較用、無くても実行可）

例：

```csv
reactants,reagents,reference_product
COC(=O)C1=CCCN(C)C1.O.[Al+3].[H-].[Li+].[Na+].[OH-],C1CCOC1,CN1CCC=C(CO)C1
```

## workspaceblobstore にアップロード

```bash
cd research-fields/chemistry/02-reaction-prediction-reactiont5

# デフォルトの datastore (workspaceblobstore) を経由してアップロード
az ml data create \
  --name reactions-demo \
  --version 1 \
  --type uri_file \
  --path data/demo-reactions.csv \
  --description "5 sample reactions for ReactionT5v2 demo"
```

登録された Data Asset を確認：

```bash
az ml data show -n reactions-demo -v 1 -o table
```

## 自分の反応データを使う場合

CSV を `data/my-reactions.csv` として保存し、上のコマンドの `--path` と `--name` を差し替えて再登録してください。参照生成物が無い場合は `reference_product` 列を空欄にすると `top1_accuracy` は計算されず、予測 SMILES のみが出力されます。

> [!TIP]
> ReactionT5v2 は USPTO-MIT (有機反応データベース) で学習されているため、有機小分子反応が最も得意です。金属錯体や高分子は精度が落ちます。

次: [`04-predict-and-evaluate.md`](04-predict-and-evaluate.md)
