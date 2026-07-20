#!/usr/bin/env python3
"""
TamGen 推論ラッパー (SPReAD-1000 クイックスタート版)
-------------------------------------------------
- 上流 example_inference.sh は data/crossdocked/bin/ を要求するため、
  クリーンインストールでは動作しない。本スクリプトは PDB ID から
  直接ポケット抽出 → 生成 → 物性計算までを一貫実行する。
- 上流 TamGen_Demo.py の API に厳密に従う (2024-09 pinned commit)。

使い方:
    conda activate TamGen
    cd ~/TamGen
    python ~/spread1000-azure-quickstart/quickstarts/foundation-model-science/tamgen-drug-discovery/scripts/generate_from_pdb.py \\
        --pdb 3wze --num-molecules 50 --output-dir output/3wze
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate TamGen molecules for a given PDB target.")
    ap.add_argument("--pdb", required=True, help="PDB ID (e.g. 3wze). 小文字化される。")
    ap.add_argument("--num-molecules", type=int, default=50,
                    help="生成する有効・ユニーク分子の目標数 (既定 50)。")
    ap.add_argument("--max-seeds", type=int, default=101,
                    help="ランダムシードの上限 (既定 101)。")
    ap.add_argument("--pocket-threshold", type=float, default=10.0,
                    help="結合ポケット半径 (Å, 既定 10)。")
    ap.add_argument("--ckpt", default="checkpoints/crossdock_pdb_A10/checkpoint_best.pt",
                    help="TamGen チェックポイント。")
    ap.add_argument("--data", default="TamGen_Demo_Data",
                    help="TamGen_Demo_Data ディレクトリ。")
    ap.add_argument("--output-dir", default=None,
                    help="出力ディレクトリ (既定: output/<pdb>)。")
    args = ap.parse_args()

    pdb_id = args.pdb.lower()
    out_dir = Path(args.output_dir or f"output/{pdb_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # GPU を明示 (Compute Instance の 1 GPU 想定)
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

    # 遅延インポート: TamGen リポジトリ配下で実行される前提
    if not Path("TamGen_Demo.py").exists():
        print("❌ このスクリプトは ~/TamGen ディレクトリで実行してください "
              "(TamGen_Demo.py が見つかりません)", file=sys.stderr)
        return 2

    from TamGen_Demo import TamGenDemo, prepare_pdb_data  # noqa: E402
    from rdkit import Chem  # noqa: E402
    from rdkit.Chem import AllChem, Descriptors, QED, Lipinski, DataStructs  # noqa: E402

    # 1) PDB からポケットデータ生成 (上流 API)
    print(f"[1/3] PDB {pdb_id} のポケットを抽出 (threshold={args.pocket_threshold} Å)")
    prepare_pdb_data(pdb_id=pdb_id, DemoDataFolder=args.data, thr=args.pocket_threshold)

    # 2) TamGen ロード + 分子生成
    print(f"[2/3] TamGen をロードして {args.num_molecules} 個の分子を生成")
    worker = TamGenDemo(data=args.data, ckpt=args.ckpt, use_conditional=True)
    worker.reload_data(subset=f"gen_{pdb_id}")
    results_set, ref_mol = worker.sample(
        m_sample=args.num_molecules,
        maxseed=args.max_seeds,
    )

    # 3) 物性計算 (TamGen 自体は SMILES しか返さないため RDKit で自前計算)
    print(f"[3/3] {len(results_set)} 個の生成分子に対して物性を計算")
    rows = []
    for smi, mol in results_set.items():
        if mol is None:
            continue
        try:
            row = {
                "SMILES": smi,
                "MW": Descriptors.MolWt(mol),
                "LogP": Descriptors.MolLogP(mol),
                "QED": QED.qed(mol),
                "TPSA": Descriptors.TPSA(mol),
                "HBD": Lipinski.NumHDonors(mol),
                "HBA": Lipinski.NumHAcceptors(mol),
                "NumRings": Lipinski.RingCount(mol),
            }
            row["Lipinski"] = (
                row["MW"] <= 500 and row["LogP"] <= 5
                and row["HBD"] <= 5 and row["HBA"] <= 10
            )
            rows.append(row)
        except Exception as e:  # pragma: no cover
            print(f"  warning: {smi}: {e}", file=sys.stderr)

    # Tanimoto 多様性
    mols_valid = [Chem.MolFromSmiles(r["SMILES"]) for r in rows]
    mols_valid = [m for m in mols_valid if m is not None]
    fps = [AllChem.GetMorganFingerprintAsBitVect(m, 2, 2048) for m in mols_valid]
    sims: list[float] = []
    for i in range(len(fps)):
        for j in range(i + 1, len(fps)):
            sims.append(DataStructs.TanimotoSimilarity(fps[i], fps[j]))
    diversity = 1.0 - (sum(sims) / len(sims)) if sims else 0.0

    # 保存
    smiles_path = out_dir / "generated_molecules.smi"
    csv_path = out_dir / "generated_molecules.csv"
    stats_path = out_dir / "generation_stats.json"

    with smiles_path.open("w") as f:
        for r in rows:
            f.write(r["SMILES"] + "\n")

    with csv_path.open("w") as f:
        headers = ["SMILES", "MW", "LogP", "QED", "TPSA", "HBD", "HBA", "NumRings", "Lipinski"]
        f.write(",".join(headers) + "\n")
        for r in rows:
            f.write(",".join(str(r[h]) for h in headers) + "\n")

    stats = {
        "pdb_id": pdb_id,
        "num_requested": args.num_molecules,
        "num_generated_valid": len(rows),
        "num_lipinski_pass": sum(1 for r in rows if r["Lipinski"]),
        "mean_tanimoto_diversity": round(diversity, 4),
        "ckpt": args.ckpt,
        "pocket_threshold_angstrom": args.pocket_threshold,
    }
    with stats_path.open("w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print()
    print("==========================================================")
    print(f" ✅ 完了: 出力先 {out_dir}")
    print("==========================================================")
    print(f"  生成分子 (有効・ユニーク) : {stats['num_generated_valid']}")
    print(f"  Lipinski 適合             : {stats['num_lipinski_pass']}")
    print(f"  平均 Tanimoto 多様性      : {stats['mean_tanimoto_diversity']}")
    print()
    print("  次: cat", stats_path, "|| less", csv_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
