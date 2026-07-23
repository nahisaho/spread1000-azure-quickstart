"""合成ハイパースペクトルデータ生成器

Indian Pines 相当 (200 バンド × 数千ピクセル × 6 農作物クラス) の合成データ。
実データ URL 不安定への保険 + オフライン学習体験用。

各クラスは異なる中心波長ピーク・幅・ベースライン反射率を持つガウシアン
スペクトル + ホワイトノイズで生成する。
"""
from __future__ import annotations
import numpy as np


CLASS_NAMES = [
    "corn",           # トウモロコシ
    "soybean",        # 大豆
    "wheat",          # 小麦
    "grass_pasture",  # 牧草
    "woods",          # 森林
    "bare_soil",      # 裸地
]


# 各クラスの典型的な反射スペクトル形状 (peaks: (center_band, width, amp))
_CLASS_PROFILES = {
    "corn":          [(40, 15, 0.35), (100, 25, 0.55), (150, 20, 0.30)],
    "soybean":       [(45, 20, 0.40), (110, 20, 0.50), (155, 25, 0.28)],
    "wheat":         [(35, 10, 0.30), (105, 30, 0.60), (160, 15, 0.35)],
    "grass_pasture": [(50, 25, 0.45), (115, 25, 0.55), (145, 20, 0.32)],
    "woods":         [(55, 30, 0.50), (120, 30, 0.60), (140, 15, 0.25)],
    "bare_soil":     [(80, 60, 0.45), (170, 40, 0.55)],
}
_CLASS_BASELINE = {
    "corn": 0.10, "soybean": 0.08, "wheat": 0.12,
    "grass_pasture": 0.09, "woods": 0.06, "bare_soil": 0.15,
}


def generate(n_per_class: int = 200, n_bands: int = 200,
             noise_std: float = 0.02, seed: int = 42
             ) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return X (N, n_bands) float32 reflectance in [0,1], y (N,) int, names."""
    rng = np.random.default_rng(seed)
    bands = np.arange(n_bands)
    X_all, y_all = [], []
    for cls_idx, name in enumerate(CLASS_NAMES):
        baseline = _CLASS_BASELINE[name]
        profile = _CLASS_PROFILES[name]
        # 各サンプルは class の平均スペクトルにピクセル差 + ノイズを付与
        for _ in range(n_per_class):
            spec = np.full(n_bands, baseline, dtype=np.float32)
            for center, width, amp in profile:
                # centre と amp をわずかにジッター (実世界のピクセル差を模倣)
                c = center + rng.normal(0, 2.0)
                a = amp * (1.0 + rng.normal(0, 0.05))
                spec += a * np.exp(-0.5 * ((bands - c) / width) ** 2)
            spec += rng.normal(0, noise_std, size=n_bands).astype(np.float32)
            spec = np.clip(spec, 0.0, 1.5)
            X_all.append(spec)
            y_all.append(cls_idx)
    X = np.asarray(X_all, dtype=np.float32)
    y = np.asarray(y_all, dtype=np.int64)
    # shuffle
    perm = rng.permutation(len(y))
    return X[perm], y[perm], CLASS_NAMES
