#!/usr/bin/env python3
"""BioEmu 生成アンサンブルを解析する。

使い方:
    python analyze.py <ダウンロード先ディレクトリ> [--reference-pdb 1UAO.pdb]

    <ダウンロード先> の下に samples.xtc, topology.pdb, sequence.fasta が
    存在することを想定。az ml job download の出力構造に対応する。

出力:
    analysis.csv          rmsd_nm, radius_of_gyration_nm, cluster
    rmsd_histogram.png    (reference-pdb 指定時のみ)
    rg_histogram.png
    summary.txt           median RMSD/Rg, cluster 数, filtered frame 数
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import mdtraj as md
    import numpy as np
    from sklearn.cluster import DBSCAN
except ImportError as e:
    print(f"必要ライブラリが不足: {e}", file=sys.stderr)
    print("pip install mdtraj numpy scikit-learn matplotlib", file=sys.stderr)
    sys.exit(1)


def find_ensemble(root: Path) -> tuple[Path, Path]:
    xtc_list = sorted(root.rglob("samples.xtc"))
    if not xtc_list:
        print(f"❌ {root} 配下に samples.xtc がありません", file=sys.stderr)
        sys.exit(1)
    xtc = xtc_list[0]
    top = xtc.with_name("topology.pdb")
    if not top.exists():
        print(f"❌ topology.pdb が {top.parent} にありません", file=sys.stderr)
        sys.exit(1)
    return xtc, top


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", type=Path, help="samples.xtc/topology.pdb を含むディレクトリ (再帰)")
    ap.add_argument("--reference-pdb", type=Path, default=None,
                    help="RMSD 比較用の参照 PDB (例: 1UAO)")
    ap.add_argument("--rmsd-cutoff-nm", type=float, default=0.15,
                    help="DBSCAN eps in nm (default 0.15 = 1.5Å)")
    ap.add_argument("--min-samples", type=int, default=3, help="DBSCAN min_samples")
    ap.add_argument("--outdir", type=Path, default=Path("."), help="出力先")
    args = ap.parse_args()

    xtc, top = find_ensemble(args.root)
    print(f"==== 読み込み ====")
    print(f"  XTC:      {xtc}")
    print(f"  Topology: {top}")

    traj = md.load_xtc(str(xtc), top=str(top))
    print(f"  Frames:   {traj.n_frames}")
    print(f"  Atoms:    {traj.n_atoms}")

    ca_indices = traj.topology.select("name CA")
    if len(ca_indices) == 0:
        print("❌ Cα 原子が見つかりません", file=sys.stderr)
        return 1
    sample_ca = traj.atom_slice(ca_indices)

    rg_nm = md.compute_rg(traj)

    rmsd_nm = None
    if args.reference_pdb is not None and args.reference_pdb.exists():
        ref = md.load_pdb(str(args.reference_pdb))
        ref_ca_idx = ref.topology.select("name CA")
        ref_ca = ref.atom_slice(ref_ca_idx)
        if ref_ca.n_frames > 1:
            ref_ca = ref_ca[0]
        if ref_ca.n_atoms != sample_ca.n_atoms:
            print(
                f"⚠️  参照 Cα 数 ({ref_ca.n_atoms}) と生成 Cα 数 ({sample_ca.n_atoms}) が不一致 — "
                "RMSD 計算をスキップします",
                file=sys.stderr,
            )
        else:
            rmsd_nm = md.rmsd(sample_ca, ref_ca)
    elif args.reference_pdb is not None:
        print(f"⚠️  参照 PDB が存在しません: {args.reference_pdb}", file=sys.stderr)

    n = sample_ca.n_frames
    if n > 2000:
        print(f"⚠️  Frame 数 {n} が大きいため DBSCAN をスキップ (先頭 2000 で解析)", file=sys.stderr)
        sample_ca_for_cluster = sample_ca[:2000]
    else:
        sample_ca_for_cluster = sample_ca

    m = sample_ca_for_cluster.n_frames
    dm = np.zeros((m, m), dtype=np.float32)
    for i in range(m):
        dm[i] = md.rmsd(sample_ca_for_cluster, sample_ca_for_cluster, frame=i)
    labels = DBSCAN(
        eps=args.rmsd_cutoff_nm,
        min_samples=args.min_samples,
        metric="precomputed",
    ).fit_predict(dm)
    cluster_count = len(set(labels) - {-1})
    noise_count = int((labels == -1).sum())

    args.outdir.mkdir(parents=True, exist_ok=True)

    csv_cols = [rg_nm[: len(labels)]]
    header = "radius_of_gyration_nm"
    if rmsd_nm is not None:
        csv_cols.insert(0, rmsd_nm[: len(labels)])
        header = "rmsd_nm," + header
    csv_cols.append(labels)
    header += ",cluster"
    np.savetxt(
        args.outdir / "analysis.csv",
        np.column_stack(csv_cols),
        delimiter=",",
        header=header,
        comments="",
        fmt=["%.6f"] * (len(csv_cols) - 1) + ["%d"],
    )

    if rmsd_nm is not None:
        plt.figure()
        plt.hist(rmsd_nm * 10.0, bins=30, edgecolor="black")
        plt.xlabel("Cα RMSD to reference (Å)")
        plt.ylabel("Number of samples")
        plt.title(f"RMSD distribution ({traj.n_frames} samples)")
        plt.tight_layout()
        plt.savefig(args.outdir / "rmsd_histogram.png", dpi=180)
        plt.close()

    plt.figure()
    plt.hist(rg_nm * 10.0, bins=30, edgecolor="black")
    plt.xlabel("Radius of gyration (Å)")
    plt.ylabel("Number of samples")
    plt.title(f"Rg distribution ({traj.n_frames} samples)")
    plt.tight_layout()
    plt.savefig(args.outdir / "rg_histogram.png", dpi=180)
    plt.close()

    lines = [
        f"Frames analyzed:       {traj.n_frames}",
        f"Median Rg:             {np.median(rg_nm) * 10:.3f} Å",
        f"Rg 5-95 percentile:    {np.percentile(rg_nm,5)*10:.3f}〜{np.percentile(rg_nm,95)*10:.3f} Å",
        f"DBSCAN eps (Cα RMSD):  {args.rmsd_cutoff_nm*10:.2f} Å",
        f"DBSCAN clusters:       {cluster_count} (noise frames: {noise_count})",
    ]
    if rmsd_nm is not None:
        lines.append(f"Median RMSD to ref:    {np.median(rmsd_nm) * 10:.3f} Å")
        lines.append(f"Min RMSD:              {rmsd_nm.min() * 10:.3f} Å")

    summary = "\n".join(lines)
    (args.outdir / "summary.txt").write_text(summary + "\n")
    print("")
    print("==== サマリ ====")
    print(summary)
    print("")
    print(f"出力: {args.outdir}/{{analysis.csv,rmsd_histogram.png,rg_histogram.png,summary.txt}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
