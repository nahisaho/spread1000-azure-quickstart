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

| preset | 出力次元 | 説明 |
|---|---|---|
| `magpie` | **132** | 22 元素物性 × 6 統計量 (mean, avg_dev, min, max, mode, range) |
| `megnet_el` | **80** | MEGNet の 16 次元元素埋め込み × 5 統計量 (mean, avg_dev, min, max, mode) |
| `matminer` | **65** | 内部プリセット (13 元素物性 × 5 統計量、Deml et al. 2016) |

> [!NOTE]
> MEGNet の**素の**元素埋め込みは 16 次元ですが、`ElementProperty.from_preset("megnet_el")` は組成中の各元素で統計量を取るため出力は 80 次元になります。混同しないよう注意してください。

## NaN の扱い

放射性元素や希ガスなど、Magpie 事典に含まれない元素があると特徴量計算が NaN を含みます。本教材の `featurize.py` は既定で `impute_nan=False` (matminer 0.10.1 の既定 `True` から**明示的にオフ**にしています) を渡し、NaN 行はそのまま出力に含まれ、`--drop-nan-rows` (既定 on) で削除します。

- `--no-drop-nan-rows`: NaN 行を残す (デバッグ用途)
- `--impute-nan`: matminer の平均値 imputation を有効化 (**化学的意味を持たない平均値**で埋めるため、通常は推奨しません)

`data/features.manifest.json` に削除した material_id 一覧が記録されるので、10% 超が落ちる場合はデータ取得時のフィルタ条件を見直してください。

> [!WARNING]
> `impute_nan=True` (matminer デフォルト) を使うと、`dropna()` で消えるはずだった行が「化学的に無意味な平均値」で埋められ、そのままモデルに投入されます。**サイエンスの結論を歪める**恐れがあるため、本教材ではオフにしています。

## 出力

- `data/features.parquet` — material_id, formula_pretty, 132 特徴列, band_gap (135 列)
- `data/features.manifest.json` — 入力 SHA-256、出力 SHA-256、preset、`impute_nan` 設定、matminer/pymatgen バージョン、入力行数、出力行数、削除された material_id 一覧、feature_names
- ファイルサイズは 1500 行で約 2〜5 MB

## 発展: 結晶構造ベースの特徴量

`SineCoulombMatrix`, `CrystalNNFingerprint` などは結晶構造そのものを使いますが、計算時間が長く、`fit(structures)` の事前呼び出しが必要です。本教材では組成ベースに絞っています。
