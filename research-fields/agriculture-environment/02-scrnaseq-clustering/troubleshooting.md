# トラブルシューティング

## `ModuleNotFoundError: No module named 'leidenalg'`

`leidenalg` は本シナリオでは不要です。コードは `flavor="igraph"` (python-igraph バックエンド) を使用しています。
エラーが出る場合は `pip install igraph` を実行してください。`leidenalg` はインストール不要です。

## `sc.datasets.pbmc3k()` がタイムアウト

scanpy 1.10+ は `falexwolf.de` から変換済み H5AD をダウンロードします。ネットワーク不安定なら:

```bash
# 手動でダウンロードして data/ に配置
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/02-scrnaseq-clustering"
cd "$SCENARIO_DIR"
test -f src/analyze.py || { echo "wrong dir — aborting"; exit 1; }
curl -L -o data/pbmc3k_raw.h5ad https://falexwolf.de/data/pbmc3k_raw.h5ad
```

## Leiden クラスタが 1 個しかできない

- resolution を上げる (`--resolution 1.0`)
- neighbors の k を減らす (`--k-neighbors 5`)
- QC で細胞を絞りすぎていないか確認

## メモリ不足 (数万細胞以上)

**⚠️ 注意**: 単純なダウンサンプリング (`sc.pp.subsample`) は細胞の多様性を損なうため推奨しません。代わりに以下を検討してください:

- **backed AnnData**: `sc.read_h5ad("file.h5ad", backed="r")` でメモリ外読み込み
- **sparse-aware 処理の維持**: `sc.pp.scale(zero_center=False)` で疎行列のまま処理 (`--no-zero-center` オプション)
- **Dask 統合**: 大規模データには `dask-expr` + AnnData バックエンドを検討
- **`--max-dense-cells`**: デフォルト 5e7 を超える場合は自動でゼロセンタリングをスキップ

## marker heatmap がうまく描画されない

- `matplotlib.use("Agg")` を確実に import 前に設定 (X server なし環境)
- outputs/ ディレクトリが存在するか確認
