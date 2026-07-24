# 03 — ハイパースペクトル画像分類 (1D-CNN)

**分野**: リモートセンシング、精密農業、地質探査、環境モニタリング  
**手法**: 1 ピクセルの B バンドスペクトルを 1D-CNN で分類  
**データ**: 合成 6-class toy データ (デフォルト) / 実 Indian Pines 16-class (オプション)  
**時間**: ~2 分 (CPU, synthetic)

## モデル概要

```
Input (B, 1, n_bands)
Conv1d(1→16,k7)→BN→ReLU→MaxPool → (B,16,n_bands/2)
Conv1d(16→32,k5)→BN→ReLU→MaxPool → (B,32,n_bands/4)
Conv1d(32→64,k3)→BN→ReLU→GAP    → (B,64)
Linear(64→n_classes)
```

パラメータ数 (synthetic 6-class / 200-band): **9,542**  
※ `BatchNorm` は特徴チャネルの最適化安定化用; 入力バンドの正規化は `--norm-method` が担当

## なぜ合成データか

- 実 Indian Pines `.mat` のミラー URL が不安定なため、オフライン学習体験用に合成 toy データを用意
- 合成スペクトルは Gaussian ピークで簡略化しており、**実センサー特性を再現していない**
- 手法学習には十分だが、**合成データでの高精度は実データの性能を保証しない**
- 実データへの切り替えは `--mode indianpines` または `--mode custom`

## セットアップ

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/03-hyperspectral-1dcnn"
cd "$SCENARIO_DIR"
test -f src/train.py || { echo "abort: wrong directory"; exit 1; }

python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

## 合成データで学習 (オフライン)

```bash
python src/train.py --mode synthetic --epochs 15 --n-per-class 200
```

## 実 Indian Pines で学習 (要初回インターネット)

```bash
python src/train.py --mode indianpines \
    --split-strategy disjoint_patch \
    --balance weighted_ce \
    --epochs 30
```

> ⚠ Indian Pines データを使用・発表する場合は Landgrebe (2003) を引用すること。
> ライセンスは未文書化; 非研究用途は Purdue 大学に確認。

## スモークテスト

```bash
python -m pytest tests/test_smoke.py -v -m slow
```

## 出力

- `outputs/best_model.pt` — チェックポイント (正規化 stats, class_names 含む)
- `outputs/loss_acc.png`
- `outputs/confusion_matrix.png` + `outputs/confusion_matrix.csv`
- `outputs/sample_spectra.png`
- `outputs/prediction_map.png` — 実データのみ
- `outputs/metrics.json` — 全メトリクス (macro_F1, balanced_acc, kappa, git SHA, etc.)

## 期待精度

| データ | split | 参考精度 |
|---|---|---|
| 合成 6-class (toy) | random_pixel | acc ≥ 0.95 — ⚠ 実データ性能を示さない |
| Indian Pines (16 class) | disjoint_patch | acc ≈ 0.75–0.85 |
| Indian Pines (16 class) | random_pixel | acc ≈ 0.85–0.90 — ⚠ 空間リーク |

## ドキュメント

- [01 前提条件](docs/01-prerequisites.md)
- [02 モデル設計](docs/02-model.md)
- [03 学習](docs/03-train.md)
- [04 結果の解釈](docs/04-understand-results.md)
- [05 自前データ (実 Indian Pines / カスタム)](docs/05-your-data.md)
- [06 片付け](docs/06-cleanup.md)
- [07 倫理と限界](docs/07-ethics-and-limits.md)
- [トラブルシューティング](troubleshooting.md)

## ライセンス

本シナリオのコードは MIT ライセンス (リポジトリルート LICENSE 参照)。  
Indian Pines データは NASA/JPL AVIRIS データ由来。引用・利用条件は 07 参照。
