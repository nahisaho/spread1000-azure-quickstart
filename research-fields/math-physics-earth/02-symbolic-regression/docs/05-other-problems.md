# 05 — 別問題を試す

## ケプラー第3法則: T² ∝ a³

太陽系惑星の (半長軸 a, 公転周期 T) データから対数変換を用いて線形回帰で検証する方法:

```python
import numpy as np
from sklearn.linear_model import LinearRegression

# データ源: NASA Planetary Fact Sheet
# https://nssdc.gsfc.nasa.gov/planetary/factsheet/
# a: AU (天文単位), T: 年
a = np.array([0.387, 0.723, 1.0, 1.524, 5.203, 9.537, 19.19, 30.07])
T = np.array([0.241, 0.615, 1.0, 1.881, 11.86, 29.46, 84.02, 164.8])

# log(T) = 1.5 * log(a) + const → 傾き 1.5 を回収する
log_a = np.log(a).reshape(-1, 1)
log_T = np.log(T)
model = LinearRegression().fit(log_a, log_T)
print(f"slope = {model.coef_[0]:.4f}  (理論値 1.5)")
```

gplearn で非線形探索をしたい場合は、べき乗演算を **カスタム保護関数** として定義する:

```python
import numpy as np
from gplearn.functions import make_function
from gplearn.genetic import SymbolicRegressor

def _protected_pow(x1, x2):
    with np.errstate(over="ignore", invalid="ignore"):
        result = np.where(
            np.abs(x1) < 1e-12,
            1.0,
            np.sign(x1) * np.abs(x1) ** np.clip(x2, -3, 3),
        )
    return np.where(np.isfinite(result), result, 1.0)

protected_pow = make_function(function=_protected_pow, name="pow", arity=2)

est = SymbolicRegressor(
    function_set=("add", "mul", "div", protected_pow),
    population_size=500,
    generations=20,
    random_state=42,
    verbose=1,
)
# X = log_a, y = log_T  (または生データで直接)
est.fit(log_a, log_T)
print(est._program)
```

> **注意**: gplearn の組み込み `function_set` に文字列 `"pow"` は存在しない。必ず上記のように `make_function` でカスタム定義すること。

## フックの法則: F = k x

線形 → 極めて簡単。線形回帰と GP を比較する良い教材。

## 実際のベンチマーク

記号回帰の網羅的ベンチマークは **SRBench** を参照:
- https://github.com/cavalab/srbench

物理・生物・経済など多様な実データセットで各アルゴリズムを比較している。

## 実データへの適用

- **気象時系列**: 気温 vs 太陽放射量 → 熱伝達方程式的な形が現れうる
- **化学反応速度**: `k = A exp(-E/RT)` (アレニウス式)
- **流体力学**: レイノルズ数、ヌセルト数の相関式

## 落とし穴

- **次元** を持つ量に GP を適用する場合、次元的に整合な式を制約する仕組み (dimensional constraints) が gplearn には無い → 手動で対数を取る等の前処理を推奨
- **多変数** (5 変数以上) では集団サイズを 5000+ に増やす必要
