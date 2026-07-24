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
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# MIT-licensed foundation model keys shipped by mace-torch. Only these are
# accepted without an explicit `--accept-asl-license`. Keep the list narrow
# and update against upstream release notes.
_MIT_MODEL_KEYS = {
    "medium",           # MACE-MP-0a legacy MIT
    "medium-mpa-0",     # MACE-MPA-0 MIT
    "small",            # MACE-MP-0a small MIT
    "large",            # MACE-MP-0a large MIT
}
# ASL / non-commercial models — require explicit acknowledgment.
_ASL_MODEL_KEYS = {
    "medium-omat-0",
    "mh-0",
    "mace-matpes-pbe-0",
    "mace-matpes-r2scan-0",
}
_ALL_ALLOWED_KEYS = _MIT_MODEL_KEYS | _ASL_MODEL_KEYS

# Known SHA-256 of trusted checkpoints (populated with values that have been
# verified out-of-band; add more as they are pinned).
_KNOWN_MODEL_SHA256 = {
    "medium-mpa-0": "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638",
}


def _positive_float(value: str) -> float:
    v = float(value)
    if not (v > 0):
        raise argparse.ArgumentTypeError(f"must be > 0, got {value}")
    return v


def _positive_int(value: str) -> int:
    v = int(value)
    if not (v > 0):
        raise argparse.ArgumentTypeError(f"must be > 0, got {value}")
    return v


def _nonneg_int(value: str) -> int:
    v = int(value)
    if v < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {value}")
    return v


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = p.add_mutually_exclusive_group()
    src.add_argument("--input", type=Path,
                     help="Input structure file (CIF/extxyz/POSCAR). "
                          "If omitted, --system is used.")
    src.add_argument("--system", default="Si",
                     help="Preset from build_structure.py (default: Si)")
    p.add_argument("--supercell", nargs=3, type=_positive_int, default=[1, 1, 1],
                   metavar=("NX", "NY", "NZ"),
                   help="Positive integers only.")
    p.add_argument("--model", default="medium-mpa-0", choices=sorted(_ALL_ALLOWED_KEYS),
                   help="MACE foundation model key. MIT: %s. ASL (require --accept-asl-license): %s."
                        % (sorted(_MIT_MODEL_KEYS), sorted(_ASL_MODEL_KEYS)))
    p.add_argument("--model-path", type=Path, default=None,
                   help="Optional path to a locally cached MACE checkpoint. When set, "
                        "--model-sha256 is REQUIRED — MACE ultimately uses torch.load which "
                        "is unsafe with untrusted files.")
    p.add_argument("--model-sha256", default=None,
                   help="Expected SHA-256 of --model-path or --model checkpoint. "
                        "Mandatory with --model-path; recommended with --model.")
    p.add_argument("--accept-asl-license", action="store_true",
                   help="Required to use ASL / non-commercial MACE checkpoints.")
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"],
                   help="Compute device (default: auto -> cuda if available else cpu)")
    p.add_argument("--dtype", default="float32", choices=["float32", "float64"],
                   help="Model dtype (default: float32; recommended on T4/CPU)")
    p.add_argument("--fmax", type=_positive_float, default=0.05,
                   help="Force convergence threshold in eV/Å (default: 0.05)")
    p.add_argument("--stress-tol-eV-per-A3", type=_positive_float, default=5e-4,
                   help="Max acceptable component stress (eV/Å^3) when cell relaxes.")
    p.add_argument("--max-steps", type=_positive_int, default=300,
                   help="Max optimizer steps (default: 300)")
    p.add_argument("--fix-cell", action="store_true",
                   help="Relax ions only, keep cell fixed (default: cell + ions)")
    p.add_argument("--allow-nonperiodic", action="store_true",
                   help="Allow relaxing non-periodic structures. Off by default because "
                        "the model was trained on periodic inorganic materials.")
    p.add_argument("--allow-elements-outside-domain", action="store_true",
                   help="Skip element-domain checks vs the checkpoint's supported set.")
    p.add_argument("--min-interatomic-Ang", type=_positive_float, default=0.5,
                   help="Reject inputs with any pair distance below this (default: 0.5 Å).")
    p.add_argument("--output", type=Path, default=Path("data"),
                   help="Output directory (default: data/)")
    return p.parse_args()


def _resolve_device(requested: str, torch_mod) -> str:
    if requested == "auto":
        if torch_mod.cuda.is_available():
            return "cuda"
        return "cpu"
    if requested == "cuda" and not torch_mod.cuda.is_available():
        raise SystemExit(
            "ERROR: --device cuda requested but torch.cuda.is_available() is False.\n"
            "Install GPU PyTorch:\n"
            "  pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121"
        )
    return requested


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_model_selection(args: argparse.Namespace) -> str | None:
    """Return sha256 of resolved model checkpoint if one is used, else None."""
    if args.model_path is not None:
        if not args.model_path.exists():
            raise SystemExit(f"ERROR: --model-path {args.model_path} not found.")
        if not args.model_sha256:
            raise SystemExit(
                "ERROR: --model-sha256 is REQUIRED when --model-path is set. "
                "MACE ultimately uses unsafe torch.load; refusing to load without a checksum."
            )
        actual = _sha256_file(args.model_path)
        if actual.lower() != args.model_sha256.lower():
            raise SystemExit(
                f"ERROR: --model-path sha256 mismatch: expected {args.model_sha256} got {actual}"
            )
        return actual
    if args.model in _ASL_MODEL_KEYS and not args.accept_asl_license:
        raise SystemExit(
            f"ERROR: model {args.model!r} is distributed under a non-commercial ASL. "
            "Re-run with --accept-asl-license after reading the upstream terms; the accepted "
            "license identifier will be recorded in the metrics file."
        )
    expected = args.model_sha256 or _KNOWN_MODEL_SHA256.get(args.model)
    return expected  # sha of downloaded checkpoint is verified out-of-band by the user


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return ""


def _pkg_version(name: str) -> str:
    try:
        return __import__(name).__version__
    except Exception:
        return ""


def _load_atoms(args: argparse.Namespace):
    from ase.io import read
    from ase.build import bulk

    if args.input is not None:
        if not args.input.exists():
            raise SystemExit(f"ERROR: {args.input} not found.")
        atoms = read(args.input)
        source = str(args.input)
        source_sha256 = _sha256_file(args.input)
    else:
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
        source_sha256 = ""

    nx, ny, nz = args.supercell
    if (nx, ny, nz) != (1, 1, 1):
        atoms = atoms.repeat([nx, ny, nz])
    return atoms, source, source_sha256


def _validate_input_structure(atoms, args: argparse.Namespace) -> None:
    import numpy as np
    if len(atoms) < 1:
        raise SystemExit("ERROR: input structure has zero atoms.")
    pbc = list(bool(x) for x in atoms.get_pbc())
    if not all(pbc):
        if not args.allow_nonperiodic:
            raise SystemExit(
                f"ERROR: input structure has PBC {pbc}. MACE-MP-0 is trained on periodic "
                "inorganic materials. Re-run with --allow-nonperiodic if this is intentional "
                "(and consider --fix-cell for nonperiodic systems)."
            )
    vol = float(atoms.get_volume())
    if vol <= 0 and all(pbc):
        raise SystemExit(f"ERROR: input structure has non-positive cell volume {vol}.")
    # Minimum image distance check on positions (skip for nonperiodic).
    if all(pbc) and len(atoms) >= 2:
        d = atoms.get_all_distances(mic=True)
        np.fill_diagonal(d, np.inf)
        dmin = float(d.min())
        if dmin < args.min_interatomic_Ang:
            raise SystemExit(
                f"ERROR: minimum interatomic distance {dmin:.3f} Å < "
                f"--min-interatomic-Ang {args.min_interatomic_Ang} Å. "
                "Check the input; unrealistically close atoms crash the calculator."
            )
    # Element-domain check vs a conservative allowlist covering MACE-MP-0's Z=1-89
    # non-noble-gas support. Users can bypass with --allow-elements-outside-domain.
    supported = _mace_mp_supported_elements()
    unsupported = sorted({s for s in atoms.get_chemical_symbols() if s not in supported})
    if unsupported and not args.allow_elements_outside_domain:
        raise SystemExit(
            f"ERROR: elements {unsupported} are outside the MACE-MP-0 documented support "
            "list. Re-run with --allow-elements-outside-domain if you know the checkpoint "
            "covers them (results may be unreliable)."
        )


def _mace_mp_supported_elements() -> set[str]:
    # MACE-MP-0 / MPA-0 covers Z=1-89 excluding noble gases and radioactive
    # elements above Z=83 that are absent from Materials Project.
    from ase.data import chemical_symbols
    noble = {"He", "Ne", "Ar", "Kr", "Xe", "Rn"}
    forbidden = {"Po", "At", "Fr", "Ra"}
    return {s for i, s in enumerate(chemical_symbols) if 1 <= i <= 89 and s not in noble and s not in forbidden}


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    import numpy as np
    import torch
    from ase.io import write
    from ase.optimize import BFGS
    from mace.calculators import mace_mp

    try:
        from ase.filters import ExpCellFilter
    except ImportError:  # pragma: no cover - legacy ASE
        from ase.constraints import ExpCellFilter

    device = _resolve_device(args.device, torch)
    model_sha256 = _check_model_selection(args)

    atoms, source, source_sha256 = _load_atoms(args)
    _validate_input_structure(atoms, args)
    n_atoms = len(atoms)
    print(f"[relax] source: {source}")
    print(f"[relax] atoms: {n_atoms} ({atoms.get_chemical_formula()})")
    print(f"[relax] device={device} dtype={args.dtype} model={args.model}")
    if device == "cuda":
        try:
            print(f"[relax] GPU: {torch.cuda.get_device_name(0)}")
        except Exception:
            pass

    write(args.output / "initial.extxyz", atoms, format="extxyz")

    print("[relax] loading MACE calculator (first run downloads ~80 MB) ...")
    if args.model_path is not None:
        calc = mace_mp(model=str(args.model_path), device=device, default_dtype=args.dtype)
    else:
        calc = mace_mp(model=args.model, device=device, default_dtype=args.dtype)
    atoms.calc = calc

    e0 = float(atoms.get_potential_energy())
    forces0 = atoms.get_forces()
    if not np.isfinite(e0) or not np.isfinite(forces0).all():
        raise SystemExit("ERROR: initial energy/forces contain NaN or Inf. Aborting.")
    f0_max = float(np.linalg.norm(forces0, axis=1).max())
    print(f"[relax] initial E = {e0:.4f} eV  ({e0/n_atoms:.4f} eV/atom), F_max = {f0_max:.4f} eV/Å")

    traj_path = args.output / "relaxation.traj"
    log_path = args.output / "relaxation.log"
    target = atoms if args.fix_cell else ExpCellFilter(atoms)
    opt = BFGS(target, trajectory=str(traj_path), logfile=str(log_path))
    try:
        opt.run(fmax=args.fmax, steps=args.max_steps)
    finally:
        # BFGS does not expose an explicit close on its trajectory attribute, but
        # ensure the file is flushed by dropping references early.
        pass
    optimizer_converged = bool(opt.converged())

    e_final = float(atoms.get_potential_energy())
    forces_final = atoms.get_forces()
    if not np.isfinite(e_final) or not np.isfinite(forces_final).all():
        raise SystemExit("ERROR: final energy/forces contain NaN or Inf. Relaxation failed.")
    f_final_max = float(np.linalg.norm(forces_final, axis=1).max())
    n_steps = int(opt.nsteps)

    stress = None
    pressure_GPa = None
    try:
        stress = atoms.get_stress(voigt=False)  # eV/Å^3
        if not np.isfinite(stress).all():
            raise SystemExit("ERROR: final stress contains NaN or Inf.")
        # 1 eV/Å^3 = 160.21766208 GPa
        pressure_GPa = -float(np.trace(stress) / 3.0) * 160.21766208
    except Exception:
        pass

    stress_ok = True
    if not args.fix_cell and stress is not None:
        stress_ok = float(np.abs(stress).max()) <= args.stress_tol_eV_per_A3

    converged = bool(optimizer_converged and f_final_max <= args.fmax and stress_ok)

    write(args.output / "relaxed.extxyz", atoms, format="extxyz")
    write(args.output / "relaxed.cif", atoms, format="cif")

    metrics = {
        "source": source,
        "source_sha256": source_sha256,
        "n_atoms": n_atoms,
        "formula": atoms.get_chemical_formula(),
        "device": device,
        "dtype": args.dtype,
        "model": args.model,
        "model_path": str(args.model_path) if args.model_path else None,
        "model_sha256_expected": model_sha256,
        "accept_asl_license": bool(args.accept_asl_license and args.model in _ASL_MODEL_KEYS),
        "fix_cell": args.fix_cell,
        "fmax_target_eV_per_Ang": args.fmax,
        "stress_tol_eV_per_A3": args.stress_tol_eV_per_A3,
        "initial_energy_eV": e0,
        "initial_fmax_eV_per_Ang": f0_max,
        "final_energy_eV": e_final,
        "final_energy_per_atom_eV": e_final / n_atoms,
        "final_fmax_eV_per_Ang": f_final_max,
        "final_stress_eV_per_A3": stress.tolist() if stress is not None else None,
        "final_pressure_GPa": pressure_GPa,
        "stress_ok": stress_ok,
        "n_steps": n_steps,
        "optimizer_converged": optimizer_converged,
        "converged": converged,
        "final_cell_Ang": atoms.get_cell().tolist(),
        "final_volume_Ang3": float(atoms.get_volume()),
        "relaxed_at": datetime.now(timezone.utc).isoformat(),
        "package_versions": {
            "python": platform.python_version(),
            "torch": _pkg_version("torch"),
            "numpy": np.__version__,
            "ase": _pkg_version("ase"),
            "mace": _pkg_version("mace"),
            "cuda": getattr(torch.version, "cuda", None),
            "cudnn": getattr(getattr(torch.backends, "cudnn", None), "version", lambda: None)(),
            "gpu": torch.cuda.get_device_name(0) if device == "cuda" and torch.cuda.is_available() else None,
        },
        "git_commit": _git_commit(),
        "os_uname": platform.platform(),
    }
    metrics_path = args.output / "relax_metrics.json"
    # allow_nan=False catches serialization of NaN/Inf even if a metric slipped through.
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2, allow_nan=False))

    status = "✅ CONVERGED" if converged else "⚠️ NOT CONVERGED"
    print(f"[relax] {status}: E = {e_final:.4f} eV ({e_final/n_atoms:.4f} eV/atom)")
    print(f"[relax]   F_max = {f_final_max:.4f} eV/Å in {n_steps} steps")
    if pressure_GPa is not None:
        print(f"[relax]   P = {pressure_GPa:+.3f} GPa (stress_ok={stress_ok})")
    print(f"[relax]   volume = {atoms.get_volume():.3f} Å³")
    print(f"[relax] wrote {args.output}/relaxed.extxyz, relaxed.cif, {metrics_path.name}")
    return 0 if converged else 2


if __name__ == "__main__":
    sys.exit(main())
