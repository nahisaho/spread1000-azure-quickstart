# data/ ディレクトリ

このディレクトリは実行時に自動生成されるファイルの置き場所です。**リポジトリには何も含めていません**（`.gitignore` 済み）。

## 生成されるファイル

| ファイル | 生成元 | 内容 |
|---|---|---|
| `metrics.json` | `src/train.py` | train/val loss + IoU/Dice/F1 の履歴 |
| `checkpoints/best_model.pth` | `src/train.py` | 検証 IoU が最高だったエポックの重み |
| `predictions/montage_epoch{N:03d}.png` | `src/train.py` | 入力 \| 正解 \| 予測 のモンタージュ |
| `predictions/per_image_metrics.json` | `src/train.py` | 検証画像ごとの IoU/Dice |
| `samples/*.png` | `src/generate_data.py` | データ確認用の可視化 (任意) |

## 可視化

```bash
# モンタージュを表示
xdg-open data/predictions/montage_epoch010.png  # Linux
open data/predictions/montage_epoch010.png       # macOS
```

Python で学習曲線をプロット:
```python
import json, matplotlib.pyplot as plt
m = json.load(open("data/metrics.json"))
plt.plot(m["train_loss"], label="train"); plt.plot(m["val_loss"], label="val")
plt.xlabel("epoch"); plt.ylabel("loss"); plt.legend(); plt.tight_layout()
plt.savefig("data/loss_curve.png", dpi=120)
```

## クリーンアップ

```bash
rm -rf data/*.png data/samples data/predictions data/checkpoints data/*.json
```
