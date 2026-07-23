# 02 — 記号回帰による物理法則発見

**対象**: データから **解析式** を自動発見したい物理・地球科学系研究者
**目標**: 合成観測データ (例: ケプラー第3法則 $T^2 \propto a^3$) を **gplearn** の遺伝的プログラミングに与え、数式そのものを学習する体験を CPU で 3 分以内に得る
**手法**: gplearn `SymbolicRegressor` (遺伝的プログラミング、+, -, ×, /, sqrt, log 等の演算子ツリー探索)

> [!NOTE]
> 完全にローカル CPU 完結。gplearn は pure Python で追加バイナリ依存なし (Julia を必要とする PySR とは違って軽量)。

## 全体像

```
src/generate_data.py    # 合成観測データ: y = 2 x_0 * sin(x_1) + 0.5 x_0² + ノイズ
src/train.py            # SymbolicRegressor(population=2000, generations=30)
   ├→ 遺伝的アルゴリズムで数式木を進化
   ├→ 各世代で最良個体を報告
   └→ outputs/
       ├── best_program.txt     # 発見された最良数式
       ├── fitness_curve.png    # 世代 vs fitness
       └── metrics.json         # R², MSE, プログラム長
```

## クイックスタート

```bash
python -m pip install -r requirements.txt

python src/generate_data.py --out data/obs.npz --seed 42
python src/train.py --data data/obs.npz --generations 30 --seed 42
```

## タスク

生成する真の関係:
$$y = 2 x_0 \sin(x_1) + 0.5 x_0^2 + \epsilon$$
- $x_0, x_1 \in [-3, 3]$ ランダム 200 点
- $\epsilon \sim \mathcal{N}(0, 0.1)$

## スタック

| 種別 | 選定 | 理由 |
|---|---|---|
| ライブラリ | `gplearn==0.4.3` | pure Python, sklearn 互換 API, MIT ライセンス |
| 演算子集合 | +, -, ×, ÷, √, sin, cos, log | 物理法則で頻出 |
| 探索 | population=2000, generations=30 | CPU 3 分程度 |
| 選択 | tournament (default) | GP の標準 |

## ドキュメント

1. [前提条件](docs/01-prerequisites.md)
2. [記号回帰の考え方](docs/02-sr-concept.md)
3. [学習](docs/03-train.md)
4. [結果の解釈](docs/04-understand-results.md)
5. [別問題を試す](docs/05-other-problems.md) — ケプラー、フックの法則
6. [片付け](docs/06-cleanup.md)
7. [倫理と限界](docs/07-ethics-and-limits.md)

トラブル対応: [troubleshooting.md](troubleshooting.md)

## ライセンス

- `gplearn`: BSD-3-Clause
- コード: リポジトリのライセンス

## 免責

**発見された数式は「与えたデータを最もよく説明する式」であり、真の物理法則である保証はありません。**
- **未観測領域への外挿は危険**: GP は数値フィッティングを最適化するが、物理的一貫性を保証しない
- 発見式は必ず **独立データで検証**し、可能なら物理次元解析で妥当性を確認する
