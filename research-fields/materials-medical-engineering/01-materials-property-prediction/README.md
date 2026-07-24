# 材料応用医工学 01: 材料物性予測 (band gap 回帰)

Materials Project API から結晶構造データを取得し、matminer で組成特徴量を計算、XGBoost で **band gap (バンドギャップ)** を回帰する **ローカル / WSL2 完結・CPU-only** の教材です。

## 対象読者

- Python は触ったことがあるが、materials informatics は初めて (Azure の事前知識は不要)
- MP API・matminer・XGBoost をひとつのパイプラインでつないだ動作例が欲しい
- GPU なし、無料 API のみで完結する最短経路が知りたい

## 学習内容

1. **データ取得** — MP API v2 (`mp-api` 0.46.4) で 1〜3元素・0.1〜5.0 eV の band gap をもつ結晶を約 1500 件取得
2. **特徴量化** — Matminer `ElementProperty.from_preset("magpie")` で 132 次元の組成特徴量
3. **学習** — XGBRegressor + `reduced-formula GroupKFold(5) + GroupShuffleSplit` ホールドアウトで MAE / R² を評価、DummyRegressor と LinearRegression をベースライン比較
4. **予測結果の保存** — `data/predictions.parquet` にホールドアウトの実測・予測ペア、`data/metrics.json` にスコア (ハイパーパラメータ + パッケージバージョン + SHA-256 チェーン込み)、`data/model_xgboost.ubj` に学習済みモデル、`data/split_ids.json` に train/test material_id

## 使用サービス

| コンポーネント | 用途 | コスト |
|---|---|---|
| Materials Project API | 結晶構造 + DFT band gap 取得 | **無料** (要 API キー、25 req/s) |
| ローカル / WSL2 (Linux/Windows) または macOS | 特徴量化 + 学習 (CPU-only) | **$0** |

> [!NOTE]
> **本教材は Azure リソースを一切作成しません**。既存の Azure ML ワークスペースで実行したい場合の参考手順は `docs/01-prerequisites.md §Azure ML で実行したい場合` にあります。Cloud Shell は Python 3.9 系のためサポート外です (本教材は Python 3.12)。

## 主要な設計判断

- **推奨実行環境**: ローカル / WSL2 (Python 3.12)。macOS は `xgboost-cpu` 非対応のため通常の `xgboost` パッケージを条件付きで導入 (`requirements.txt` 参照)
- **Python 3.12 を推奨**: matminer は Python 3.13 の公式 classifier を持たない
- **GNoME を除外**: `include_gnome=False` を必ず指定 (GNoME データは CC BY-NC で本教材の CC BY 4.0 統一運用と非互換のため。GNoME を使いたい場合は GNoME 個別ライセンスを直接確認)
- **Structure は JSON で保存**: pickle は互換性リスク。`Structure.as_dict()` を JSON 文字列にして Parquet に格納
- **`xgboost-cpu` を使用** (Linux/Windows): GPU 版を要求しないため軽量パッケージで十分

## クイックスタート

```bash
# 1. Python 3.12 環境 (WSL2 / Linux / macOS)
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

# 6. 出力の整合性検証 (SHA-256 チェーン + 分布 + train/test disjoint 等)
python src/verify.py
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

本教材はローカル / WSL2 / macOS で完結し、**Azure リソースを作成しないため課金は発生しません**。参考として自分で Azure ML Compute Instance (`Standard_E2s_v3`, PAYG) を用意して実行する場合は 30 分で概ね $0.08 ですが、**idle shutdown を必ず設定**しないと使わない時間も課金され続けます。詳細は `docs/01-prerequisites.md`。

## 引用

このデータを研究に用いる際は以下を引用してください:

> Jain, A. *et al.* Commentary: The Materials Project: A materials genome approach to accelerating materials innovation. **APL Materials** 1, 011002 (2013). DOI: [10.1063/1.4812323](https://doi.org/10.1063/1.4812323)

特徴量に matminer / Magpie を使うため、以下も併記してください:

> Ward, L. *et al.* Matminer: An open source toolkit for materials data mining. **Comput. Mater. Sci.** 152, 60-69 (2018). DOI: [10.1016/j.commatsci.2018.05.018](https://doi.org/10.1016/j.commatsci.2018.05.018)
>
> Ward, L. *et al.* A general-purpose machine learning framework for predicting properties of inorganic materials. **npj Comput. Mater.** 2, 16028 (2016). DOI: [10.1038/npjcompumats.2016.28](https://doi.org/10.1038/npjcompumats.2016.28)

Materials Project データのライセンスは **CC BY 4.0** です (GNoME を除く。GNoME を含める場合は GNoME 側の個別ライセンス条件を確認してください)。
