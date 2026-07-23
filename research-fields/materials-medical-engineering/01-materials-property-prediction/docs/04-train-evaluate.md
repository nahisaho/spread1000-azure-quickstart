# 04. 学習と評価

## 実行

```bash
python src/train.py --features data/features.parquet --output data/metrics.json
```

以下 3 モデルを 5-fold CV + 80/20 ホールドアウトで評価します (30 秒程度):

1. **DummyRegressor(strategy="mean")** — 学習データ平均を出すだけのベースライン
2. **LinearRegression** — SimpleImputer + StandardScaler + 線形回帰
3. **XGBRegressor** — 勾配ブースティング (n_estimators=500, max_depth=6, lr=0.05)

## 期待される出力

```
[train] X shape=(1500, 132), y stats: mean=2.318 std=1.104
[train] dummy_mean : CV MAE=0.907±0.024 | holdout MAE=0.912 RMSE=1.101 R²=-0.001
[train] linear     : CV MAE=0.720±0.030 | holdout MAE=0.712 RMSE=0.902 R²=0.320
[train] xgboost    : CV MAE=0.560±0.025 | holdout MAE=0.554 RMSE=0.735 R²=0.552
```

> [!NOTE]
> 上記は目安です。実データ・シード次第で数値は変動します。**必ず DummyRegressor と LinearRegression を上回っている**ことを確認してください (XGBoost が下回っている場合、特徴量化 or データ取得に問題があります)。

## 出力ファイル

| ファイル | 内容 |
|---|---|
| `data/metrics.json` | 全モデルの CV MAE + ホールドアウト MAE/RMSE/R² |
| `data/predictions.parquet` | XGBoost のホールドアウト予測 (material_id, band_gap_true, band_gap_pred_xgboost) |

## パフォーマンス改善の方向

1. **データを増やす**: `--num-chunks 5` などで 5000 件に (時間 3〜5 分)
2. **モデルパラメータ調整**: `--n-estimators 1000 --max-depth 8 --learning-rate 0.03`
3. **特徴量の追加**: `Composition + Structure` featurizer (SineCoulombMatrix 等) をパイプライン化
4. **より現実的な汎化評価**: 本スクリプトは既定で `formula_pretty` (reduced formula) をキーにした `GroupShuffleSplit` (ホールドアウト) と `GroupKFold` (CV) を使い、同一組成の多形が train/test に混ざる composition leakage を防いでいます。さらに厳しい評価をしたい場合、元素種でグループ化する ElementGroupKFold を検討してください。

## 予測結果の可視化 (任意)

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_parquet("data/predictions.parquet")
plt.figure(figsize=(6, 6))
plt.scatter(df["band_gap_true"], df["band_gap_pred_xgboost"], alpha=0.3, s=10)
plt.plot([0, 5], [0, 5], "k--", lw=1)
plt.xlabel("True band gap (eV, DFT)")
plt.ylabel("Predicted band gap (eV)")
plt.title("XGBoost holdout parity plot")
plt.tight_layout()
plt.savefig("data/parity.png", dpi=120)
```

## 想定コスト

- **ローカル / WSL2**: $0
- **AML Compute Instance E2s_v3**: 30 分で約 **$0.08** (Japan East 従量課金 $0.16/h)
- **Cloud Shell**: ホスト無料 (Azure Files に若干)
