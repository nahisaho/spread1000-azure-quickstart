# 03 — 振動信号異常検知 (1D Conv Autoencoder)

**対象**: 予知保全・状態監視・構造ヘルスモニタリングを AI で始めたい研究者
**目標**: 合成振動波形 (正常＝ベアリング健全時) を **1D Convolutional Autoencoder** で学習し、**再構成誤差の閾値** で異常 (欠陥) を検出する教師なし異常検知パイプラインを ノート PC で ≤ 5 分で体験
**手法**: 1D Conv AE (~50K params) + 再構成 MSE + 検証セットの 99 分位で閾値決定 → テストセットで ROC-AUC 評価

> [!NOTE]
> 完全にローカル CPU 完結。データは実行時に合成生成 (正常＝正弦波 + ノイズ、異常＝インパルス欠陥挿入)。

## 全体像

```
src/generate_data.py     # 正常 800 + 異常 200 の振動波形 (2048 サンプル/window) を生成

src/train.py             # AE を正常データのみで学習 (異常は使わない, unsupervised)
   ├→ 1D Conv Encoder (2048 → 512 → 128 → 32 latent)
   ├→ 1D Conv Decoder (32 → 128 → 512 → 2048)
   ├→ MSE loss + Adam
   └→ 検証セットの再構成 MSE の 99 分位 = 閾値

src/evaluate.py          # テストセット (正常 + 異常混合) で ROC-AUC, F1
                         # 混同行列 PNG + threshold-vs-metrics カーブ PNG
```

## クイックスタート

```bash
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt

python src/generate_data.py --out data/vibration.npz --seed 42
python src/train.py --data data/vibration.npz --epochs 30 --device cpu
python src/evaluate.py --data data/vibration.npz --model outputs/best_ae.pt
```

## データ設計

- **正常** (label=0): 800 サンプル
  - 基底波形: `sin(2π f₁ t) + 0.5 sin(2π f₂ t)` (f₁ ∈ [30, 60] Hz, f₂ ∈ [90, 180] Hz, ランダム)
  - Gaussian ノイズ σ=0.05
- **異常** (label=1): 200 サンプル
  - 正常波形 + **周期的インパルス欠陥** (ベアリング欠陥模擬): 期間 100〜300 サンプルごとに振幅 1.0 の短パルス

**分割** (再現性のため fixed seed):
- Train: 正常のみ 640 (AE 学習用、異常は含めない = 教師なし)
- Val:   正常のみ 160 (閾値決定用)
- Test:  正常 200 + 異常 200 (評価用)

## スタック

| 種別 | 選定 | 理由 |
|---|---|---|
| モデル | 1D Conv AE (~50K params) | 波形の局所パターンを畳み込みで捉える |
| 損失 | MSE (再構成誤差) | 教師なし異常検知の定番 |
| 閾値 | 検証セットの 99 分位 | 誤検出率 1% を目標 |
| 評価 | ROC-AUC, F1, precision, recall | クラス不均衡下でも意味のある指標 |

## ドキュメント

1. [前提条件](docs/01-prerequisites.md)
2. [データ生成](docs/02-generate-data.md) — 波形の合成レシピ、視覚化
3. [学習](docs/03-train.md) — CLI、AE の構造、閾値決定
4. [結果の読み方](docs/04-understand-results.md) — ROC-AUC、混同行列、閾値
5. [実データへの応用](docs/05-real-data.md) — CWRU/PHM データセットへの拡張
6. [片付け](docs/06-cleanup.md)
7. [倫理と限界](docs/07-ethics-and-limits.md) — 誤検出コスト、false negative の意味

トラブル対応: [troubleshooting.md](troubleshooting.md)

## ライセンス

- コード: リポジトリのライセンスに従う
- データ: 完全合成、制約なし

## 免責

**本教材のデータは合成波形であり、実際の産業機器 (ベアリング、モーター、ギア) の欠陥スペクトルとは異なります。実データへの適用時は以下を必ず検証してください:**
- ドメイン特有の物理 (回転数、サンプリング周波数、機器固有共振周波数) の考慮
- 再構成誤差の空間的偏り (時間帯ごとの分布)
- 少数の誤検出でもコスト大な用途 (安全機器) では precision > 0.99 の要件を再学習で満たすまで運用しない
