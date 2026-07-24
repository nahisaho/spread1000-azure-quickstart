# 04 — 結果の解釈

## best_program.txt

gplearn の S 式表現:
```
add(mul(X0, sin(X1)), mul(X0, X0))
```

これは Python で `X[:, 0] * sin(X[:, 1]) + X[:, 0] * X[:, 0]` に相当。**真の関数と一致**していれば大成功。

## sympy で読みやすく

```python
import sympy as sp
from gplearn.functions import _function_map
# 手動で S 式 → sympy 変換 (簡易)
prog_str = open("outputs/best_program.txt").read().strip()
# 実際には est._program.export_graphviz() or 手動パース
```

## pred_vs_true.png

- 対角線 (y=x) 付近に散布 = 良好
- 大きく外れる点 = 発見式が真の式と構造的に違う (よくある)

## R² 目安 (参考値 illustrative)

| R² | 意味 |
|---|---|
| > 0.99 | 予測適合が良好。真の関数再発見の主張には シンボリック簡約 + 密な独立評価 + 次元解析 + 外挿テストが別途必要 |
| 0.90 - 0.99 | 良い近似だが構造は違うかも |
| < 0.90 | 世代数・集団サイズを増やす、演算子を追加 |

## ハイパーパラメータ調整 (検証セットで行う)

> **重要**: ハイパーパラメータはテストセットではなく **検証セット (val)** の指標を使って調整する。テストセットは最終評価のみに使用し、結果報告まで参照しないこと。

| Val R² | 推奨アクション |
|---|---|
| > 0.99 | このまま test で最終評価 |
| 0.90 - 0.99 | `--generations` を増やす、または `--population` を増やす |
| < 0.90 | 演算子を追加、ノイズを確認 |

## パレートフロンティア

「精度と単純さのトレードオフ」を見たい場合、`SymbolicRegressor` の `_programs[-1]` から全ての個体を取り出して MAE vs length の散布図を描くと良い。
