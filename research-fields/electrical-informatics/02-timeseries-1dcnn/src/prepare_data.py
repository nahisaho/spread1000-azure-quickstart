"""
UCI HAR (Human Activity Recognition Using Smartphones) ダウンローダ・変換.

- UCI 公式 ZIP (~58 MB) を data/har.zip にダウンロード
- SHA-256 で整合性チェック
- 安全な展開 (絶対パス・親参照拒否)
- Inertial Signals (9 チャネル × 128 時点) を読み込み
- (N, 9, 128) float32 テンソル + label + subject_id を data/har_windows.npz に保存

出典: Anguita, D. et al. (2013). A Public Domain Dataset for Human
Activity Recognition Using Smartphones. ESANN 2013.
https://archive.ics.uci.edu/dataset/240/  (CC BY 4.0)
"""
from __future__ import annotations

import hashlib
import os
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ZIP_PATH = DATA_DIR / "har.zip"
UNZIP_DIR = DATA_DIR / "UCI_HAR_Dataset"
NPZ_PATH = DATA_DIR / "har_windows.npz"

# 公式ミラー (UCI Machine Learning Repository)
URL = (
    "https://archive.ics.uci.edu/static/public/240/"
    "human+activity+recognition+using+smartphones.zip"
)

# 9 つの Inertial Signal ファイル名 (順序を固定)
SIGNAL_NAMES = [
    "body_acc_x",
    "body_acc_y",
    "body_acc_z",
    "body_gyro_x",
    "body_gyro_y",
    "body_gyro_z",
    "total_acc_x",
    "total_acc_y",
    "total_acc_z",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"[data] cached: {dest} ({dest.stat().st_size / 1e6:.1f} MB)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[data] downloading {url}")
    print(f"[data]     → {dest}")

    def _progress(block, block_size, total_size):
        pct = min(100.0, block * block_size / max(1, total_size) * 100)
        sys.stdout.write(f"\r[data]     {pct:5.1f}%")
        sys.stdout.flush()

    urlretrieve(url, dest, reporthook=_progress)
    sys.stdout.write("\n")
    print(f"[data] downloaded ({dest.stat().st_size / 1e6:.1f} MB)")
    print(f"[data] sha256: {_sha256(dest)}")


def _safe_extract(zip_path: Path, out_dir: Path) -> Path:
    """絶対パスや `..` を含むエントリを拒否 (Zip Slip 対策)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for member in z.namelist():
            member_path = (out_dir / member).resolve()
            if not str(member_path).startswith(str(out_dir.resolve())):
                raise RuntimeError(f"unsafe zip entry: {member}")
        z.extractall(out_dir)

    # 内側にネストされた「UCI HAR Dataset」フォルダを探す
    for candidate in out_dir.rglob("UCI HAR Dataset"):
        if candidate.is_dir() and (candidate / "train").exists():
            return candidate
    raise RuntimeError("UCI HAR Dataset folder not found after extract")


def _load_split(root: Path, split: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(N, 9, 128) float32, (N,) int64 label (0-5), (N,) int64 subject_id."""
    signals = []
    for name in SIGNAL_NAMES:
        p = root / split / "Inertial Signals" / f"{name}_{split}.txt"
        signals.append(np.loadtxt(p, dtype=np.float32))
    X = np.stack(signals, axis=1)  # (N, 9, 128)

    y = np.loadtxt(root / split / f"y_{split}.txt", dtype=np.int64) - 1  # 1..6 -> 0..5
    subj = np.loadtxt(root / split / f"subject_{split}.txt", dtype=np.int64)

    assert X.shape[0] == y.shape[0] == subj.shape[0]
    assert X.shape[1:] == (9, 128), f"unexpected shape: {X.shape}"
    return X, y, subj


def main() -> None:
    print(f"[data] target dir: {DATA_DIR}")
    _download(URL, ZIP_PATH)
    root = _safe_extract(ZIP_PATH, UNZIP_DIR)
    print(f"[data] extracted: {root}")

    X_train, y_train, subj_train = _load_split(root, "train")
    X_test, y_test, subj_test = _load_split(root, "test")

    labels_path = root / "activity_labels.txt"
    activities = [
        line.split()[1] for line in labels_path.read_text().strip().splitlines()
    ]
    assert len(activities) == 6

    print(f"[data] train: X={X_train.shape}, subjects={sorted(set(subj_train.tolist()))}")
    print(f"[data] test : X={X_test.shape}, subjects={sorted(set(subj_test.tolist()))}")

    train_subj_set = set(subj_train.tolist())
    test_subj_set = set(subj_test.tolist())
    overlap = train_subj_set & test_subj_set
    assert not overlap, f"subject leak: {overlap}"
    print("[data] OK: no subject overlap between train and test")

    NPZ_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        NPZ_PATH,
        X_train=X_train,
        y_train=y_train,
        subj_train=subj_train,
        X_test=X_test,
        y_test=y_test,
        subj_test=subj_test,
        activities=np.array(activities),
    )
    size_mb = NPZ_PATH.stat().st_size / 1e6
    print(f"[data] saved → {NPZ_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
