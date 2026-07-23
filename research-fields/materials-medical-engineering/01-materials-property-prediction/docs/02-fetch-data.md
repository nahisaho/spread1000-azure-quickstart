# 02. データ取得 (Materials Project API)

## 実行

```bash
python src/fetch_data.py --output data/mp-bandgap.parquet
```

既定条件 (1〜3 元素、band gap 0.1〜5.0 eV) で約 1500 件を取得します (数分)。

## 主要オプション

| オプション | 既定 | 説明 |
|---|---|---|
| `--num-elements-min / --max` | 1 / 3 | 元素数フィルタ |
| `--band-gap-min / --max` | 0.1 / 5.0 | band gap (eV) 範囲 |
| `--chunk-size` | 1000 | 1 チャンクあたりの取得件数 |
| `--num-chunks` | 2 | 取得するチャンク数 (上限件数 = chunk-size × num-chunks) |
| `--limit` | 1500 | 取得後にスライスする件数 |

## 出力

- `data/mp-bandgap.parquet` — material_id, formula_pretty, band_gap, nsites, nelements, structure_json (5 列 + 構造 JSON)
- `data/mp-bandgap.manifest.json` — mp-api バージョン、DB バージョン、クエリ条件、レコード数、SHA-256、取得日時

> [!IMPORTANT]
> `include_gnome=False` を必ず指定しています (`fetch_data.py` の既定)。GNoME (117,000 材料) は **CC BY-NC** ライセンスで**商用不可・教材再配布不可**のため除外しています。

## クエリのカスタマイズ

例: 二元素化合物のみ、band gap 1〜3 eV (光触媒候補):

```bash
python src/fetch_data.py --output data/photocat.parquet \
  --num-elements-min 2 --num-elements-max 2 \
  --band-gap-min 1.0 --band-gap-max 3.0
```

## レート制限とキャッシュ

- MP API は 25 req/s 制限
- `chunk_size=1000` はほぼ最大効率。大きくしすぎると `429 Too Many Requests`
- 一度取得した Parquet はローカルキャッシュとして扱い、頻繁に再取得しないでください (公式推奨: [Tips for Large Downloads](https://docs.materialsproject.org/downloading-data/using-the-api/tips-for-large-downloads.md))

## band gap 分布の確認

```python
import pandas as pd
df = pd.read_parquet("data/mp-bandgap.parquet")
print(df.band_gap.describe())
df.band_gap.hist(bins=40)
```

MP の band gap は **DFT 由来** (PBE / GGA + Hubbard U 等) で、実験値より系統的に小さくなります (bandgap underestimation problem)。詳細は [06-ethics-and-limits.md](06-ethics-and-limits.md) を参照。
