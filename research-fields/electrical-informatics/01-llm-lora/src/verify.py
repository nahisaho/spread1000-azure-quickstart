"""Post-training verification: finite metrics + file integrity.

Usage:
    python src/verify.py --output data/adapter/
    python src/verify.py --output data/adapter/ --manifest data/adapter/manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--output", type=Path, required=True,
                   help="Adapter output directory (contains metrics.json)")
    p.add_argument("--manifest", type=Path, default=None,
                   help="Path to manifest.json. Default: <output>/manifest.json")
    return p.parse_args()


def verify_metrics(metrics_path: Path) -> bool:
    ok = True
    if not metrics_path.exists():
        print(f"[verify] ERROR: metrics.json not found: {metrics_path}", file=sys.stderr)
        return False

    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[verify] ERROR: cannot read metrics.json: {exc}", file=sys.stderr)
        return False

    train_loss = metrics.get("train_loss")
    if train_loss is None:
        print("[verify] ERROR: metrics.json missing 'train_loss'", file=sys.stderr)
        ok = False
    elif not math.isfinite(float(train_loss)):
        print(f"[verify] ERROR: train_loss is non-finite: {train_loss}", file=sys.stderr)
        ok = False
    else:
        print(f"[verify] train_loss = {train_loss:.4f} — OK")

    eval_loss = metrics.get("eval_loss")
    if eval_loss is not None and not math.isfinite(float(eval_loss)):
        print(f"[verify] ERROR: eval_loss is non-finite: {eval_loss}", file=sys.stderr)
        ok = False
    elif eval_loss is not None:
        print(f"[verify] eval_loss  = {eval_loss:.4f} — OK")

    return ok


def verify_manifest(manifest_path: Path) -> bool:
    ok = True
    if not manifest_path.exists():
        print(f"[verify] WARNING: manifest.json not found: {manifest_path}", file=sys.stderr)
        return True  # non-fatal; manifest is written by train step

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[verify] ERROR: cannot read manifest.json: {exc}", file=sys.stderr)
        return False

    files = manifest.get("files", {})
    base_dir = manifest_path.parent
    for rel_path, expected_sha in files.items():
        abs_path = base_dir / rel_path
        if not abs_path.exists():
            print(f"[verify] ERROR: file in manifest not found: {abs_path}", file=sys.stderr)
            ok = False
            continue
        actual_sha = sha256_file(abs_path)
        if not hmac.compare_digest(actual_sha, expected_sha):
            print(f"[verify] ERROR: SHA-256 mismatch for {rel_path}", file=sys.stderr)
            print(f"         expected: {expected_sha}", file=sys.stderr)
            print(f"         actual:   {actual_sha}", file=sys.stderr)
            ok = False
        else:
            print(f"[verify] {rel_path} — SHA-256 OK")

    # Verify dataset SHA if present
    dataset_sha = manifest.get("dataset_sha256")
    dataset_path_str = manifest.get("dataset_path")
    if dataset_sha and dataset_path_str:
        dataset_path = Path(dataset_path_str)
        if dataset_path.exists():
            actual = sha256_file(dataset_path)
            if not hmac.compare_digest(actual, dataset_sha):
                print(f"[verify] ERROR: dataset SHA-256 mismatch: {dataset_path}", file=sys.stderr)
                ok = False
            else:
                print(f"[verify] dataset SHA-256 — OK")
        else:
            print(f"[verify] WARNING: dataset not found locally for SHA check: {dataset_path}",
                  file=sys.stderr)

    return ok


def main() -> int:
    args = parse_args()
    final_dir = args.output / "final"
    metrics_path = final_dir / "metrics.json"
    manifest_path = args.manifest or (args.output / "manifest.json")

    print(f"[verify] checking {args.output}")
    metrics_ok = verify_metrics(metrics_path)
    manifest_ok = verify_manifest(manifest_path)

    if metrics_ok and manifest_ok:
        print("[verify] ALL CHECKS PASSED")
        return 0
    else:
        print("[verify] VERIFICATION FAILED — see errors above", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
