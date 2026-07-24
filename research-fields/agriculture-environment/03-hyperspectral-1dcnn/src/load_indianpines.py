"""Indian Pines real-data loader (BLOCKING 1 fix).

Tries community mirrors with curl, verifies sha256, loads via scipy.io.

⚠ Internet access required for first download.
⚠ DATA LICENSE NOTE: The Indian Pines scene was acquired by the AVIRIS sensor
  (NASA/JPL) over the Agriculture site in north-western Indiana in June 1992.
  The processed .mat files are widely used in academic research. Formal
  per-file licensing is not documented; cite Landgrebe (1992/1999) and contact
  Purdue University for authoritative terms before any non-research use.

  Preferred citation:
    Landgrebe, D. (2003). Signal Theory Methods in Multispectral Remote Sensing.
    Wiley. (https://engineering.purdue.edu/~biehl/MultiSpec/)

  TODO: Verify current mirror availability and license status before
  redistributing derived works. Known mirrors listed below; check each.
"""
from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Community mirrors — user MUST verify availability and license terms.
# Direct Purdue hotlink returns 403; do NOT add it here.
# TODO: Update sha256 hashes on first successful download (see _EXPECTED_SHA256).
IP_MIRRORS = [
    "https://www.ehu.eus/ccwintco/uploads/6/67/Indian_pines_corrected.mat",
    "https://www.ehu.eus/ccwintco/uploads/c/c4/Indian_pines_gt.mat",
]

# Expected SHA-256 hashes (fill in after verified first download).
# Set to None to skip verification (not recommended for production).
_EXPECTED_SHA256: dict[str, Optional[str]] = {
    "Indian_pines_corrected.mat": None,  # TODO: fill after first download
    "Indian_pines_gt.mat": None,          # TODO: fill after first download
}

CLASS_NAMES_IP = [
    "Alfalfa",            # 1
    "Corn-notill",        # 2
    "Corn-mintill",       # 3
    "Corn",               # 4
    "Grass-pasture",      # 5
    "Grass-trees",        # 6
    "Grass-pasture-mowed",# 7
    "Hay-windrowed",      # 8
    "Oats",               # 9
    "Soybean-notill",     # 10
    "Soybean-mintill",    # 11
    "Soybean-clean",      # 12
    "Wheat",              # 13
    "Woods",              # 14
    "Buildings-Grass-Trees-Drives",  # 15
    "Stone-Steel-Towers", # 16
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _curl_download(url: str, dest: Path) -> bool:
    """Try to download url → dest with curl. Returns True on success."""
    if not shutil.which("curl"):
        logger.warning("curl not found; trying urllib fallback")
        return _urllib_download(url, dest)
    cmd = ["curl", "-f", "-L", "--retry", "3", "--retry-delay", "2",
           "--max-time", "120", "-o", str(dest), url]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def _urllib_download(url: str, dest: Path) -> bool:
    """Fallback downloader via urllib."""
    try:
        import urllib.request
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as exc:
        logger.warning("urllib fallback failed: %s", exc)
        return False


def _try_download(url: str, dest: Path, expected_sha: Optional[str] = None) -> bool:
    """Download url to dest, optionally verify sha256."""
    logger.info("Trying %s …", url)
    if not _curl_download(url, dest):
        logger.warning("Download failed: %s", url)
        return False
    if expected_sha is not None:
        actual = _sha256(dest)
        if actual != expected_sha:
            logger.warning("SHA-256 mismatch for %s: expected %s got %s",
                           dest.name, expected_sha, actual)
            dest.unlink(missing_ok=True)
            return False
    actual_sha = _sha256(dest)
    logger.info("Downloaded %s (sha256=%s)", dest.name, actual_sha[:16] + "…")
    return True


def download_indianpines(data_dir: Path) -> tuple[Path, Path]:
    """Download Indian Pines .mat files to data_dir. Returns (cube_path, gt_path)."""
    data_dir.mkdir(parents=True, exist_ok=True)
    cube_path = data_dir / "Indian_pines_corrected.mat"
    gt_path = data_dir / "Indian_pines_gt.mat"

    cube_urls = [IP_MIRRORS[0]]
    gt_urls = [IP_MIRRORS[1]]

    if not cube_path.exists():
        ok = False
        for url in cube_urls:
            ok = _try_download(url, cube_path, _EXPECTED_SHA256.get("Indian_pines_corrected.mat"))
            if ok:
                break
        if not ok:
            raise RuntimeError(
                "Could not download Indian_pines_corrected.mat from any mirror.\n"
                "Please download manually from one of:\n"
                f"  {IP_MIRRORS[0]}\n"
                "and place it in: " + str(data_dir)
            )

    if not gt_path.exists():
        ok = False
        for url in gt_urls:
            ok = _try_download(url, gt_path, _EXPECTED_SHA256.get("Indian_pines_gt.mat"))
            if ok:
                break
        if not ok:
            raise RuntimeError(
                "Could not download Indian_pines_gt.mat from any mirror.\n"
                "Please download manually from one of:\n"
                f"  {IP_MIRRORS[1]}\n"
                "and place it in: " + str(data_dir)
            )

    return cube_path, gt_path


def load_indianpines(
    data_dir: Path | str = "data",
    *,
    auto_download: bool = True,
) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    """Load Indian Pines dataset.

    Returns
    -------
    X : (N, 200) float32  — per-pixel spectra (background excluded)
    y : (N,) int64        — 0-indexed class labels
    class_names : list[str]
    coords : (N, 2) int32 — (row, col) pixel coordinates in original image
    """
    try:
        import scipy.io as sio
    except ImportError as exc:
        raise ImportError(
            "scipy is required for Indian Pines: pip install scipy"
        ) from exc

    data_dir = Path(data_dir)
    cube_path = data_dir / "Indian_pines_corrected.mat"
    gt_path = data_dir / "Indian_pines_gt.mat"

    if not cube_path.exists() or not gt_path.exists():
        if auto_download:
            logger.info("Indian Pines .mat files not found; attempting download …")
            download_indianpines(data_dir)
        else:
            missing = [p for p in [cube_path, gt_path] if not p.exists()]
            raise FileNotFoundError(
                f"Missing files: {missing}\n"
                "Run with auto_download=True or download manually.\n"
                f"Cube URL: {IP_MIRRORS[0]}\n"
                f"GT URL:   {IP_MIRRORS[1]}"
            )

    cube = sio.loadmat(str(cube_path))
    gt = sio.loadmat(str(gt_path))

    # Key names vary by source; try common variants
    cube_data = None
    for key in ["indian_pines_corrected", "indian_pines", "data"]:
        if key in cube:
            cube_data = cube[key]
            break
    if cube_data is None:
        # Last resort: pick the largest ndarray
        arrays = {k: v for k, v in cube.items()
                  if not k.startswith("_") and isinstance(v, np.ndarray) and v.ndim >= 3}
        if not arrays:
            raise ValueError("Cannot find HSI cube in .mat file; keys: " + str(list(cube.keys())))
        cube_data = max(arrays.values(), key=lambda a: a.size)

    gt_data = None
    for key in ["indian_pines_gt", "gt", "labels"]:
        if key in gt:
            gt_data = gt[key]
            break
    if gt_data is None:
        arrays = {k: v for k, v in gt.items()
                  if not k.startswith("_") and isinstance(v, np.ndarray) and v.ndim == 2}
        if not arrays:
            raise ValueError("Cannot find GT map in .mat file; keys: " + str(list(gt.keys())))
        gt_data = max(arrays.values(), key=lambda a: a.size)

    # cube_data: (H, W, C), gt_data: (H, W)
    H, W, C = cube_data.shape
    logger.info("Indian Pines cube: %d×%d×%d  gt: %d×%d", H, W, C, *gt_data.shape)

    mask = gt_data > 0  # exclude background (label 0)
    rows, cols = np.where(mask)
    X = cube_data[mask].astype(np.float32)  # (N, C)
    y = gt_data[mask].astype(np.int64) - 1  # 0-indexed
    coords = np.stack([rows, cols], axis=1).astype(np.int32)

    n_classes = int(y.max()) + 1
    class_names = CLASS_NAMES_IP[:n_classes]

    if not np.all(np.isfinite(X)):
        n_bad = np.sum(~np.isfinite(X))
        logger.warning("Found %d non-finite values in cube; replacing with 0", n_bad)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    logger.info("Loaded %d pixels, %d classes, %d bands", len(y), n_classes, C)
    return X, y, class_names, coords
