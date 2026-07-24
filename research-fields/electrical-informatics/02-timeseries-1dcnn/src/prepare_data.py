"""
UCI HAR (Human Activity Recognition Using Smartphones) ダウンローダ・変換.

- UCI 公式 ZIP (~58 MB) を data/har.zip にダウンロード
- outer archive SHA-256 を厳密に検証
- 安全な展開 (Zip Slip / symlink / device entry 対策)
- ネストされた UCI HAR Dataset.zip も展開
- Inertial Signals (9 チャネル × 128 時点) を読み込み
- (N, 9, 128) float32 テンソル + label + subject_id を data/har_windows.npz に保存

出典: Anguita, D. et al. (2013). A Public Domain Dataset for Human
Activity Recognition Using Smartphones. ESANN 2013.
https://archive.ics.uci.edu/dataset/240/  (CC BY 4.0)
"""
from __future__ import annotations

import hashlib
import shutil
import stat
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath
from urllib.error import URLError
from urllib.request import urlopen

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ZIP_PATH = DATA_DIR / "har.zip"
UNZIP_DIR = DATA_DIR / "UCI_HAR_Dataset"
NPZ_PATH = DATA_DIR / "har_windows.npz"
EXPECTED_OUTER_SHA256 = "c00b803081a5c797cd5e4b83700a9810b38d53d9d84e01917e090e1fdbc81031"
URL = (
    "https://archive.ics.uci.edu/static/public/240/"
    "human+activity+recognition+using+smartphones.zip"
)
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
EXPECTED_SHAPE = (9, 128)
EXPECTED_LABEL_SET = set(range(6))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_outer_hash(path: Path) -> None:
    actual = _sha256(path)
    if actual != EXPECTED_OUTER_SHA256:
        raise RuntimeError(
            "outer archive SHA-256 mismatch for "
            f"{path}: expected {EXPECTED_OUTER_SHA256}, got {actual}"
        )
    print(f"[data] sha256 OK: {actual}")


def _download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"[data] cached: {dest} ({dest.stat().st_size / 1e6:.1f} MB)")
        _verify_outer_hash(dest)
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest.with_suffix(dest.suffix + ".part")
    if part_path.exists():
        part_path.unlink()

    backoffs = [1, 2, 4]
    for attempt in range(1, len(backoffs) + 2):
        if attempt > 1:
            print(f"[data] retry attempt {attempt}/{len(backoffs) + 1}")
        print(f"[data] downloading {url}")
        downloaded = 0
        try:
            with urlopen(url, timeout=60) as response, part_path.open("wb") as handle:
                total_size = int(response.headers.get("Content-Length", "0") or 0)
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    handle.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = min(100.0, downloaded / total_size * 100.0)
                        sys.stdout.write(f"\r[data]     {pct:5.1f}%")
                    else:
                        sys.stdout.write(f"\r[data]     {downloaded / 1e6:6.1f} MB")
                    sys.stdout.flush()
            sys.stdout.write("\n")
            actual = _sha256(part_path)
            if actual != EXPECTED_OUTER_SHA256:
                raise RuntimeError(
                    "downloaded outer archive SHA-256 mismatch: "
                    f"expected {EXPECTED_OUTER_SHA256}, got {actual}"
                )
            part_path.replace(dest)
            print(f"[data] downloaded ({dest.stat().st_size / 1e6:.1f} MB)")
            print(f"[data] sha256 OK: {actual}")
            return
        except (OSError, URLError, RuntimeError) as exc:
            sys.stdout.write("\n")
            if part_path.exists():
                part_path.unlink()
            if attempt > len(backoffs):
                raise RuntimeError(f"failed to download {url}: {exc}") from exc
            wait_seconds = backoffs[attempt - 1]
            print(f"[data] attempt {attempt} failed: {exc}")
            print(f"[data] waiting {wait_seconds}s before retry")
            time.sleep(wait_seconds)


def _member_mode(info: zipfile.ZipInfo) -> int:
    return (info.external_attr >> 16) & 0xFFFF


def _validate_member(info: zipfile.ZipInfo, out_dir: Path) -> Path:
    raw_name = info.filename
    member_path = PurePosixPath(raw_name)
    if member_path.is_absolute():
        raise RuntimeError(f"unsafe zip entry (absolute path): {raw_name}")
    if ".." in member_path.parts:
        raise RuntimeError(f"unsafe zip entry (parent traversal): {raw_name}")
    mode = _member_mode(info)
    if stat.S_ISLNK(mode):
        raise RuntimeError(f"unsafe zip entry (symlink): {raw_name}")
    if stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode):
        raise RuntimeError(f"unsafe zip entry (device or special file): {raw_name}")
    target_path = out_dir.joinpath(*member_path.parts)
    resolved_target = target_path.resolve()
    resolved_root = out_dir.resolve()
    if not resolved_target.is_relative_to(resolved_root):
        raise RuntimeError(f"unsafe zip entry (outside target dir): {raw_name}")
    return target_path


def _safe_extract(zip_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            target_path = _validate_member(info, out_dir)
            if info.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as src, target_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def _find_inner_zip(out_dir: Path) -> Path | None:
    for candidate in out_dir.rglob("UCI HAR Dataset.zip"):
        if candidate.is_file():
            return candidate
    return None


def _find_dataset_root(out_dir: Path) -> Path | None:
    for candidate in out_dir.rglob("UCI HAR Dataset"):
        if candidate.is_dir() and (candidate / "train").is_dir() and (candidate / "test").is_dir():
            return candidate
    return None


def _validate_split_arrays(X: np.ndarray, y: np.ndarray, subj: np.ndarray, split: str) -> None:
    if X.dtype != np.float32:
        raise ValueError(f"{split}: expected X dtype float32, got {X.dtype}")
    if y.dtype != np.int64:
        raise ValueError(f"{split}: expected y dtype int64, got {y.dtype}")
    if subj.dtype != np.int64:
        raise ValueError(f"{split}: expected subject dtype int64, got {subj.dtype}")
    if X.ndim != 3:
        raise ValueError(f"{split}: expected X ndim=3, got shape {X.shape}")
    if X.shape[1:] != EXPECTED_SHAPE:
        raise ValueError(
            f"{split}: expected X shape (*, {EXPECTED_SHAPE[0]}, {EXPECTED_SHAPE[1]}), got {X.shape}"
        )
    if y.ndim != 1 or subj.ndim != 1:
        raise ValueError(f"{split}: expected 1D y/subj, got y={y.shape}, subj={subj.shape}")
    if not (X.shape[0] == y.shape[0] == subj.shape[0]):
        raise ValueError(
            f"{split}: sample count mismatch X={X.shape[0]}, y={y.shape[0]}, subj={subj.shape[0]}"
        )
    if X.shape[0] == 0:
        raise ValueError(f"{split}: no samples loaded")
    if not np.isfinite(X).all():
        raise ValueError(f"{split}: X contains non-finite values")
    label_set = set(np.unique(y).tolist())
    if not label_set.issubset(EXPECTED_LABEL_SET):
        raise ValueError(f"{split}: unexpected labels {sorted(label_set)}")
    missing = EXPECTED_LABEL_SET - label_set
    if missing:
        raise ValueError(f"{split}: missing classes {sorted(missing)}")
    if np.any(subj <= 0):
        raise ValueError(f"{split}: subject IDs must be positive")


def _load_split(root: Path, split: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    signals: list[np.ndarray] = []
    for name in SIGNAL_NAMES:
        path = root / split / "Inertial Signals" / f"{name}_{split}.txt"
        if not path.exists():
            raise FileNotFoundError(f"missing inertial signal file: {path}")
        signal = np.loadtxt(path, dtype=np.float32)
        if signal.ndim != 2 or signal.shape[1] != EXPECTED_SHAPE[1]:
            raise ValueError(f"{split}: unexpected signal shape in {path.name}: {signal.shape}")
        signals.append(signal)
    X = np.stack(signals, axis=1).astype(np.float32, copy=False)

    label_path = root / split / f"y_{split}.txt"
    subject_path = root / split / f"subject_{split}.txt"
    if not label_path.exists() or not subject_path.exists():
        raise FileNotFoundError(f"missing label or subject file for split '{split}'")

    y = np.loadtxt(label_path, dtype=np.int64) - 1
    subj = np.loadtxt(subject_path, dtype=np.int64)
    _validate_split_arrays(X, y, subj, split)
    return X, y, subj


def main() -> None:
    print(f"[data] target dir: {DATA_DIR}")
    _download(URL, ZIP_PATH)

    _safe_extract(ZIP_PATH, UNZIP_DIR)
    inner_zip = _find_inner_zip(UNZIP_DIR)
    if inner_zip is None:
        print(
            "[data] ERROR: nested 'UCI HAR Dataset.zip' was not found after outer extraction.",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"[data] extracting nested archive: {inner_zip}")
    _safe_extract(inner_zip, UNZIP_DIR)
    root = _find_dataset_root(UNZIP_DIR)
    if root is None:
        raise RuntimeError("UCI HAR Dataset folder not found after nested extraction")
    print(f"[data] extracted: {root}")

    X_train, y_train, subj_train = _load_split(root, "train")
    X_test, y_test, subj_test = _load_split(root, "test")

    labels_path = root / "activity_labels.txt"
    if not labels_path.exists():
        raise FileNotFoundError(f"missing activity_labels.txt: {labels_path}")
    activities: list[str] = []
    for line in labels_path.read_text(encoding="utf-8").strip().splitlines():
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"invalid activity_labels line: {line!r}")
        activities.append(parts[1])
    if len(activities) != len(EXPECTED_LABEL_SET):
        raise ValueError(f"expected 6 activity labels, got {len(activities)}")

    train_label_set = set(np.unique(y_train).tolist())
    test_label_set = set(np.unique(y_test).tolist())
    if train_label_set != EXPECTED_LABEL_SET or test_label_set != EXPECTED_LABEL_SET:
        raise ValueError(
            f"expected all classes in both splits; train={sorted(train_label_set)}, test={sorted(test_label_set)}"
        )

    train_subjects = set(subj_train.tolist())
    test_subjects = set(subj_test.tolist())
    overlap = train_subjects & test_subjects
    if overlap:
        raise RuntimeError(f"subject leak between official train/test: {sorted(overlap)}")

    print(f"[data] train: X={X_train.shape}, subjects={sorted(train_subjects)}")
    print(f"[data] test : X={X_test.shape}, subjects={sorted(test_subjects)}")
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
