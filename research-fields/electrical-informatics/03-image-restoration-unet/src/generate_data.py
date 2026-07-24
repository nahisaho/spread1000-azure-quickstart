"""
合成クリーン画像 + Gaussian ノイズによる (clean, noisy) ペア生成.

- ライセンス制約なし (すべて手続き的生成)
- 各サンプル: 128x128, 1 channel, float32 in [0, 1]
- 幾何プリミティブ (矩形、円、グラデーション、直線) をランダム配置
- ガウシアン平滑化で自然なエッジに → 加算 Gaussian ノイズ σ=0.10

保存形式: data/{split}/{idx:04d}.npz  {"clean": (1,H,W), "noisy": (1,H,W)}
分割:     train / val / test
          (source_image はすべて独立生成なのでリーク不可。実データに移行する際は
           source_image_id でグループ分けして split=cross-image で分割すること)

Idempotency:
  - 既存の split ディレクトリに .npz が存在する場合は --overwrite が必要
  - 各 split は一時ディレクトリに書き込んだ後、atomic rename で差し替える
  - 完了後に data/manifest.json (各ファイルの SHA-256) を書き出す
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

import numpy as np


def _positive_int(value: str) -> int:
    v = int(value)
    if v <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value!r}")
    return v


def _positive_float(value: str) -> float:
    v = float(value)
    if v <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive float, got {value!r}")
    return v


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


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate synthetic (clean, noisy) NPZ pairs.")
    p.add_argument("--n-train", type=_positive_int, default=200)
    p.add_argument("--n-val", type=_positive_int, default=40)
    p.add_argument("--n-test", type=_positive_int, default=40,
                   help="Number of held-out test samples (default: 40)")
    p.add_argument("--size", type=_positive_int, default=128,
                   help="Patch size (must be divisible by 4)")
    p.add_argument("--noise-sigma", type=_positive_float, default=0.10)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--seed", type=_positive_int, default=42)
    p.add_argument("--overwrite", action="store_true",
                   help="Required if any split directory already contains .npz files")
    return p.parse_args()


def _check_overwrite(split_dir: Path, overwrite: bool) -> None:
    if split_dir.exists() and any(split_dir.glob("*.npz")):
        if not overwrite:
            raise SystemExit(
                f"[abort] {split_dir} already contains .npz files. "
                "Pass --overwrite to regenerate."
            )


def _write_split(
    dest_dir: Path,
    n: int,
    size: int,
    noise_sigma: float,
    rng: np.random.Generator,
) -> list[tuple[str, str]]:
    """Write n samples to dest_dir; returns list of (relative_path, sha256)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Write into a sibling tmp dir, then atomic rename
    parent = dest_dir.parent
    tmp_dir = parent / f"_tmp_{dest_dir.name}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    records: list[tuple[str, str]] = []
    for i in range(n):
        clean = make_clean_sample(size=size, rng=rng)
        noisy = add_gaussian_noise(clean, noise_sigma, rng)
        out_path = tmp_dir / f"{i:04d}.npz"
        np.savez(out_path, clean=clean, noisy=noisy)
        sha = _sha256_file(out_path)
        records.append((f"{dest_dir.name}/{i:04d}.npz", sha))

    # Atomic replace: remove old, rename tmp
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    os.replace(tmp_dir, dest_dir)

    print(f"[gen] {dest_dir}: {n} samples ({size}x{size}, sigma={noise_sigma})")
    return records


def main() -> None:
    args = parse_args()

    if args.size % 4 != 0:
        raise SystemExit(
            f"[abort] --size {args.size} is not divisible by 4 "
            "(MiniUNet requires two MaxPool2d(2) layers)."
        )

    root = args.output_dir or (Path(__file__).resolve().parents[1] / "data")
    rng = np.random.default_rng(args.seed)

    # Idempotency guard
    for split_name in ("train", "val", "test"):
        _check_overwrite(root / split_name, args.overwrite)

    all_records: list[tuple[str, str]] = []
    all_records += _write_split(root / "train", args.n_train, args.size, args.noise_sigma, rng)
    all_records += _write_split(root / "val", args.n_val, args.size, args.noise_sigma, rng)
    all_records += _write_split(root / "test", args.n_test, args.size, args.noise_sigma, rng)

    # Emit manifest.json with per-file SHA-256
    manifest = {
        "seed": args.seed,
        "size": args.size,
        "noise_sigma": args.noise_sigma,
        "n_train": args.n_train,
        "n_val": args.n_val,
        "n_test": args.n_test,
        "files": {rel: sha for rel, sha in all_records},
    }
    manifest_path = root / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, allow_nan=False)
    print(f"[gen] manifest → {manifest_path}")

    # Preview samples
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
