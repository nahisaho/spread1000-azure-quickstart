"""Synthetic microscopy image generators (Voronoi grains, particle circles).

Generates 1-channel float32 images and their binary segmentation masks entirely
in-code — no third-party image data required.

Usage (visualize a few samples):
    python src/generate_data.py --task grains --n 4 --output data/samples/
    python src/generate_data.py --task particles --n 4 --output data/samples/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


def make_grain_sample(
    size: int = 128,
    n_grains: int = 20,
    noise_std: float = 0.05,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Voronoi polycrystalline SEM-like image + binary grain-boundary mask.

    Uses periodic-tiled seed points so boundaries reach the image edge.

    Returns
    -------
    img : (1, size, size) float32 in [0, 1]
    mask : (1, size, size) float32 in {0.0, 1.0}
    """
    from scipy.spatial import cKDTree
    from skimage.segmentation import find_boundaries

    if rng is None:
        rng = np.random.default_rng()

    # Sample seed points, then tile to 3x3. Nearest-seed labeling over the
    # tiled set is exactly the periodic (torus) Voronoi diagram — every
    # pixel gets a label, so there is no fallback / edge distortion.
    pts = rng.uniform(0, size, (n_grains, 2))
    offsets = np.array([[dx * size, dy * size]
                        for dx in (-1, 0, 1) for dy in (-1, 0, 1)])
    tiled = np.vstack([pts + off for off in offsets])  # (9*n_grains, 2) as (x, y)

    # Query nearest tiled seed for every pixel, then fold back to grain id.
    ys, xs = np.mgrid[0:size, 0:size]
    pixel_pts = np.stack([xs.ravel(), ys.ravel()], axis=1)  # (H*W, 2) as (x, y)
    _, nearest = cKDTree(tiled).query(pixel_pts, k=1)
    label_img = (nearest % n_grains).reshape(size, size).astype(np.int32) + 1

    grayscales = rng.uniform(0.15, 0.9, n_grains).astype(np.float32)
    intensity_img = grayscales[label_img - 1]

    # Gaussian noise to mimic SEM detector noise
    img = intensity_img + rng.normal(0.0, noise_std, intensity_img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)

    # Binary grain-boundary mask
    mask = find_boundaries(label_img, mode="outer").astype(np.float32)

    return img[np.newaxis], mask[np.newaxis]


def make_particle_sample(
    size: int = 128,
    n_particles: int = 15,
    noise_std: float = 0.05,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Random bright circles on a noisy dark background + binary particle mask.

    Returns
    -------
    img : (1, size, size) float32 in [0, 1]
    mask : (1, size, size) float32 in {0.0, 1.0}
    """
    from skimage.draw import disk

    if rng is None:
        rng = np.random.default_rng()

    img = rng.normal(0.20, 0.05, (size, size)).astype(np.float32)
    mask = np.zeros((size, size), dtype=np.float32)

    for _ in range(n_particles):
        r = int(rng.integers(10, size - 10))
        c = int(rng.integers(10, size - 10))
        radius = int(rng.integers(4, 12))
        rr, cc = disk((r, c), radius, shape=(size, size))
        img[rr, cc] = float(rng.uniform(0.6, 1.0))
        mask[rr, cc] = 1.0

    img += rng.normal(0.0, noise_std, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return img[np.newaxis], mask[np.newaxis]


def generate_batch(
    task: str,
    n: int,
    size: int,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate n samples for the given task.

    Returns
    -------
    imgs  : (n, 1, size, size) float32
    masks : (n, 1, size, size) float32
    """
    rng = np.random.default_rng(seed)
    imgs = np.zeros((n, 1, size, size), dtype=np.float32)
    masks = np.zeros((n, 1, size, size), dtype=np.float32)
    if task == "grains":
        for i in range(n):
            img, m = make_grain_sample(size=size, rng=rng)
            imgs[i] = img
            masks[i] = m
    elif task == "particles":
        for i in range(n):
            img, m = make_particle_sample(size=size, rng=rng)
            imgs[i] = img
            masks[i] = m
    else:
        raise ValueError(f"unknown task: {task!r}. Use 'grains' or 'particles'.")
    return imgs, masks


def _save_preview(img: np.ndarray, mask: np.ndarray, path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(6, 3))
    axes[0].imshow(img[0], cmap="gray", vmin=0, vmax=1); axes[0].set_title("image")
    axes[1].imshow(mask[0], cmap="gray", vmin=0, vmax=1); axes[1].set_title("mask")
    for ax in axes:
        ax.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=120)
    plt.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--task", default="grains", choices=["grains", "particles"])
    p.add_argument("--n", type=int, default=4, help="Number of preview samples")
    p.add_argument("--size", type=int, default=128)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--output", type=Path, default=Path("data/samples"))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    imgs, masks = generate_batch(args.task, args.n, args.size, args.seed)
    for i in range(args.n):
        out = args.output / f"{args.task}_{i:02d}.png"
        _save_preview(imgs[i], masks[i], out)
        print(f"[gen] wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
