# 03 — ガウス過程による周期信号フィッティング

**対象**: 観測値に **不確実性 (エラーバー)** をつけて予測したい天体・地球観測系研究者
**目標**: 合成周期信号 (系外惑星ライトカーブ模擬) をガウス過程で回帰し、**平均予測 + 95% 信頼区間** を可視化する
**手法**: `sklearn.gaussian_process.GaussianProcessRegressor` に RBF + ExpSineSquared kernel

> [!NOTE]
> 完全にローカル CPU 完結。1 分以内。ライブラリは scikit-learn のみで完結。

## 全体像

```
src/train.py

   ├→ 合成: y(t) = sin(2π t / 5) + 0.1 t + ノイズ
   ├→ 一部データ (30 点) のみ観測、残りは未観測
   ├→ Kernel = ExpSineSquared * ConstantKernel + WhiteKernel
   ├→ GP fit (最尤法でハイパラ最適化)
   ├→ 予測: 全 t 上で mean + std
   └→ outputs/
        ├── gp_fit.png       # データ点 + 予測平均 + 95%CI + 真の関数
        ├── residuals.png
        └── metrics.json     # RMSE, log-marginal-likelihood
```

## クイックスタート

```bash
python -m pip install -r requirements.txt
python src/train.py --seed 42
```

## タスク

- 真関数: $y(t) = \sin(2\pi t / 5) + 0.1 t$  ($t \in [0, 20]$)
- 観測ノイズ: $\epsilon \sim \mathcal{N}(0, 0.15)$
- 観測点: 30 点 (ランダムサンプル)
- **予測**: 200 点上で mean + std

## スタック

| 種別 | 選定 | 理由 |
|---|---|---|
| ライブラリ | `scikit-learn>=1.4` | GP 実装が付属、追加依存なし |
| Kernel | `ConstantKernel * ExpSineSquared + WhiteKernel` | 周期性を陽に表現 + ノイズ吸収 |
| ハイパラ最適化 | 最尤 (log-marginal likelihood 最大化) | GP 標準 |
| 予測 | `return_std=True` で 1σ | 95%CI = ±1.96σ |

## ドキュメント

1. [前提条件](docs/01-prerequisites.md)
2. [GP の考え方](docs/02-gp-concept.md)
3. [学習と予測](docs/03-train.md)
4. [結果の解釈](docs/04-understand-results.md)
5. [応用](docs/05-applications.md) — 天体観測、時空間モデリング
6. [片付け](docs/06-cleanup.md)
7. [倫理と限界](docs/07-ethics-and-limits.md)

トラブル対応: [troubleshooting.md](troubleshooting.md)

## ライセンス

- scikit-learn: BSD-3-Clause
- コード: リポジトリのライセンス

## 免責

**GP の信頼区間は kernel が正しく系を表現できていることを前提とする**。周期性を持たないデータに ExpSineSquared kernel を当てはめると、意味のない信頼区間が出力されます。kernel 選定は必ずドメイン知識に基づいてください。
