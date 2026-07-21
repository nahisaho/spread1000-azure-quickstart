#!/usr/bin/env python3
"""ダウンロードした MONAI 予測 mask (NIfTI) を検証。

使い方:
    python verify-output.py <predictions ディレクトリ> [--expected-count 20] [--images-dir <元画像>]

チェック内容:
    - すべての予測 mask に spleen (label=1) が含まれる
    - --expected-count が指定されていれば件数一致を要求
    - --images-dir が指定されていれば、同名画像との shape と affine の一致を確認
    - 極端に小さい/大きい体積の外れ値を警告
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import nibabel as nib
    import numpy as np
except ImportError as e:
    print(f"必要ライブラリが不足: {e}", file=sys.stderr)
    print("インストール: pip install nibabel numpy", file=sys.stderr)
    sys.exit(1)


def find_image(images_dir: Path, mask_path: Path) -> Path | None:
    """mask ファイル名から対応する元画像を推定 (spleen_42_trans.nii.gz -> spleen_42.nii.gz)"""
    name = mask_path.name
    # 標準的な MONAI Bundle postfix: _trans, _seg, _pred
    for suffix in ("_trans", "_seg", "_pred"):
        if suffix in name:
            base = name.replace(suffix, "")
            cand = images_dir / base
            if cand.exists():
                return cand
    # postfix なしの同名ファイル
    cand = images_dir / name
    return cand if cand.exists() else None


def verify(pred_dir: Path, expected_count: int | None, images_dir: Path | None) -> int:
    nii_files = sorted(pred_dir.rglob("*.nii.gz"))
    if not nii_files:
        print(f"❌ {pred_dir} に .nii.gz が見つかりません", file=sys.stderr)
        return 1

    print(f"==== {len(nii_files)} ファイルを検証 ====")
    if expected_count is not None and len(nii_files) != expected_count:
        print(
            f"❌ ファイル数不一致: 実測 {len(nii_files)}, 期待 {expected_count}",
            file=sys.stderr,
        )
        return 1

    print(
        f"{'File':<40} {'Shape':<18} {'Labels':<12} {'Voxels(spleen)':>15}  {'Geom':>6}  {'Status':>10}"
    )
    print("-" * 110)

    failures = 0
    for f in nii_files:
        img = nib.load(str(f))
        data = np.asarray(img.dataobj)
        labels = np.unique(data).astype(int).tolist()
        spleen_voxels = int((data == 1).sum())

        status = "OK"
        if 1 not in labels:
            status = "NO_SPLEEN"
            failures += 1
        elif spleen_voxels < 1000:
            status = "TINY?"
        elif spleen_voxels > 5_000_000:
            status = "HUGE?"

        geom = "-"
        if images_dir is not None:
            src = find_image(images_dir, f)
            if src is None:
                geom = "no-src"
                if status == "OK":
                    status = "NO_SRC"
                failures += 1
            else:
                src_img = nib.load(str(src))
                shape_ok = src_img.shape[:3] == img.shape[:3]
                affine_ok = np.allclose(src_img.affine, img.affine, atol=1e-3)
                if shape_ok and affine_ok:
                    geom = "OK"
                else:
                    geom = f"S={shape_ok},A={affine_ok}"
                    if status == "OK":
                        status = "GEOM_FAIL"
                    failures += 1

        rel = f.relative_to(pred_dir) if f.is_relative_to(pred_dir) else f.name
        print(
            f"{str(rel):<40} {str(data.shape):<18} {str(labels):<12} {spleen_voxels:>15,}  {geom:>6}  {status:>10}"
        )

    print("-" * 110)
    if failures:
        print(f"❌ {failures} / {len(nii_files)} ファイルで検証失敗")
        return 1
    print(f"✓ すべての予測 mask が検証に合格 ({len(nii_files)} files)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pred_dir", type=Path, help="予測 mask を含むディレクトリ")
    ap.add_argument(
        "--expected-count", type=int, default=None,
        help="期待される mask ファイル数 (Task09 imagesTs なら 20)",
    )
    ap.add_argument(
        "--images-dir", type=Path, default=None,
        help="対応する元画像を含むディレクトリ (shape/affine 検証用)",
    )
    args = ap.parse_args()
    if not args.pred_dir.is_dir():
        print(f"❌ ディレクトリが存在しません: {args.pred_dir}", file=sys.stderr)
        return 1
    if args.images_dir is not None and not args.images_dir.is_dir():
        print(f"❌ 元画像ディレクトリが存在しません: {args.images_dir}", file=sys.stderr)
        return 1
    return verify(args.pred_dir, args.expected_count, args.images_dir)


if __name__ == "__main__":
    sys.exit(main())
