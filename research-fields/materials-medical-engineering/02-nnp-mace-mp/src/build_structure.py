"""Build a bulk crystal structure with ASE and save as extxyz.

Uses `ase.build.bulk()` — no third-party data required, fully reproducible.

Usage:
    python src/build_structure.py --system Si --supercell 1 1 1 --output data/initial.extxyz
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# Curated presets: system name -> (crystal structure, lattice param Å, cubic?)
# cubic=True is preferred so all presets yield >= 2 atoms per cell, which is
# required for MD after FixCom is applied.
PRESETS: dict[str, tuple[str, float, bool]] = {
    "Si":   ("diamond",  5.431, True),   # 8-atom conventional cell
    "Ge":   ("diamond",  5.658, True),   # 8-atom conventional cell
    "NaCl": ("rocksalt", 5.640, True),   # 8-atom conventional cell
    "Cu":   ("fcc",      3.615, True),   # 4-atom conventional cell
    "Al":   ("fcc",      4.050, True),   # 4-atom conventional cell
    "Fe":   ("bcc",      2.870, True),   # 2-atom conventional cell
}


def _positive_int(value: str) -> int:
    v = int(value)
    if not (v > 0):
        raise argparse.ArgumentTypeError(f"must be > 0, got {value}")
    return v


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--system", default="Si", choices=list(PRESETS.keys()),
                   help="Preset crystal system (default: Si)")
    p.add_argument("--supercell", nargs=3, type=_positive_int, default=[1, 1, 1],
                   metavar=("NX", "NY", "NZ"),
                   help="Supercell multipliers (positive integers, default: 1 1 1)")
    p.add_argument("--output", type=Path, default=Path("data/initial.extxyz"))
    return p.parse_args()


def main() -> int:
    args = parse_args()

    from ase.build import bulk
    from ase.io import write

    crystal, a, cubic = PRESETS[args.system]
    atoms = bulk(args.system, crystalstructure=crystal, a=a, cubic=cubic)
    nx, ny, nz = args.supercell
    if (nx, ny, nz) != (1, 1, 1):
        atoms = atoms.repeat([nx, ny, nz])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, atoms, format="extxyz")

    print(f"[build] {args.system} {crystal} a={a} Å")
    print(f"[build] supercell {nx}×{ny}×{nz} → {len(atoms)} atoms")
    print(f"[build] wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
