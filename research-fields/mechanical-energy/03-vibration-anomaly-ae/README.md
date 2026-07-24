# 03 — 振動信号異常検知 (1D Conv Autoencoder)

**対象**: 予知保全・状態監視・構造ヘルスモニタリングを AI で始めたい研究者
**目標**: 合成振動波形 (正常＝ベアリング健全時) を **1D Convolutional Autoencoder** で学習し、**再構成誤差の閾値** で異常 (欠陥) を検出する教師なし異常検知パイプラインを ノート PC で ≤ 5 分で体験
**手法**: 1D Conv AE (1,083,105 params) + 再構成 MSE + キャリブレーションセットの 99 分位で閾値決定 → テストセットで ROC-AUC 評価

> [!NOTE]
> 完全にローカル CPU 完結。データは実行時に合成生成 (正常＝正弦波 + ノイズ、異常＝インパルス欠陥挿入)。

## 全体像

```
src/generate_data.py     # 正常 1000 + 異常 200 の振動波形 (2048 サンプル/window) を生成

src/train.py             # AE を正常データのみで学習 (異常は使わない, unsupervised)
   ├→ 1D Conv Encoder (2048 → 1024 → 512 → 256 → 32 latent)
   ├→ 1D Conv Decoder (32 → 256 → 512 → 1024 → 2048)
   ├→ MSE loss + Adam
   └→ キャリブレーションセット (X_cal) の再構成 MSE の 99 分位 = 閾値
      ※ 閾値はキャリブレーションセットで 1 回だけ選ぶ。テストセットは使わない。

src/evaluate.py          # テストセット (正常 + 異常混合) で ROC-AUC, F1
                         # 混同行列 PNG + threshold-vs-metrics カーブ PNG
```

## クイックスタート

```bash
cd research-fields/mechanical-energy/03-vibration-anomaly-ae

# torch CPU wheel を先にインストール
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu

# その他の依存 (ハッシュなし簡易版)
python -m pip install -r requirements.txt
# ハッシュ検証付きインストール (推奨): requirements-lock/README.md を参照

python src/generate_data.py --out data/vibration.npz --seed 42
python src/train.py --data data/vibration.npz --epochs 30 --seed 42 --device cpu
python src/evaluate.py --data data/vibration.npz --model outputs/best_ae.pt
```

## 回帰テスト

```bash
cd research-fields/mechanical-energy/03-vibration-anomaly-ae
python -m pytest tests/test_regression.py -v
```

seed=42 で ROC-AUC ≥ 0.95、F1 ≥ 0.85 を自動検証します (所要時間 ≈ 2 分)。

## データ設計

- **正常** (label=0): 1000 サンプル
  - 基底波形: `sin(2π f₁ t) + 0.5 sin(2π f₂ t)` (f₁ ∈ [30, 60] Hz, f₂ ∈ [90, 180] Hz, ランダム)
  - Gaussian ノイズ σ=0.05
- **異常** (label=1): 200 サンプル
  - 正常波形 + **周期的インパルス欠陥** (ベアリング欠陥模擬): 期間 100〜300 サンプルごとに振幅 3〜6 の短パルス

**分割** (再現性のため fixed seed):
| セット | 内訳 | 用途 |
|---|---|---|
| Train   | 正常 640    | AE 学習 (異常は含めない = 教師なし) |
| Val-ES  | 正常 32     | 早期終了検証のみ (閾値決定には使わない) |
| Cal     | 正常 128    | 閾値キャリブレーション (テストとは独立) |
| Test    | 正常 200 + 異常 200 | 最終評価に 1 回だけ使用 |

## スタック

| 種別 | 選定 | 理由 |
|---|---|---|
| モデル | 1D Conv AE (1,083,105 params) | 波形の局所パターンを畳み込みで捉える |
| 損失 | MSE (再構成誤差) | 教師なし異常検知の定番 |
| 閾値 | キャリブレーションセットの 99 分位 | テスト汚染を防ぐ |
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

> [!WARNING]
> **本モデルは安全認証されておらず、単独で停止・保全判断の根拠にしてはなりません。**

**本教材のデータは合成波形であり、実際の産業機器 (ベアリング、モーター、ギア) の欠陥スペクトルとは異なります。実データへの適用時は以下を必ず検証してください:**

- ドメイン特有の物理 (回転数、サンプリング周波数、機器固有共振周波数) の考慮
- 再構成誤差の空間的偏り (時間帯ごとの分布)
- **代表的な recall / sensitivity の実測値と false-negative の許容上限の確認**
- **発生率 (prevalence) 補正後の precision の評価** (稀な欠陥では precision は見かけ上高くなりやすい)
- **フェイルセーフ制御との組み合わせ** — AI 判定は補助情報であり、機械的なフェイルセーフを置き換えない
- **人間 + ドメインエキスパートによるレビュー** を必ず挟む
