"""Render top-K scored molecules to a single grid PNG using RDKit.

Selects the top-K by QED (descending) among scored rows, deduplicates by
canonical SMILES, and produces a 2D depiction grid.

Usage:
  python render_topk.py \
    --input  /mnt/outputs/scored.csv \
    --output /mnt/outputs/top20.png \
    --top-k 20
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import Draw

RDLogger.DisableLog("rdApp.*")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--top-k", type=int, default=20)
    p.add_argument("--sort-by", default="qed", choices=["qed", "logp", "mw"])
    args = p.parse_args()

    if not args.input.is_file():
        logger.error("input not found: %s", args.input)
        return 2

    df = pd.read_csv(args.input)
    for col in ("smiles_canonical", args.sort_by):
        if col not in df.columns:
            logger.error("expected column '%s' missing (found %s)", col, list(df.columns))
            return 1

    # Dedup by canonical SMILES, then top-K by sort key desc.
    df = df.drop_duplicates(subset=["smiles_canonical"])
    df = df.sort_values(args.sort_by, ascending=False).head(args.top_k).reset_index(drop=True)
    logger.info("Selected %d molecules by %s", len(df), args.sort_by)

    mols = []
    legends = []
    for _, row in df.iterrows():
        mol = Chem.MolFromSmiles(row["smiles_canonical"])
        if mol is None:
            continue
        mols.append(mol)
        legends.append(f"QED={row.get('qed', float('nan')):.2f} "
                       f"MW={row.get('mw', float('nan')):.0f}")

    if not mols:
        logger.error("No renderable molecules found.")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    img = Draw.MolsToGridImage(
        mols,
        molsPerRow=5,
        subImgSize=(300, 300),
        legends=legends,
        useSVG=False,
    )
    img.save(str(args.output))
    logger.info("✅ Wrote %s", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
