# サンプルデータ

このディレクトリには初期状態でデータファイルはありません (すべて `.gitignore` 済み)。以下のコマンドで再生成できます:

```bash
export MP_API_KEY=<your-key>
python src/fetch_data.py --output data/mp-bandgap.parquet     # ~1500 rows, ~10-50MB
python src/featurize.py --input data/mp-bandgap.parquet --output data/features.parquet
python src/train.py --features data/features.parquet --output data/metrics.json
```

生成物:

| ファイル | 内容 |
|---|---|
| `mp-bandgap.parquet` | MP から取得した material_id, formula, band_gap, structure_json |
| `mp-bandgap.manifest.json` | mp-api バージョン、DB バージョン、クエリ条件、取得日時 |
| `features.parquet` | 132 次元 Magpie 特徴量 + material_id + formula + band_gap |
| `metrics.json` | Dummy / Linear / XGBoost の CV MAE と ホールドアウト評価 |
| `predictions.parquet` | ホールドアウトの真値と XGBoost 予測 |

**Materials Project データは CC BY 4.0** です。研究・発表で使う際は必ず以下を引用してください:

> Jain, A. et al. *APL Materials* 1, 011002 (2013). DOI: 10.1063/1.4812323
