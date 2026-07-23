# 04 — 結果の解釈

## best_program.txt

gplearn の S 式表現:
```
add(mul(mul(2.0, X0), sin(X1)), mul(0.5, mul(X0, X0)))
```

これは Python で `2.0 * X[0] * sin(X[1]) + 0.5 * X[0] * X[0]` に相当。**真の関数と一致**していれば大成功。

## sympy で読みやすく

```python
import sympy as sp
from gplearn.functions import _function_map
# 手動で S 式 → sympy 変換 (簡易)
prog_str = open("outputs/best_program.txt").read().strip()
# 実際には gplearn.export_graphviz or 手動パース
```

## pred_vs_true.png

- 対角線 (y=x) 付近に散布 = 良好
- 大きく外れる点 = 発見式が真の式と構造的に違う (よくある)

## R² 目安

| R² | 意味 |
|---|---|
| > 0.99 | 真の関数を再発見できた可能性大 |
| 0.90 - 0.99 | 良い近似だが構造は違うかも |
| < 0.90 | 世代数・集団サイズを増やす、演算子を追加 |

## パレートフロンティア

「精度と単純さのトレードオフ」を見たい場合、`SymbolicRegressor` の `_programs[-1]` から全ての個体を取り出して MAE vs length の散布図を描くと良い。
