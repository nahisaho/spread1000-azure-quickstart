"""Short NVT MD with MACE-MP-0 (Langevin thermostat, ASE).

Usage:
    python src/run_md.py --input data/relaxed.extxyz --output data/ --steps 5000

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

# Kept aligned with relax.py — see comments there.
_MIT_MODEL_KEYS = {"medium", "medium-mpa-0", "small", "large"}
_ASL_MODEL_KEYS = {"medium-omat-0", "mh-0", "mace-matpes-pbe-0", "mace-matpes-r2scan-0"}
_ALL_ALLOWED_KEYS = _MIT_MODEL_KEYS | _ASL_MODEL_KEYS

# Safety cap on total simulated time (ps) unless --allow-long-run is set.
_DEFAULT_LONG_RUN_LIMIT_PS = 100.0


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


def _nonneg_float(value: str) -> float:
    v = float(value)
    if v < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {value}")
    return v


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", type=Path, default=Path("data/relaxed.extxyz"),
                   help="Input structure (default: data/relaxed.extxyz)")
    p.add_argument("--output", type=Path, default=Path("data"))
    p.add_argument("--model", default="medium-mpa-0", choices=sorted(_ALL_ALLOWED_KEYS))
    p.add_argument("--model-path", type=Path, default=None,
                   help="Optional locally cached MACE checkpoint. Requires --model-sha256.")
    p.add_argument("--model-sha256", default=None,
                   help="Expected SHA-256 of --model-path. Mandatory with --model-path.")
    p.add_argument("--accept-asl-license", action="store_true",
                   help="Required for ASL / non-commercial MACE checkpoints.")
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    p.add_argument("--dtype", default="float32", choices=["float32", "float64"])
    p.add_argument("--temperature", type=_nonneg_float, default=300.0,
                   help="Target temperature in K (default: 300)")
    p.add_argument("--timestep-fs", type=_positive_float, default=1.0,
                   help="MD timestep in fs (default: 1.0)")
    p.add_argument("--friction-inv-fs", type=_positive_float, default=0.01,
                   help="Langevin friction in 1/fs (default: 0.01)")
    p.add_argument("--steps", type=_positive_int, default=5000,
                   help="Total production MD steps (default: 5000 = 5 ps at dt=1 fs). "
                        "Equilibration is separate and not counted in --steps.")
    p.add_argument("--equilibration-steps", type=_nonneg_int, default=1000,
                   help="Steps to run BEFORE reset+production recording (default: 1000).")
    p.add_argument("--save-every", type=_positive_int, default=10,
                   help="Trajectory save interval in production steps (default: 10)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--allow-long-run", action="store_true",
                   help=f"Required to run more than {_DEFAULT_LONG_RUN_LIMIT_PS} ps of production MD.")
    return p.parse_args()


def _resolve_device(requested: str, torch_mod) -> str:
    if requested == "auto":
        return "cuda" if torch_mod.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch_mod.cuda.is_available():
        raise SystemExit("ERROR: --device cuda requested but torch.cuda.is_available() is False.")
    return requested


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_model_selection(args: argparse.Namespace) -> str | None:
    if args.model_path is not None:
        if not args.model_path.exists():
            raise SystemExit(f"ERROR: --model-path {args.model_path} not found.")
        if not args.model_sha256:
            raise SystemExit(
                "ERROR: --model-sha256 is REQUIRED with --model-path (torch.load is unsafe)."
            )
        actual = _sha256_file(args.model_path)
        if actual.lower() != args.model_sha256.lower():
            raise SystemExit(f"ERROR: --model-path sha256 mismatch: expected {args.model_sha256} got {actual}")
        return actual
    if args.model in _ASL_MODEL_KEYS and not args.accept_asl_license:
        raise SystemExit(
            f"ERROR: model {args.model!r} is ASL / non-commercial. Re-run with --accept-asl-license "
            "after reading upstream terms."
        )
    return args.model_sha256


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return ""


def _pkg_version(name: str) -> str:
    try:
        return __import__(name).__version__
    except Exception:
        return ""


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    if not args.input.exists():
        raise SystemExit(
            f"ERROR: {args.input} not found. Run src/relax.py first "
            "or point --input at your own structure."
        )

    import numpy as np
    import torch
    from ase import units
    from ase.constraints import FixCom
    from ase.io import read
    from ase.io.trajectory import Trajectory
    from ase.md.langevin import Langevin
    from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
    from mace.calculators import mace_mp

    _freezing_names = ("FixAtoms", "FixScaled", "FixCartesian",
                       "FixedPlane", "FixedLine")
    import ase.constraints as _ase_c
    _freezing_types = tuple(
        getattr(_ase_c, n) for n in _freezing_names if hasattr(_ase_c, n)
    )

    device = _resolve_device(args.device, torch)
    model_sha256 = _check_model_selection(args)

    # Cost guard: refuse very long production runs unless explicitly allowed.
    prod_ps = args.steps * args.timestep_fs / 1000.0
    if prod_ps > _DEFAULT_LONG_RUN_LIMIT_PS and not args.allow_long_run:
        raise SystemExit(
            f"ERROR: production MD is {prod_ps:.1f} ps > {_DEFAULT_LONG_RUN_LIMIT_PS} ps limit.\n"
            "Refusing to run to prevent unexpected GPU cost. Rough T4 estimate: "
            "10 ns → ~83–167 GPU-hours (~$59–$119). Re-run with --allow-long-run to acknowledge."
        )
    saved_frames = args.steps // args.save_every
    print(f"[md] planned: {args.steps} production steps ({prod_ps:.2f} ps), "
          f"{saved_frames} saved frames (+1 initial); equilibration={args.equilibration_steps} steps")

    input_sha = _sha256_file(args.input)
    atoms = read(args.input)
    n_atoms = len(atoms)
    if n_atoms < 1:
        raise SystemExit("ERROR: input structure has zero atoms.")
    print(f"[md] loaded {n_atoms} atoms ({atoms.get_chemical_formula()}) from {args.input}")

    print(f"[md] loading MACE calculator ...")
    if args.model_path is not None:
        atoms.calc = mace_mp(model=str(args.model_path), device=device, default_dtype=args.dtype)
    else:
        atoms.calc = mace_mp(model=args.model, device=device, default_dtype=args.dtype)

    existing = list(atoms.constraints or [])
    position_freezing = any(isinstance(c, _freezing_types) for c in existing)
    if position_freezing:
        print("[md] input already has position-freezing constraints; keeping them and skipping FixCom")
    else:
        if not any(isinstance(c, FixCom) for c in existing):
            atoms.set_constraint(existing + [FixCom()])

    try:
        n_dof = int(atoms.get_number_of_degrees_of_freedom())
    except AttributeError:
        n_dof = 3 * n_atoms - (3 if not position_freezing else 0)
    if n_dof <= 0:
        raise SystemExit(f"ERROR: input structure has {n_dof} remaining degrees of freedom.")
    print(f"[md] degrees of freedom: {n_dof} (n_atoms={n_atoms})")

    np.random.seed(args.seed)
    MaxwellBoltzmannDistribution(atoms, temperature_K=args.temperature, rng=np.random)

    dyn = Langevin(
        atoms,
        timestep=args.timestep_fs * units.fs,
        temperature_K=args.temperature,
        friction=args.friction_inv_fs / units.fs,
        fixcm=False,
    )

    # Equilibration (no recording).
    if args.equilibration_steps > 0:
        print(f"[md] equilibrating for {args.equilibration_steps} steps ...")

        # Check finite values periodically during equilibration too.
        def _eq_finite_check() -> None:
            if dyn.nsteps % max(1, args.equilibration_steps // 10) == 0:
                if not np.isfinite(atoms.get_positions()).all():
                    raise SystemExit("ERROR: NaN/Inf in positions during equilibration.")

        dyn.attach(_eq_finite_check, interval=1)
        try:
            dyn.run(args.equilibration_steps)
        except Exception:
            raise
        # Detach equilibration callback
        try:
            dyn.observers = [o for o in dyn.observers if o[0] is not _eq_finite_check]
        except Exception:
            pass

    # Production recorders.
    temps: list[float] = []
    e_pots: list[float] = []
    e_kins: list[float] = []
    traj_path = args.output / "md.traj"
    traj_writer = Trajectory(str(traj_path), "w", atoms)
    prod_start_step = dyn.nsteps

    def record() -> None:
        prod_step = dyn.nsteps - prod_start_step
        # Fail-fast on NaN/Inf every step (cheap; positions/energies are already computed).
        pos = atoms.get_positions()
        if not np.isfinite(pos).all():
            raise SystemExit(f"ERROR: NaN/Inf in positions at production step {prod_step}. Aborting.")
        if prod_step % args.save_every == 0:
            traj_writer.write()
            e_pot = float(atoms.get_potential_energy())
            e_kin = float(atoms.get_kinetic_energy())
            if not (np.isfinite(e_pot) and np.isfinite(e_kin)):
                raise SystemExit(f"ERROR: NaN/Inf in energies at production step {prod_step}.")
            t_inst = float(atoms.get_temperature())
            if not np.isfinite(t_inst):
                raise SystemExit(f"ERROR: NaN temperature at production step {prod_step}.")
            temps.append(t_inst)
            e_pots.append(e_pot)
            e_kins.append(e_kin)
            if prod_step % (args.save_every * 20) == 0:
                total_time_ps = prod_step * args.timestep_fs / 1000.0
                print(f"[md] step {prod_step:>6d} ({total_time_ps:6.2f} ps) "
                      f"T={t_inst:6.1f} K  E_pot={e_pot:.4f}  E_kin={e_kin:.4f}")

    dyn.attach(record, interval=1)
    try:
        dyn.run(args.steps)
    finally:
        traj_writer.close()

    metrics = {
        "input": str(args.input),
        "input_sha256": input_sha,
        "n_atoms": n_atoms,
        "formula": atoms.get_chemical_formula(),
        "device": device,
        "dtype": args.dtype,
        "model": args.model,
        "model_path": str(args.model_path) if args.model_path else None,
        "model_sha256_expected": model_sha256,
        "accept_asl_license": bool(args.accept_asl_license and args.model in _ASL_MODEL_KEYS),
        "temperature_target_K": args.temperature,
        "timestep_fs": args.timestep_fs,
        "friction_inv_fs": args.friction_inv_fs,
        "equilibration_steps": args.equilibration_steps,
        "n_steps_production": args.steps,
        "total_production_time_ps": prod_ps,
        "save_every": args.save_every,
        "n_frames_saved_production": len(temps),
        "ensemble": "fixed-cell NVT (Langevin) — production statistics only, "
                    "does NOT include equilibration.",
        "temperature_mean_K": float(np.mean(temps)) if temps else None,
        "temperature_std_K": float(np.std(temps)) if temps else None,
        "e_pot_mean_eV": float(np.mean(e_pots)) if e_pots else None,
        "e_pot_std_eV": float(np.std(e_pots)) if e_pots else None,
        "e_kin_mean_eV": float(np.mean(e_kins)) if e_kins else None,
        "seed": args.seed,
        "finished_at": datetime.now(timezone.utc).isoformat(),
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
    metrics_path = args.output / "md_metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2, allow_nan=False))
    print(f"[md] wrote {traj_path} ({len(temps)} frames), {metrics_path.name}")
    if temps:
        print(f"[md] ⟨T⟩ = {metrics['temperature_mean_K']:.1f} ± "
              f"{metrics['temperature_std_K']:.1f} K "
              f"(target {args.temperature:.0f} K, production only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
