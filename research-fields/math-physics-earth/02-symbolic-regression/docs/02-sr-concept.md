# 02 — 記号回帰の考え方

## 通常の回帰との違い

| 通常 (線形回帰・NN 等) | 記号回帰 (GP) |
|---|---|
| モデル構造 (層数・特徴量) を先に決める | **構造そのものを探索**する |
| パラメータのみ最適化 | 演算子ツリー全体 (構造+定数) を探索 |
| 出力: 数値表 or ブラックボックス | 出力: **人間が読める数式** |

## 遺伝的プログラミング (GP)

1. **初期集団**: ランダムな数式木を population_size 個 (例 2000) 生成
2. **評価**: 各個体の **生の fitness** (今回は MAE) を計算。**調整済み fitness** は MAE に `parsimony_coefficient × 式長` を加えたペナルティ込みの値で、選択に用いる
3. **選択**: tournament で優秀な数個を親に
4. **交叉 (crossover)**: 親 2 つの部分木を交換
5. **突然変異 (mutation)**: 一部を書き換え / 置換 / hoist
6. **次世代へ**: これを generations 回 (例 30) 繰り返す (世代番号は 0 始まり: Gen 0 〜 Gen 29)

## 数式木

```
   add
   / \
  mul  mul
  / \  / \
 X0 X1 X0  X0
```

これは $x_0 x_1 + x_0^2$ を表す。

## Parsimony (簡潔性) の重要性

- 数式が長いほど**過学習**しやすく、可読性も低下
- `parsimony_coefficient` を上げると短い式を優先
- 短すぎると表現力不足 → データに合わない

## Fitness の意味

- 今回 `metric="mean absolute error"`
- **生の fitness (raw fitness)**: 個体の MAE そのもの — 小さいほど良い
- **調整済み fitness (adjusted fitness)**: `MAE + length × parsimony_coefficient` — 選択・進化に用いる内部値
- グラフに表示するのは **生の fitness (MAE)** なので、ペナルティの影響は含まれない
- 世代を追うごとに fitness が下がる (単調とは限らない、swarm-like)
