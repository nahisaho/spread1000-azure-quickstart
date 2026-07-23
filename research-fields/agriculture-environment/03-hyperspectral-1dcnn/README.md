# 03 — ハイパースペクトル画像分類 (1D-CNN)

**分野**: リモートセンシング、精密農業、地質探査、環境モニタリング  
**手法**: 1 ピクセルの 200 バンドスペクトルを 1D-CNN で分類  
**データ**: 合成 Indian Pines 相当 (6 農作物クラス × 200 バンド × 1200 ピクセル)  
**時間**: ~2 分 (CPU)

## なぜ合成データか

- 実 Indian Pines (`.mat`) URL が不安定 (ehu.eus, 大学サーバー)
- 授業/研修で「まず動かす」ことを優先
- 各クラスに現実的なスペクトル形状 (植生の red edge, NIR プラトー等を模した Gaussian ピーク) を与えているため、**手法学習には十分**
- 実データへの切り替えは `src/dataset.py` を差し替えるだけ (docs/05 参照)

## 使い方

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python src/train.py --epochs 15 --n-per-class 200
```

## 出力

- `outputs/best_model.pt`
- `outputs/loss_acc.png` — train/val loss + val_acc
- `outputs/confusion_matrix.png` — 6×6 クラス別混同行列
- `outputs/sample_spectra.png` — 各クラスの代表スペクトル
- `outputs/metrics.json` — precision/recall/F1 per class

## 期待精度

15 epoch × 200 samples/class で **test acc ≥ 0.95**、合成データでは 200 バンドが十分な情報量なので容易に高精度になります (実データ Indian Pines では 0.80-0.90 が典型)。

## ドキュメント

- [01 前提条件](docs/01-prerequisites.md)
- [02 モデル設計](docs/02-model.md)
- [03 学習](docs/03-train.md)
- [04 結果の解釈](docs/04-understand-results.md)
- [05 自前データ (実 Indian Pines 差し替え)](docs/05-your-data.md)
- [06 片付け](docs/06-cleanup.md)
- [07 倫理と限界](docs/07-ethics-and-limits.md)
- [トラブルシューティング](troubleshooting.md)
