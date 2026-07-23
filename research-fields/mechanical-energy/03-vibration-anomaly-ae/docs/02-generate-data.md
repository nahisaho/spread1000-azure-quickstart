# 02 — データ生成

## 実行

```bash
python src/generate_data.py --out data/vibration.npz --seed 42
```

## 生成データ

- サンプリング周波数 fs = 5000 Hz
- 1 窓 = 2048 サンプル ≈ 410 ms
- 正常 1000 + 異常 200 波形

## 正常波形

$$x(t) = \sin(2\pi f_1 t + \phi_1) + 0.5 \sin(2\pi f_2 t + \phi_2) + \epsilon(t)$$

- $f_1 \in [30, 60]$ Hz, $f_2 \in [90, 180]$ Hz (窓ごとにランダム)
- $\epsilon \sim \mathcal{N}(0, 0.05)$
- 位相 $\phi_1, \phi_2$ もランダム

## 異常波形 (ベアリング欠陥模擬)

正常波形 + **周期的インパルス列**:
- 周期 100〜300 サンプル (欠陥周波数 16.7〜50 Hz)
- 振幅 0.8〜1.5、幅 3 サンプル、`[0.5, 1.0, 0.5]` の短パルス
- 実機の局所欠陥 (ベアリング外輪剥離等) が発生させる BPFO (Ball Pass Frequency Outer race) 類似の波形

## 分割 (再現性のため seed=42 で固定)

| セット | 内訳 | 用途 |
|---|---|---|
| Train | 正常 640 | AE 学習 (異常なし = 教師なし) |
| Val   | 正常 160 | 閾値決定 (99 分位) |
| Test  | 正常 200 + 異常 200 | ROC-AUC / F1 評価 |

## 可視化 (option)

```python
import numpy as np, matplotlib.pyplot as plt
d = np.load("data/vibration.npz")
fig, ax = plt.subplots(2, 1, figsize=(10, 4))
ax[0].plot(d["X_train"][0]); ax[0].set_title("normal")
# X_test の中で y_test==1 の最初のサンプル
anom_idx = np.where(d["y_test"] == 1)[0][0]
ax[1].plot(d["X_test"][anom_idx]); ax[1].set_title("anomaly (impulse defects)")
plt.tight_layout(); plt.savefig("data/preview.png", dpi=100)
```
