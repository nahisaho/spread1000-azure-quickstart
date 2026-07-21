"""Sample SMILES from a REINVENT4 LibInvent prior using the CLI.

We build a minimal TOML config on the fly (so the caller only needs to pass
`--scaffold` + `--num-smiles`), invoke the `reinvent` CLI, and copy the
sampled CSV to the requested output path.

REINVENT4 v4.8 exposes a `reinvent` console script that reads a TOML
`sampling` config and writes an `output_file` CSV containing the sampled SMILES
plus per-molecule NLL.

Usage:
  python run_libinvent.py \
    --prior /path/to/libinvent.prior \
    --scaffold "Cc1ccc([*:1])cc1[*:2]" \
    --num-smiles 100 \
    --output /mnt/output/sampled.csv
"""
from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


TOML_TEMPLATE = """\
run_type = "sampling"

[parameters]
model_file = "{prior_path}"
smiles_file = "{smiles_file}"
output_file = "{out_csv}"
num_smiles = {num_smiles}
# Keep RAW samples (do NOT let REINVENT filter dupes/invalids); we compute
# valid_ratio / unique_ratio ourselves in score_molecules.py.
unique_molecules = false
randomize_smiles = true
"""


def _build_toml(prior: Path, smiles_file: Path, num_smiles: int,
                out_csv: Path) -> str:
    # Escape backslashes for TOML string literals (POSIX paths should be safe already).
    return TOML_TEMPLATE.format(
        prior_path=str(prior.resolve()).replace("\\", "\\\\"),
        smiles_file=str(smiles_file.resolve()).replace("\\", "\\\\"),
        out_csv=str(out_csv.resolve()).replace("\\", "\\\\"),
        num_smiles=int(num_smiles),
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prior", required=True, type=Path)
    p.add_argument("--scaffold", required=True, help="Scaffold SMILES with [*:1]/[*:2]")
    p.add_argument("--num-smiles", type=int, default=100)
    p.add_argument("--output", required=True, type=Path,
                   help="Where REINVENT should write the sampled CSV")
    args = p.parse_args()

    if not args.prior.is_file():
        logger.error("prior file not found: %s", args.prior)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        # LibInvent expects scaffolds via `smiles_file`, one SMILES per line.
        smiles_file = Path(td) / "scaffolds.smi"
        smiles_file.write_text(args.scaffold.strip() + "\n")

        cfg = Path(td) / "sampling.toml"
        cfg.write_text(_build_toml(args.prior, smiles_file, args.num_smiles,
                                   args.output))
        logger.info("Wrote sampling config: %s", cfg)
        logger.info("Config contents:\n%s", cfg.read_text())

        cmd = ["reinvent", "-l", str(Path(td) / "reinvent.log"), str(cfg)]
        logger.info("Running: %s", " ".join(cmd))
        rc = subprocess.call(cmd)
        if rc != 0:
            logger.error("reinvent CLI failed with exit code %s", rc)
            log_path = Path(td) / "reinvent.log"
            if log_path.exists():
                logger.error("---- reinvent.log ----\n%s", log_path.read_text())
            return rc

    if not args.output.is_file():
        logger.error("reinvent finished but output file is missing: %s", args.output)
        return 1

    n_lines = sum(1 for _ in args.output.open())
    logger.info("✅ Wrote %s (%d lines)", args.output, n_lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
