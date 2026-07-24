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

CSV を `data/my-reactions.csv` として保存し、上のコマンドの `--path` と `--name` を差し替えて再登録してください。参照生成物が無い場合は `reference_product` 列を空欄にすると `top1_accuracy` は計算されず、予測 SMILES のみが出力されます (`num_scored=0` として MLflow にも記録)。**空欄でない `reference_product` が RDKit でパース不能な場合、`predict.py` は行番号を明示して即座に失敗します** — top-1 精度が空欄行の隠れた除外で歪まないよう、無効な参照は「削除して未評価にする」か「正しい SMILES に修正する」か明示的に選択する必要があります。

## 同梱デモ CSV (`data/demo-reactions.csv`) の由来

`data/demo-reactions.csv` の 5 反応レコードは Open Reaction Database (ORD) 由来のデータを SPReAD-1000 用に抽出・改変したものです:

- **元出典**: Open Reaction Database ([https://open-reaction-database.org/](https://open-reaction-database.org/)) — CC BY-SA 4.0
- **改変内容**: (a) 元 ORD レコードの `ord_data.reaction_id` (例 `ord-...`) は本 CSV では保持していません（列を追加する予定）。(b) `reagents` 列は元 ORD レコードの溶媒/触媒/添加剤から人が抜粋しており、元レコードの完全な reagent リストではありません。(c) SMILES 表記は canonicalize せず ORD 提供値をそのまま採録しています。
- **継承ライセンス**: 上記改変を含めた本 CSV は CC BY-SA 4.0 で頒布されます (ORD の share-alike 条項)。第三者が本 CSV を再配布する場合も CC BY-SA 4.0 とその attribution 要件が及びます。
- **推奨**: 独自の研究で使う場合は本 CSV に依存せず、ORD の Python API または `ord-data` GitHub リポジトリから対象反応 ID を明示して取得することを推奨します。

> [!TIP]
> ReactionT5v2 は **ORD で学習**され、**USPTO-MIT ベンチマークで top-1 92.8% を達成**したモデルです（[Hugging Face モデルカード](https://huggingface.co/sagawa/ReactionT5v2-forward)）。金属錯体や高分子は精度が落ちます。

次: [`04-predict-and-evaluate.md`](04-predict-and-evaluate.md)
