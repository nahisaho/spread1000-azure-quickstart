# 05 — 結果の読み方

## 出力ファイル

学習完了後 `data/` 以下に:
```
data/
├── metrics.json                       # 学習全体のサマリ
├── checkpoints/
│   └── best_model.pth                 # ベスト IoU のエポックの重み
└── predictions/
    ├── montage_epoch010.png           # 検証画像 × [入力 | 正解 | 予測]
    └── per_image_metrics.json         # 検証画像ごとの IoU/Dice
```

## metrics.json の中身

```json
{
  "config": {"task": "grains", "image_size": 128, "epochs": 10, ...},
  "positive_pixel_fraction_train": 0.1217,
  "n_parameters": 117073,
  "train_loss": [0.72, 0.51, 0.40, 0.33, 0.28, 0.25, 0.23, 0.22, 0.21, 0.20],
  "val_loss":   [0.65, 0.49, 0.38, 0.32, 0.28, 0.26, 0.24, 0.23, 0.22, 0.22],
  "val_iou":    [0.28, 0.42, 0.51, 0.57, 0.60, 0.62, 0.64, 0.66, 0.67, 0.68],
  "val_dice":   [0.44, 0.59, 0.68, 0.73, 0.75, 0.77, 0.78, 0.80, 0.81, 0.81],
  "best_epoch": 10,
  "best_val_iou": 0.6864,
  "best_val_dice": 0.8130
}
```

## 指標の意味

### IoU (Intersection over Union = Jaccard index)
`|A ∩ B| / |A ∪ B|`。0（全く合わない）〜 1（完全一致）。
セグメンテーションで最もよく使う指標。

### Dice = F1 スコア (二値)
`2|A ∩ B| / (|A| + |B|)`。0〜1。IoU より少し甘め (`Dice = 2·IoU / (1 + IoU)`)。

### 本クイックスタートで期待される値

| タスク | 期待 IoU | 期待 Dice | 理由 |
|---|---:|---:|---|
| `grains` (粒界) | 0.55〜0.75 | 0.70〜0.85 | 境界が 1〜2 ピクセル幅、1 ピクセルずれるだけで False Negative になる |
| `particles` (円粒子) | 0.75〜0.90 | 0.85〜0.95 | 塊状オブジェクトは境界より学習しやすい |

> ⚠️ 粒界タスクで IoU 0.5 は「悪い」のではなく **境界検出タスクとして妥当な値** です。IoU 0.9 を目指すと過学習を疑ってください（合成データなので過学習は容易に起きます）。

## モンタージュの読み方

`data/predictions/montage_epoch010.png` は 6 行 × 3 列:

| 列 | 内容 |
|---|---|
| Input | 検証画像 (グレースケール、ノイズ入り) |
| Ground Truth | 真の境界 or 粒子マスク (白 = 陽性) |
| Prediction | シグモイド閾値 0.5 の予測 |

**良い予測の兆候**:
- 予測境界が真の境界と重なる
- 誤検出 (false positive) が少ない
- 途切れた境界がつながっている

**悪い予測の兆候**:
- 全画面白 → `pos_weight` が高すぎ、または学習不足
- 全画面黒 → `pos_weight` が低すぎ、または損失計算のバグ
- 境界が斑点状 → 学習不足、`--epochs` を増やす

## 検証画像ごとの分析

```python
import json
rows = json.load(open("data/predictions/per_image_metrics.json"))

# ワースト 5 と ベスト 5
rows.sort(key=lambda r: r["iou"])
print("== worst 5 ==")
for r in rows[:5]:  print(r)
print("== best 5 ==")
for r in rows[-5:]: print(r)

# 統計
import statistics
ious = [r["iou"] for r in rows]
print(f"IoU: mean={statistics.mean(ious):.3f}, "
      f"median={statistics.median(ious):.3f}, "
      f"min={min(ious):.3f}, max={max(ious):.3f}")
```

**ワースト画像を可視化してデバッグ**:
```python
import torch, matplotlib.pyplot as plt
from model import MiniUNet
from generate_data import generate_batch

# 検証データを再生成 (--seed と同じシード + 10000 で再現可能)
imgs, masks = generate_batch("grains", 50, 128, seed=42 + 10000)
model = MiniUNet(); model.load_state_dict(torch.load("data/checkpoints/best_model.pth", map_location="cpu"))
model.eval()

worst_idx = rows[0]["index"]
with torch.no_grad():
    pred = torch.sigmoid(model(torch.from_numpy(imgs[worst_idx:worst_idx+1]).float()))
# ...matplotlib で可視化
```

## 学習曲線の異常検知

| パターン | 原因 |
|---|---|
| train_loss は下がるが val_loss が上がる | 過学習 (合成データ多様性不足)、`--n-train` を増やす |
| train/val 両方が停滞 | 学習率過小 or モデル容量不足、`--lr 5e-3` or `base=32` に |
| val_loss が振動する | batch_size が小さすぎ、`--batch-size 16` に |
| 1〜2 epoch で val_iou が飽和 | データが簡単すぎ、`--n-grains 30` を試す |

## 論文・レポートで報告する内容

論文に載せるなら以下を明記:
1. 使用した合成データ生成手法 (Voronoi + Gaussian noise σ=0.05)
2. モデル (MiniUNet 3-level, 117K params)
3. 学習ハイパーパラメータ (Adam lr=1e-3, BCE pos_weight=9.0, batch=8, 10 epochs)
4. データ分割 (200 train / 50 val, seed=42 / seed=10042)
5. 最終指標 (IoU mean/std, Dice mean/std over 50 val images)
6. 使用ライブラリのバージョン (PyTorch 2.7.1, torchmetrics x.x.x, scikit-image x.x.x)
