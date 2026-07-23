# 材料応用医工学 01: 材料物性予測 (band gap 回帰)

Materials Project API から結晶構造データを取得し、matminer で組成特徴量を計算、XGBoost で **band gap (バンドギャップ)** を回帰する CPU-only の教材です。

## 対象読者

- Azure と Python は触ったことがあるが、materials informatics は初めて
- MP API・matminer・XGBoost をひとつのパイプラインでつないだ動作例が欲しい
- GPU なし、無料 API のみで完結する最短経路が知りたい

## 学習内容

1. **データ取得** — MP API v2 (`mp-api` 0.46.4) で 1〜3元素・0.1〜5.0 eV の band gap をもつ結晶を約 1500 件取得
2. **特徴量化** — Matminer `ElementProperty.from_preset("magpie")` で 132 次元の組成特徴量
3. **学習** — XGBRegressor + KFold(5) で MAE / R² を評価、DummyRegressor と LinearRegression をベースライン比較
4. **予測結果の保存** — `data/predictions.parquet` にホールドアウトの実測・予測ペア、`data/metrics.json` にスコア

## 使用サービス

| コンポーネント | 用途 | コスト |
|---|---|---|
| Materials Project API | 結晶構造 + DFT band gap 取得 | **無料** (要 API キー、25 req/s) |
| ローカル / WSL2 / Cloud Shell | 特徴量化 + 学習 (CPU-only) | **$0** |
| Azure ML Compute Instance (任意) | 再現性が必要な場合 | 約 $0.16/h (E2s_v3, Japan East) |

## 主要な設計判断

- **推奨実行環境**: WSL2 または Cloud Shell (どちらも Python 3.12)。AML は再現性・共有時のみ
- **Python 3.12 を推奨**: matminer は Python 3.13 の公式 classifier を持たない
- **GNoME を除外**: `include_gnome=False` を必ず指定 (GNoME データは CC BY-NC、教材再配布に不向き)
- **Structure は JSON で保存**: pickle は互換性リスク。`Structure.as_dict()` を JSON 文字列にして Parquet に格納
- **`xgboost-cpu` を使用**: GPU 版を要求しないため軽量パッケージで十分

## クイックスタート

```bash
# 1. Python 3.12 環境
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. MP API キー設定 (https://next-gen.materialsproject.org/dashboard で取得)
export MP_API_KEY=your_mp_api_key_here

# 3. データ取得 (~5-10 分、1500 件)
python src/fetch_data.py --output data/mp-bandgap.parquet

# 4. 特徴量化 (~1-2 分)
python src/featurize.py --input data/mp-bandgap.parquet --output data/features.parquet

# 5. 学習 + 評価 (~30 秒)
python src/train.py --features data/features.parquet --output data/metrics.json
```

詳細は [docs/](docs/) を参照。

## ドキュメント

1. [01 前提条件](docs/01-prerequisites.md)
2. [02 データ取得 (MP API)](docs/02-fetch-data.md)
3. [03 特徴量化 (matminer)](docs/03-featurize.md)
4. [04 学習と評価 (XGBoost)](docs/04-train-evaluate.md)
5. [05 クリーンアップ](docs/05-cleanup.md)
6. [06 倫理と限界 (ライセンス・適用範囲)](docs/06-ethics-and-limits.md)

トラブルシューティング: [troubleshooting.md](troubleshooting.md)

## 想定コスト

デモを 1 回実行すると **$0** (ローカル / WSL2) または **$0.05〜0.10** (Cloud Shell の Azure Files 少額 / AML Compute Instance 30 分) です。

## 引用

このデータを研究に用いる際は以下を引用してください:

> Jain, A. *et al.* Commentary: The Materials Project: A materials genome approach to accelerating materials innovation. **APL Materials** 1, 011002 (2013). DOI: [10.1063/1.4812323](https://doi.org/10.1063/1.4812323)

Materials Project データのライセンスは **CC BY 4.0** です (GNoME を除く)。
