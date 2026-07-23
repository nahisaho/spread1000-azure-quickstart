"""
合成クリーン画像 + Gaussian ノイズによる (clean, noisy) ペア生成.

- ライセンス制約なし (すべて手続き的生成)
- 各サンプル: 128x128, 1 channel, float32 in [0, 1]
- 幾何プリミティブ (矩形、円、グラデーション、直線) をランダム配置
- ガウシアン平滑化で自然なエッジに → 加算 Gaussian ノイズ σ=0.10

保存形式: data/{split}/{idx:04d}.npz  {"clean": (1,H,W), "noisy": (1,H,W)}
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def _draw_rectangle(img: np.ndarray, rng: np.random.Generator) -> None:
    h, w = img.shape
    y0, x0 = rng.integers(0, h - 30, size=2)
    y1 = min(h, y0 + rng.integers(15, 60))
    x1 = min(w, x0 + rng.integers(15, 60))
    intensity = rng.uniform(0.25, 1.0)
    img[y0:y1, x0:x1] = intensity


def _draw_circle(img: np.ndarray, rng: np.random.Generator) -> None:
    from skimage.draw import disk

    h, w = img.shape
    r = int(rng.integers(6, 22))
    cy = int(rng.integers(r, h - r))
    cx = int(rng.integers(r, w - r))
    rr, cc = disk((cy, cx), r, shape=img.shape)
    img[rr, cc] = rng.uniform(0.25, 1.0)


def _draw_line(img: np.ndarray, rng: np.random.Generator) -> None:
    from skimage.draw import line_aa

    h, w = img.shape
    y0, x0, y1, x1 = rng.integers(0, min(h, w), size=4)
    rr, cc, val = line_aa(int(y0), int(x0), int(y1), int(x1))
    intensity = rng.uniform(0.4, 1.0)
    img[rr, cc] = np.maximum(img[rr, cc], val * intensity)


def _add_gradient(img: np.ndarray, rng: np.random.Generator) -> None:
    h, w = img.shape
    axis = rng.integers(0, 2)
    strength = rng.uniform(0.05, 0.20)
    ramp = np.linspace(0, strength, w if axis == 1 else h, dtype=np.float32)
    if axis == 1:
        img += ramp[None, :]
    else:
        img += ramp[:, None]


def make_clean_sample(size: int = 128, rng: np.random.Generator | None = None) -> np.ndarray:
    """(1, size, size) float32 in [0, 1]."""
    from scipy.ndimage import gaussian_filter

    if rng is None:
        rng = np.random.default_rng()
    img = np.zeros((size, size), dtype=np.float32)

    _add_gradient(img, rng)
    n_prims = int(rng.integers(4, 10))
    for _ in range(n_prims):
        kind = rng.integers(0, 3)
        if kind == 0:
            _draw_rectangle(img, rng)
        elif kind == 1:
            _draw_circle(img, rng)
        else:
            _draw_line(img, rng)

    # 軽い Gaussian smoothing でエッジをやや自然に (実撮影の LSF に近づける)
    sigma = float(rng.uniform(0.5, 1.2))
    img = gaussian_filter(img, sigma=sigma)

    img = np.clip(img, 0.0, 1.0).astype(np.float32)
    return img[None]  # (1, H, W)


def add_gaussian_noise(
    img: np.ndarray, sigma: float, rng: np.random.Generator
) -> np.ndarray:
    noise = rng.normal(0.0, sigma, size=img.shape).astype(np.float32)
    noisy = np.clip(img + noise, 0.0, 1.0).astype(np.float32)
    return noisy


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--n-train", type=int, default=200)
    p.add_argument("--n-val", type=int, default=40)
    p.add_argument("--size", type=int, default=128)
    p.add_argument("--noise-sigma", type=float, default=0.10)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def _write_split(
    split_dir: Path,
    n: int,
    size: int,
    noise_sigma: float,
    rng: np.random.Generator,
) -> None:
    split_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        clean = make_clean_sample(size=size, rng=rng)
        noisy = add_gaussian_noise(clean, noise_sigma, rng)
        np.savez(split_dir / f"{i:04d}.npz", clean=clean, noisy=noisy)
    print(f"[gen] {split_dir}: {n} samples ({size}x{size}, sigma={noise_sigma})")


def main() -> None:
    args = parse_args()
    root = args.output_dir or (Path(__file__).resolve().parents[1] / "data")
    rng = np.random.default_rng(args.seed)

    _write_split(root / "train", args.n_train, args.size, args.noise_sigma, rng)
    _write_split(root / "val", args.n_val, args.size, args.noise_sigma, rng)

    # 可視化用サンプルを 4 枚保存 (matplotlib は評価時のみ import)
    samples_dir = root / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(4, 2, figsize=(6, 12))
    preview_rng = np.random.default_rng(args.seed + 1)
    for i in range(4):
        clean = make_clean_sample(size=args.size, rng=preview_rng)
        noisy = add_gaussian_noise(clean, args.noise_sigma, preview_rng)
        axes[i, 0].imshow(clean[0], cmap="gray", vmin=0, vmax=1)
        axes[i, 0].set_title("clean")
        axes[i, 0].axis("off")
        axes[i, 1].imshow(noisy[0], cmap="gray", vmin=0, vmax=1)
        axes[i, 1].set_title(f"noisy (sigma={args.noise_sigma})")
        axes[i, 1].axis("off")
    plt.tight_layout()
    plt.savefig(samples_dir / "preview.png", dpi=100)
    plt.close()
    print(f"[gen] preview → {samples_dir / 'preview.png'}")


if __name__ == "__main__":
    main()
