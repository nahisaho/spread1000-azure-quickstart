# 03. 特徴量化 (matminer)

## 実行

```bash
python src/featurize.py \
  --input data/mp-bandgap.parquet \
  --output data/features.parquet
```

各構造の**組成**から 132 次元の Magpie 記述子を計算します (数分)。

## 使用する featurizer

`matminer.featurizers.composition.ElementProperty.from_preset("magpie")`

- 各元素の物理化学的性質 (原子量、電気陰性度、原子半径、電子親和力、価電子数、融点、電気/熱伝導率など) から統計量 (mean, avg_dev, min, max, mode, range) を計算
- **DFT 計算不要**、CPU で高速
- 132 次元固定

## 他の選択肢 (任意)

```bash
python src/featurize.py --input ... --output ... --preset megnet_el
```

- `megnet_el`: MEGNet の元素埋め込み (16 次元)。事前学習された埋め込みで表現力が高い
- `matminer`: matminer の内部プリセット (67 次元、Deml et al. 2016)

> [!NOTE]
> `MEGNetElementEmbedding` クラスは存在しません。**`ElementProperty.from_preset("megnet_el")`** を使ってください。

## NaN の扱い

放射性元素や希ガスなど、Magpie 事典に含まれない元素があると特徴量計算が NaN を含みます。`featurize.py` は既定で NaN 行を削除し、削除件数を stderr に表示します。

削除件数が想定より多い (10% 超) 場合は、取得データに希元素が多く混入していないか `data/mp-bandgap.parquet` を確認してください。

## 出力

- `data/features.parquet` — material_id, formula_pretty, 132 特徴列, band_gap (135 列)
- ファイルサイズは 1500 行で約 2〜5 MB

## 発展: 結晶構造ベースの特徴量

`SineCoulombMatrix`, `CrystalNNFingerprint` などは結晶構造そのものを使いますが、計算時間が長く、`fit(structures)` の事前呼び出しが必要です。本教材では組成ベースに絞っています。
