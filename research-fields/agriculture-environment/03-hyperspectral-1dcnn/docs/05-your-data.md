# 05 — 自前データへの適用

## 実 Indian Pines への差し替え

### データ入手

```bash
# 145×145 pixels × 200 bands
wget https://www.ehu.eus/ccwintco/uploads/6/67/Indian_pines_corrected.mat -O data/indian_pines.mat
wget https://www.ehu.eus/ccwintco/uploads/c/c4/Indian_pines_gt.mat -O data/indian_pines_gt.mat
```

### `src/dataset.py` の差し替え

```python
import scipy.io as sio
import numpy as np

def load_indian_pines(data_dir="data"):
    cube = sio.loadmat(f"{data_dir}/indian_pines.mat")["indian_pines_corrected"]  # (145,145,200)
    gt = sio.loadmat(f"{data_dir}/indian_pines_gt.mat")["indian_pines_gt"]        # (145,145)
    # ピクセル単位に flatten、背景クラス 0 を除外
    mask = gt > 0
    X = cube[mask].astype(np.float32)   # (N, 200)
    y = gt[mask].astype(np.int64) - 1   # (N,) 0-indexed
    # 反射率正規化 (per-band z-score)
    X = (X - X.mean(0, keepdims=True)) / (X.std(0, keepdims=True) + 1e-8)
    return X, y
```

要件: `pip install scipy`

## 他のハイパースペクトル公開データ

| データセット | サイズ | クラス数 | ドメイン |
|---|---|---|---|
| Indian Pines | 145×145×200 | 16 | 農地 (米中西部) |
| Salinas | 512×217×204 | 16 | 農地 (加州) |
| Pavia University | 610×340×103 | 9 | 都市 |
| Houston 2013 | 349×1905×144 | 15 | 都市+植生 |
| KSC (Kennedy Space Center) | 512×614×176 | 13 | 湿地植生 |

## 精度向上のコツ

- **チャネル正規化必須** (per-band z-score または min-max)
- Indian Pines 等では **クラス不均衡が大きい** (Soybean 数千, Oats 20) → `WeightedRandomSampler`
- **PCA で 200 → 30 バンドに削減**してから 1D-CNN に入れる方法もある
- 空間コンテキストが必要なら 2D-CNN で 5×5 patch を入力に

## 応用例

- 精密農業: 圃場のドローン HSI → 品種/生育ステージ/病害マッピング
- 環境: 湿地/森林の分類、河川 chl-a 推定
- 地質: 鉱物分類、地表被覆分類
