# トラブルシューティング

## `RuntimeWarning: invalid value encountered in log/sqrt`

- gplearn は保護演算 (`_protected_sqrt`, `_protected_log`) を使うため実行は続行。無視して OK。

## 発見式が真の式と全く違う

- gen 数を増やす: `--generations 60`
- population を増やす: `--population 5000`
- `--parsimony 0.005` に上げて短い式を強制

## 決定係数 R² がマイナス

- ノイズレベル (data 生成の `--noise`) が高すぎる可能性
- 演算子集合が足りない (真の式に必要な演算子を追加)

## 実行が遅い

- `n_jobs=-1` に変更 (train.py 内) で並列化 (Windows は不安定なことあり)
- population/generations を減らす
