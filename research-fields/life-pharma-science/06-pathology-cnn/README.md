# 06 — 病理組織画像分類 (MedMNIST PathMNIST)

**分野**: 病理診断、腫瘍学、細胞学、組織学  
**手法**: 軽量 CNN で大腸組織 9 クラス分類  
**データ**: MedMNIST PathMNIST (28×28 RGB × 107K サンプル、自動 DL ~205MB)  
**時間**: ~3 分 (CPU、10% サブサンプル + 3 epoch)

## 何が学べるか

- 病理画像 (Whole Slide Image のパッチ) の基本的な分類パイプライン
- MedMNIST の医用画像ベンチマークセットの使い方
- 9 クラス組織分類 (脂肪, 背景, デブリ, リンパ球, 粘液, 平滑筋, 正常粘膜, 癌関連間質, 大腸腺癌上皮)

## 使い方

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python src/train.py --epochs 8 --train-frac 0.5
```

## 出力

- `outputs/best_model.pt`
- `outputs/loss_acc.png`
- `outputs/confusion_matrix.png` — 9×9 組織クラス混同行列
- `outputs/metrics.json` — precision/recall/F1 per class

## 期待精度

| 設定 | test_acc |
|---|---|
| 3 epoch × 10% サブセット (~9K train) | ~0.73 (smoke) |
| 8 epoch × 50% サブセット | ~0.85 |
| 15 epoch × フル 90K train | ~0.90 (論文級) |

## 応用先

- 病理 WSI パッチ分類 (Camelyon16, TCGA)
- 細胞形態分類 (Cell Painting)
- 組織免疫染色画像分類 (IHC scoring)
- 内視鏡画像分類 (Kvasir)

## ドキュメント

- [01 前提条件](docs/01-prerequisites.md)
- [02 PathMNIST とタスク](docs/02-task.md)
- [03 学習](docs/03-train.md)
- [04 結果の解釈](docs/04-understand-results.md)
- [05 自前病理画像への適用](docs/05-your-data.md)
- [06 片付け](docs/06-cleanup.md)
- [07 倫理と限界](docs/07-ethics-and-limits.md)
- [トラブルシューティング](troubleshooting.md)
