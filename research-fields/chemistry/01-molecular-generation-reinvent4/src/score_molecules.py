"""Score generated SMILES with RDKit + log summary metrics to MLflow.

Reads REINVENT4 sampling output CSV (columns include `SMILES` plus REINVENT
scoring metadata). For each row we:
  1. Parse with RDKit; drop invalid.
  2. Canonicalize (isomeric).
  3. Compute MW, LogP, TPSA, QED, HeavyAtoms.
  4. Compute validity/uniqueness ratios and log to MLflow.

Usage:
  python score_molecules.py \
    --input  /mnt/outputs/sampled.csv \
    --output /mnt/outputs/scored.csv
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import mlflow
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, Crippen, Descriptors, QED

RDLogger.DisableLog("rdApp.*")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


SMILES_COL_CANDIDATES = ["SMILES", "Molecule", "smiles"]


def _find_smiles_col(df: pd.DataFrame) -> str:
    for c in SMILES_COL_CANDIDATES:
        if c in df.columns:
            return c
    raise KeyError(f"No SMILES column found. Columns: {list(df.columns)}")


def _score_row(smi: str) -> dict | None:
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    canonical = Chem.MolToSmiles(mol, isomericSmiles=True, canonical=True)
    try:
        qed = QED.qed(mol)
    except Exception:  # noqa: BLE001
        qed = float("nan")
    return {
        "smiles_canonical": canonical,
        "mw": Descriptors.MolWt(mol),
        "logp": Crippen.MolLogP(mol),
        "tpsa": Descriptors.TPSA(mol),
        "qed": qed,
        "heavy_atoms": mol.GetNumHeavyAtoms(),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    if not args.input.is_file():
        logger.error("input not found: %s", args.input)
        return 2

    df = pd.read_csv(args.input)
    smi_col = _find_smiles_col(df)
    n_total = len(df)
    logger.info("Loaded %d rows from %s (SMILES column: %s)", n_total, args.input, smi_col)

    scored_rows = []
    for idx, smi in enumerate(df[smi_col].astype(str)):
        info = _score_row(smi)
        if info is None:
            continue
        info["_idx"] = idx
        info["smiles_input"] = smi
        scored_rows.append(info)

    if not scored_rows:
        logger.error("No valid molecules parsed. Check reinvent output.")
        return 1

    scored = pd.DataFrame(scored_rows)
    n_valid = len(scored)
    n_unique = scored["smiles_canonical"].nunique()
    valid_ratio = n_valid / max(n_total, 1)
    unique_ratio = n_unique / max(n_valid, 1)  # among valid

    scored.to_csv(args.output, index=False)
    logger.info("Wrote %s (%d valid, %d unique)", args.output, n_valid, n_unique)

    # MLflow logging (best-effort; explicit failure so novice sees the problem)
    mlflow.log_metric("n_total", float(n_total))
    mlflow.log_metric("n_valid", float(n_valid))
    mlflow.log_metric("n_unique", float(n_unique))
    mlflow.log_metric("valid_ratio", float(valid_ratio))
    mlflow.log_metric("unique_ratio", float(unique_ratio))
    mlflow.log_metric("mean_qed", float(scored["qed"].mean()))
    mlflow.log_metric("mean_mw", float(scored["mw"].mean()))
    mlflow.log_metric("mean_logp", float(scored["logp"].mean()))
    logger.info("MLflow metrics logged.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
