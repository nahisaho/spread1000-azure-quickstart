"""Structure relaxation with MACE-MP-0 (MACE-MPA-0, MIT).

Auto-downloads the ~80 MB checkpoint to ~/.cache/mace/ on first run.

Usage:
    # From a system preset (recommended for first run):
    python src/relax.py --system Si --supercell 1 1 1 --output data/

    # From a user-supplied structure file (CIF/extxyz/POSCAR):
    python src/relax.py --input my_structure.cif --output data/

Requires:
    torch==2.4.0, mace-torch>=0.3.16, ase>=3.23
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = p.add_mutually_exclusive_group()
    src.add_argument("--input", type=Path,
                     help="Input structure file (CIF/extxyz/POSCAR). "
                          "If omitted, --system is used.")
    src.add_argument("--system", default="Si",
                     help="Preset from build_structure.py (default: Si)")
    p.add_argument("--supercell", nargs=3, type=int, default=[1, 1, 1],
                   metavar=("NX", "NY", "NZ"))
    p.add_argument("--model", default="medium-mpa-0",
                   help="MACE model key (default: medium-mpa-0 = MACE-MPA-0, MIT). "
                        "Use 'medium' for legacy MACE-MP-0a.")
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda"],
                   help="Compute device (default: cpu)")
    p.add_argument("--dtype", default="float32", choices=["float32", "float64"],
                   help="Model dtype (default: float32; recommended on T4/CPU)")
    p.add_argument("--fmax", type=float, default=0.05,
                   help="Force convergence threshold in eV/Å (default: 0.05)")
    p.add_argument("--max-steps", type=int, default=300,
                   help="Max optimizer steps (default: 300)")
    p.add_argument("--fix-cell", action="store_true",
                   help="Relax ions only, keep cell fixed (default: cell + ions)")
    p.add_argument("--output", type=Path, default=Path("data"),
                   help="Output directory (default: data/)")
    return p.parse_args()


def _load_atoms(args: argparse.Namespace):
    from ase.io import read
    from ase.build import bulk

    if args.input is not None:
        if not args.input.exists():
            raise SystemExit(f"ERROR: {args.input} not found.")
        atoms = read(args.input)
        source = str(args.input)
    else:
        # Import preset table from build_structure.py to keep single source of truth.
        sys.path.insert(0, str(Path(__file__).parent))
        from build_structure import PRESETS
        if args.system not in PRESETS:
            raise SystemExit(
                f"ERROR: unknown --system '{args.system}'. "
                f"Choose from: {list(PRESETS.keys())} or use --input."
            )
        crystal, a, cubic = PRESETS[args.system]
        atoms = bulk(args.system, crystalstructure=crystal, a=a, cubic=cubic)
        source = f"preset:{args.system}({crystal},a={a})"

    nx, ny, nz = args.supercell
    if (nx, ny, nz) != (1, 1, 1):
        atoms = atoms.repeat([nx, ny, nz])
    return atoms, source


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    import numpy as np
    import torch
    from ase.io import write
    from ase.optimize import BFGS
    from mace.calculators import mace_mp

    # ExpCellFilter moved from ase.constraints to ase.filters in ASE 3.23+.
    try:
        from ase.filters import ExpCellFilter
    except ImportError:  # pragma: no cover - legacy ASE
        from ase.constraints import ExpCellFilter

    # Validate CUDA availability if requested.
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit(
            "ERROR: --device cuda requested but torch.cuda.is_available() is False. "
            "Install GPU PyTorch:\n"
            "  pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121"
        )

    atoms, source = _load_atoms(args)
    n_atoms = len(atoms)
    print(f"[relax] source: {source}")
    print(f"[relax] atoms: {n_atoms} ({atoms.get_chemical_formula()})")
    print(f"[relax] device={args.device} dtype={args.dtype} model={args.model}")

    # Save initial structure for reference.
    write(args.output / "initial.extxyz", atoms, format="extxyz")

    print("[relax] loading MACE calculator (first run downloads ~80 MB) ...")
    calc = mace_mp(model=args.model, device=args.device, default_dtype=args.dtype)
    atoms.calc = calc

    e0 = float(atoms.get_potential_energy())
    f0_max = float(np.linalg.norm(atoms.get_forces(), axis=1).max())
    print(f"[relax] initial E = {e0:.4f} eV  ({e0/n_atoms:.4f} eV/atom), F_max = {f0_max:.4f} eV/Å")

    traj_path = args.output / "relaxation.traj"
    log_path = args.output / "relaxation.log"
    target = atoms if args.fix_cell else ExpCellFilter(atoms)
    opt = BFGS(target, trajectory=str(traj_path), logfile=str(log_path))
    opt.run(fmax=args.fmax, steps=args.max_steps)
    optimizer_converged = bool(opt.converged())

    # After optimization, forces belong to the underlying atoms object.
    # Use per-atom force magnitude (norm), not per-component max.
    e_final = float(atoms.get_potential_energy())
    forces_final = atoms.get_forces()
    f_final_max = float(np.linalg.norm(forces_final, axis=1).max())
    n_steps = int(opt.nsteps)
    converged = bool(optimizer_converged and f_final_max <= args.fmax)

    write(args.output / "relaxed.extxyz", atoms, format="extxyz")
    write(args.output / "relaxed.cif", atoms, format="cif")

    metrics = {
        "source": source,
        "n_atoms": n_atoms,
        "formula": atoms.get_chemical_formula(),
        "device": args.device,
        "dtype": args.dtype,
        "model": args.model,
        "fix_cell": args.fix_cell,
        "fmax_target_eV_per_Ang": args.fmax,
        "initial_energy_eV": e0,
        "initial_fmax_eV_per_Ang": f0_max,
        "final_energy_eV": e_final,
        "final_energy_per_atom_eV": e_final / n_atoms,
        "final_fmax_eV_per_Ang": f_final_max,
        "n_steps": n_steps,
        "converged": converged,
        "final_cell_Ang": atoms.get_cell().tolist(),
        "final_volume_Ang3": float(atoms.get_volume()),
        "relaxed_at": datetime.now(timezone.utc).isoformat(),
    }
    metrics_path = args.output / "relax_metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2))

    status = "✅ CONVERGED" if converged else "⚠️ NOT CONVERGED"
    print(f"[relax] {status}: E = {e_final:.4f} eV ({e_final/n_atoms:.4f} eV/atom)")
    print(f"[relax]   F_max = {f_final_max:.4f} eV/Å in {n_steps} steps")
    print(f"[relax]   volume = {atoms.get_volume():.3f} Å³")
    print(f"[relax] wrote {args.output}/relaxed.extxyz, relaxed.cif, {metrics_path.name}")
    return 0 if converged else 2


if __name__ == "__main__":
    sys.exit(main())
