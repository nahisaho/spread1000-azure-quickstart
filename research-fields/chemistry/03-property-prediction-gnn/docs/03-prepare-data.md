# 03 — ESOL データセットの準備

## MoleculeNet ESOL の CSV を取得

MoleculeNet の ESOL データセット (`delaney-processed.csv`, 1128 行, ~130 KB) を DeepChem の S3 バケットから取得します。

```bash
cd research-fields/chemistry/03-property-prediction-gnn

bash scripts/download-esol.sh
# → data/delaney-processed.csv が作成される
```

スクリプトは以下を行います：
1. `curl` で https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/delaney-processed.csv を取得
2. 行数を検証 (1129 行 = ヘッダー + 1128 分子)
3. `data/` に保存

## Data Asset として登録

**なぜ生 CSV を登録するか**: PyG が生成する `data.pt` は PyG / RDKit のバージョンに強く依存するので、**生 CSV** を登録して各ジョブ実行時に処理する方が再現性が高いです。

```bash
az ml data create \
  --name moleculenet-esol \
  --version 1 \
  --type uri_file \
  --path data/delaney-processed.csv \
  --description "MoleculeNet ESOL (Delaney 2004) aqueous solubility"
```

登録された Data Asset を確認：

```bash
az ml data show -n moleculenet-esol -v 1 -o table
```

## データの中身

| 列 | 内容 |
|---|---|
| Compound ID | 分子名 (例: Amigdalin) |
| ESOL predicted log solubility in mols per litre | Delaney の推定値 |
| Minimum Degree | 最小連結度 |
| Molecular Weight | 分子量 |
| Number of H-Bond Donors | 水素結合ドナー数 |
| Number of Rings | 環の数 |
| Number of Rotatable Bonds | 回転可能結合数 |
| Polar Surface Area | 極性表面積 |
| **measured log solubility in mols per litre** | **目的変数 y** |
| smiles | SMILES 文字列 (モデル入力) |

学習には `smiles` と `measured log solubility in mols per litre` のみを使います。

> [!TIP]
> ReactionT5v2 は違い、この GNN シナリオでは PyG の `MoleculeNet` ローダーが CSV の**末尾列を SMILES、末尾から 2 番目を目的変数**として固定で読み込みます（列名は無視）。独自データを使う際は同じスキーマにするか、`src/train.py` の `load_esol` を書き換えてください。詳細は [`docs/04-train-and-evaluate.md`](04-train-and-evaluate.md#自分のデータで試す) を参照。

次: [`04-train-and-evaluate.md`](04-train-and-evaluate.md)
