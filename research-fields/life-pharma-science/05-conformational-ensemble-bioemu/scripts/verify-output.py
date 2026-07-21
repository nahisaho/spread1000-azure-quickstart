#!/usr/bin/env python3
"""BioEmu 出力の基本整合性チェック。

チェック内容:
    - samples.xtc / topology.pdb / sequence.fasta が存在する
    - Frame 数 ≥ 期待値 (--min-frames)
    - すべての Frame で atom 数が一致
    - sequence.fasta の配列長 × 4 (backbone N,CA,C,O) と atom 数の関係が妥当
    - NaN / inf を含まない
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import mdtraj as md
    import numpy as np
except ImportError as e:
    print(f"必要ライブラリが不足: {e}", file=sys.stderr)
    print("pip install mdtraj numpy", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", type=Path, help="samples.xtc を含むディレクトリ (再帰探索)")
    ap.add_argument("--min-frames", type=int, default=1,
                    help="最低 frame 数 (BioEmu の filter で減ることを許容)")
    args = ap.parse_args()

    if not args.root.is_dir():
        print(f"❌ ディレクトリが存在しません: {args.root}", file=sys.stderr)
        return 1

    xtc_list = sorted(args.root.rglob("samples.xtc"))
    if not xtc_list:
        print(f"❌ samples.xtc が見つかりません (root={args.root})", file=sys.stderr)
        return 1

    failures = 0
    for xtc in xtc_list:
        job_dir = xtc.parent
        print(f"==== {xtc.relative_to(args.root) if xtc.is_relative_to(args.root) else xtc} ====")
        top = job_dir / "topology.pdb"
        fasta = job_dir / "sequence.fasta"
        for req in (top, fasta):
            if not req.exists():
                print(f"  ❌ {req.name} が存在しません")
                failures += 1
        if not top.exists():
            continue

        traj = md.load_xtc(str(xtc), top=str(top))
        n_frames = traj.n_frames
        n_atoms = traj.n_atoms
        print(f"  Frames: {n_frames} (期待 ≥ {args.min_frames})")
        print(f"  Atoms:  {n_atoms}")

        if n_frames < args.min_frames:
            print(f"  ❌ Frame 数不足")
            failures += 1

        if not np.isfinite(traj.xyz).all():
            print("  ❌ NaN/inf が座標に含まれる")
            failures += 1

        # 配列長との整合性: backbone (N,CA,C,O) だけなら 4L, 全 heavy atom なら 8〜10L 程度
        if fasta.exists():
            seq_lines = [l.strip() for l in fasta.read_text().splitlines() if not l.startswith(">")]
            seq = "".join(seq_lines).replace(" ", "")
            L = len(seq)
            per_residue = n_atoms / L if L else 0
            print(f"  Sequence length: {L}, atoms/residue: {per_residue:.1f}")
            if not 3.0 <= per_residue <= 20.0:
                print(f"  ❌ atoms/residue が想定範囲外")
                failures += 1

        rg = md.compute_rg(traj)
        print(f"  Rg range: {rg.min()*10:.2f} - {rg.max()*10:.2f} Å")

    print("")
    if failures:
        print(f"❌ {failures} 件の問題を検出")
        return 1
    print(f"✓ すべての BioEmu 出力が検証に合格 ({len(xtc_list)} run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
