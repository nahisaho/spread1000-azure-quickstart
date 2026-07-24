"""Synthetic microscopy image generators (Voronoi grains, particle circles).

Generates 1-channel float32 images and their binary segmentation masks entirely
in-code — no third-party image data required.

Modes
-----
preview  (default): save PNG previews of a few samples.
splits           : generate train/val/test NPZ splits for the full pipeline.

Usage (preview):
    python src/generate_data.py --task grains --n 4 --output data/samples/

Usage (splits — idempotent with --overwrite):
    python src/generate_data.py --mode splits --task grains \
        --n-train 200 --n-val 50 --n-test 50 --output data/ \
        --size 128 --seed 42 --overwrite
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
from pathlib import Path

import numpy as np


# ── Argument validators ────────────────────────────────────────────────────


def _positive_int(value: str) -> int:
    try:
        v = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected integer, got {value!r}")
    if v <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer (got {v})")
    return v


# ── Image generators ───────────────────────────────────────────────────────


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
    img  : (1, size, size) float32 in [0, 1]
    mask : (1, size, size) float32 in {0.0, 1.0}
    """
    from scipy.spatial import cKDTree
    from skimage.segmentation import find_boundaries

    if rng is None:
        rng = np.random.default_rng()

    pts = rng.uniform(0, size, (n_grains, 2))
    offsets = np.array(
        [[dx * size, dy * size] for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    )
    tiled = np.vstack([pts + off for off in offsets])

    ys, xs = np.mgrid[0:size, 0:size]
    pixel_pts = np.stack([xs.ravel(), ys.ravel()], axis=1)
    _, nearest = cKDTree(tiled).query(pixel_pts, k=1)
    label_img = (nearest % n_grains).reshape(size, size).astype(np.int32) + 1

    grayscales = rng.uniform(0.15, 0.9, n_grains).astype(np.float32)
    intensity_img = grayscales[label_img - 1]

    img = intensity_img + rng.normal(0.0, noise_std, intensity_img.shape).astype(
        np.float32
    )
    img = np.clip(img, 0.0, 1.0)
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
    img  : (1, size, size) float32 in [0, 1]
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
            imgs[i], masks[i] = make_grain_sample(size=size, rng=rng)
    elif task == "particles":
        for i in range(n):
            imgs[i], masks[i] = make_particle_sample(size=size, rng=rng)
    else:
        raise ValueError(f"unknown task: {task!r}. Use 'grains' or 'particles'.")
    return imgs, masks


# ── Split generation ───────────────────────────────────────────────────────


def _sha256_of_array(arr: np.ndarray) -> str:
    return hashlib.sha256(arr.tobytes()).hexdigest()


def generate_splits_to_disk(
    task: str,
    n_train: int,
    n_val: int,
    n_test: int,
    size: int,
    output_dir: Path,
    seed: int = 42,
    overwrite: bool = False,
) -> dict:
    """Save train/val/test NPZ splits and a manifest.json.

    Each split uses a non-overlapping seed range so no source image appears
    in more than one split.  Files are written atomically: data is first
    written to a sibling temporary directory, then renamed into place.

    Returns the manifest dict.
    """
    splits = {
        "train": (n_train, seed),
        "val": (n_val, seed + 10_000),
        "test": (n_test, seed + 20_000),
    }

    # Guard: refuse if any split dir is non-empty without --overwrite
    for split_name in splits:
        split_dir = output_dir / split_name
        if split_dir.exists() and any(split_dir.iterdir()):
            if not overwrite:
                raise SystemExit(
                    f"ERROR: {split_dir} already exists and is non-empty. "
                    "Pass --overwrite to regenerate."
                )

    # Write atomically: generate into temp sibling, then os.replace
    tmp_root = output_dir / "_tmp_splits"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True)

    manifest_files: list[dict] = []

    for split_name, (n, split_seed) in splits.items():
        print(
            f"[gen] {split_name}: {n} samples, size={size}, seed={split_seed} ..."
        )
        imgs, masks = generate_batch(task, n, size, seed=split_seed)
        tmp_dir = tmp_root / split_name
        tmp_dir.mkdir()
        for i in range(n):
            fname = f"{task}_{i:04d}.npz"
            np.savez_compressed(
                tmp_dir / fname,
                image=imgs[i],
                label=masks[i],
            )
            manifest_files.append(
                {
                    "split": split_name,
                    "file": f"{split_name}/{fname}",
                    "sha256": _sha256_of_array(
                        np.concatenate([imgs[i].ravel(), masks[i].ravel()])
                    ),
                }
            )

    # Atomically replace existing split dirs
    for split_name in splits:
        target = output_dir / split_name
        src = tmp_root / split_name
        if target.exists():
            shutil.rmtree(target)
        os.replace(str(src), str(target))

    shutil.rmtree(tmp_root, ignore_errors=True)

    manifest = {
        "task": task,
        "size": size,
        "seed": seed,
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
        "total": n_train + n_val + n_test,
        "files": manifest_files,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)
    )
    print(
        f"[gen] wrote {n_train + n_val + n_test} files + {manifest_path}"
    )
    return manifest


# ── Preview helpers ────────────────────────────────────────────────────────


def _save_preview(img: np.ndarray, mask: np.ndarray, path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(6, 3))
    axes[0].imshow(img[0], cmap="gray", vmin=0, vmax=1)
    axes[0].set_title("image")
    axes[1].imshow(mask[0], cmap="gray", vmin=0, vmax=1)
    axes[1].set_title("label")
    for ax in axes:
        ax.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=120)
    plt.close()


# ── CLI ────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--mode",
        default="preview",
        choices=["preview", "splits"],
        help="preview: PNG samples; splits: train/val/test NPZ files",
    )
    p.add_argument("--task", default="grains", choices=["grains", "particles"])
    # preview mode
    p.add_argument("--n", type=_positive_int, default=4,
                   help="Number of preview samples (preview mode)")
    # splits mode
    p.add_argument("--n-train", type=_positive_int, default=200)
    p.add_argument("--n-val", type=_positive_int, default=50)
    p.add_argument("--n-test", type=_positive_int, default=50)
    p.add_argument("--overwrite", action="store_true",
                   help="Overwrite existing split directories")
    # shared
    p.add_argument("--size", type=_positive_int, default=128)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output", type=Path, default=Path("data/samples"))
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.size % 4 != 0:
        raise SystemExit(
            f"ERROR: --size must be divisible by 4 (got {args.size})."
        )

    if args.mode == "splits":
        args.output.mkdir(parents=True, exist_ok=True)
        generate_splits_to_disk(
            task=args.task,
            n_train=args.n_train,
            n_val=args.n_val,
            n_test=args.n_test,
            size=args.size,
            output_dir=args.output,
            seed=args.seed,
            overwrite=args.overwrite,
        )
    else:
        # preview mode
        args.output.mkdir(parents=True, exist_ok=True)
        imgs, masks = generate_batch(args.task, args.n, args.size, args.seed)
        for i in range(args.n):
            out = args.output / f"{args.task}_{i:02d}.png"
            _save_preview(imgs[i], masks[i], out)
            print(f"[gen] wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
