"""Verification checks for the UCI HAR 1D-CNN artifacts."""
from __future__ import annotations

import argparse
import hmac
import json
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score

from _argtypes import bounded_probability, positive_int
from model import BiosignalCNN

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--normalization", required=True, type=Path)
    parser.add_argument("--dataset-npz", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--min-macro-f1", type=bounded_probability, default=0.70)
    parser.add_argument("--max-macro-f1", type=bounded_probability, default=0.99)
    parser.add_argument("--expected-classes", type=positive_int, default=6)
    return parser.parse_args()


def _resolve_manifest_path(path_str: str | None) -> Path | None:
    if not path_str:
        return None
    path = Path(path_str)
    if path.is_absolute():
        return path
    return ROOT / path


def _verify_manifest_hashes(manifest_path: Path, checkpoint: Path, normalization: Path, dataset_npz: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pairs = [
        ("checkpoint_sha256", checkpoint, manifest.get("checkpoint_sha256")),
        ("normalization_sha256", normalization, manifest.get("normalization_sha256")),
        ("dataset_sha256", dataset_npz, manifest.get("dataset_sha256")),
    ]
    for label, path, expected in pairs:
        if expected is None:
            raise RuntimeError(f"manifest is missing required field: {label}")
        actual = _sha256(path)
        if not hmac.compare_digest(expected, actual):
            raise RuntimeError(f"manifest {label} mismatch for {path}: expected {expected}, got {actual}")

    lockfile_sha = manifest.get("lockfile_sha256")
    lockfile_path = _resolve_manifest_path(manifest.get("lockfile_path"))
    if lockfile_sha:
        if lockfile_path is None or not lockfile_path.exists():
            raise RuntimeError("manifest lockfile_sha256 is present but lockfile_path is missing or not found")
        actual_lockfile_sha = _sha256(lockfile_path)
        if not hmac.compare_digest(lockfile_sha, actual_lockfile_sha):
            raise RuntimeError(
                "manifest lockfile_sha256 mismatch for "
                f"{lockfile_path}: expected {lockfile_sha}, got {actual_lockfile_sha}"
            )


def main() -> None:
    args = parse_args()
    if args.min_macro_f1 > args.max_macro_f1:
        raise ValueError("--min-macro-f1 must be <= --max-macro-f1")

    for path in [args.checkpoint, args.normalization, args.dataset_npz]:
        if not path.exists():
            raise FileNotFoundError(f"required file not found: {path}")
    if args.manifest is not None and not args.manifest.exists():
        raise FileNotFoundError(f"manifest not found: {args.manifest}")

    if args.manifest is not None:
        _verify_manifest_hashes(args.manifest, args.checkpoint, args.normalization, args.dataset_npz)
        print("[verify] manifest SHA-256 checks: OK")

    ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    norm = np.load(args.normalization, allow_pickle=False)
    data = np.load(args.dataset_npz, allow_pickle=False)

    X_test = data["X_test"]
    y_test = data["y_test"]
    activities = [str(a) for a in data["activities"].tolist()]
    mean = norm["mean"]
    std = norm["std"]

    if X_test.ndim != 3:
        raise ValueError(f"expected X_test ndim=3, got {X_test.shape}")
    if X_test.shape[1] != ckpt.get("n_channels", 9):
        raise ValueError(
            f"channel mismatch: X_test has {X_test.shape[1]}, checkpoint expects {ckpt.get('n_channels', 9)}"
        )
    if mean.shape != (1, X_test.shape[1], 1) or std.shape != (1, X_test.shape[1], 1):
        raise ValueError(f"unexpected normalization shapes: mean={mean.shape}, std={std.shape}")
    if not np.isfinite(X_test).all():
        raise ValueError("X_test contains non-finite values")
    if not np.isfinite(mean).all() or not np.isfinite(std).all():
        raise ValueError("normalization statistics contain non-finite values")
    if set(np.unique(y_test).tolist()) != set(range(args.expected_classes)):
        raise ValueError("dataset labels do not match expected class set")
    if len(activities) != args.expected_classes:
        raise ValueError(
            f"expected {args.expected_classes} activity labels, got {len(activities)}"
        )

    X_test = ((X_test - mean) / std).astype(np.float32)
    if not np.isfinite(X_test).all():
        raise ValueError("normalized X_test contains non-finite values")

    model = BiosignalCNN(
        n_channels=ckpt.get("n_channels", X_test.shape[1]),
        n_classes=ckpt.get("n_classes", args.expected_classes),
        dropout=ckpt.get("dropout", 0.30),
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    if ckpt.get("n_classes", args.expected_classes) != args.expected_classes:
        raise ValueError(
            f"checkpoint class count {ckpt.get('n_classes')} does not match expected {args.expected_classes}"
        )

    sample = torch.from_numpy(X_test[: min(8, len(X_test))])
    with torch.no_grad():
        logits = model(sample)
        if logits.shape != (sample.shape[0], args.expected_classes):
            raise ValueError(f"unexpected logits shape: {tuple(logits.shape)}")
        if not bool(torch.isfinite(logits).all().item()):
            raise RuntimeError("non-finite logits detected in sanity forward pass")
        probs = torch.softmax(logits, dim=-1)
        if not bool(torch.isfinite(probs).all().item()):
            raise RuntimeError("non-finite probabilities detected in sanity forward pass")

    full_preds = []
    batch_size = 256
    with torch.no_grad():
        for start in range(0, len(X_test), batch_size):
            xb = torch.from_numpy(X_test[start : start + batch_size])
            logits = model(xb)
            if not bool(torch.isfinite(logits).all().item()):
                raise RuntimeError(f"non-finite logits detected during full inference at start={start}")
            probs = torch.softmax(logits, dim=-1)
            if not bool(torch.isfinite(probs).all().item()):
                raise RuntimeError(f"non-finite probabilities detected during full inference at start={start}")
            full_preds.append(logits.argmax(dim=-1).cpu().numpy())
    y_pred = np.concatenate(full_preds)
    if set(np.unique(y_pred).tolist()) != set(range(args.expected_classes)):
        raise RuntimeError(
            f"predictions do not cover all classes: {sorted(set(np.unique(y_pred).tolist()))}"
        )

    accuracy = float(accuracy_score(y_test, y_pred))
    macro_f1 = float(
        f1_score(
            y_test,
            y_pred,
            labels=np.arange(args.expected_classes),
            average="macro",
            zero_division=0,
        )
    )
    if not np.isfinite(accuracy) or not np.isfinite(macro_f1):
        raise RuntimeError("metrics are non-finite")
    if macro_f1 < args.min_macro_f1:
        raise RuntimeError(f"macro_F1 {macro_f1:.4f} is below minimum {args.min_macro_f1:.4f}")
    if macro_f1 > args.max_macro_f1:
        raise RuntimeError(f"macro_F1 {macro_f1:.4f} exceeds suspicious upper bound {args.max_macro_f1:.4f}")

    print("[verify] checkpoint       :", args.checkpoint)
    print("[verify] normalization    :", args.normalization)
    print("[verify] dataset          :", args.dataset_npz)
    print(f"[verify] samples          : {len(y_test)}")
    print(f"[verify] classes          : {args.expected_classes}")
    print(f"[verify] accuracy         : {accuracy:.4f}")
    print(f"[verify] macro_F1         : {macro_f1:.4f}")
    print("[verify] status           : OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"[verify] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
