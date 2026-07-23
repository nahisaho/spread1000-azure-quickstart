"""Short NVT MD with MACE-MP-0 (Langevin thermostat, ASE).

Usage:
    python src/run_md.py --input data/relaxed.extxyz --output data/ --steps 5000

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
    p.add_argument("--input", type=Path, default=Path("data/relaxed.extxyz"),
                   help="Input structure (default: data/relaxed.extxyz)")
    p.add_argument("--output", type=Path, default=Path("data"))
    p.add_argument("--model", default="medium-mpa-0")
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    p.add_argument("--dtype", default="float32", choices=["float32", "float64"])
    p.add_argument("--temperature", type=float, default=300.0,
                   help="Target temperature in K (default: 300)")
    p.add_argument("--timestep-fs", type=float, default=1.0,
                   help="MD timestep in fs (default: 1.0)")
    p.add_argument("--friction-inv-fs", type=float, default=0.01,
                   help="Langevin friction in 1/fs (default: 0.01)")
    p.add_argument("--steps", type=int, default=5000,
                   help="Total MD steps (default: 5000 = 5 ps at dt=1 fs)")
    p.add_argument("--save-every", type=int, default=10,
                   help="Trajectory save interval in steps (default: 10)")
    p.add_argument("--seed", type=int, default=42,
                   help="RNG seed for MaxwellBoltzmannDistribution (default: 42)")
    return p.parse_args()


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

    # Collect all position-freezing constraint classes ASE ships with. Names
    # are looked up dynamically since older ASE releases don't have all of them.
    _freezing_names = ("FixAtoms", "FixScaled", "FixCartesian",
                       "FixedPlane", "FixedLine")
    import ase.constraints as _ase_c
    _freezing_types = tuple(
        getattr(_ase_c, n) for n in _freezing_names if hasattr(_ase_c, n)
    )

    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit(
            "ERROR: --device cuda requested but torch.cuda.is_available() is False."
        )

    atoms = read(args.input)
    n_atoms = len(atoms)
    print(f"[md] loaded {n_atoms} atoms ({atoms.get_chemical_formula()}) from {args.input}")

    print(f"[md] loading MACE calculator ...")
    atoms.calc = mace_mp(model=args.model, device=args.device, default_dtype=args.dtype)

    # Handle center-of-mass drift carefully so that atoms.get_temperature()
    # reports the correct (3N - N_frozen) DoF. Two supported cases:
    #   (a) No position-freezing constraints on input → add FixCom.
    #   (b) Existing position-freezing constraints (FixAtoms/FixScaled/etc.
    #       incl. VASP POSCAR selective dynamics) → keep them, do NOT add
    #       FixCom (would drag frozen atoms).
    # Langevin's fixcm=True is deprecated (does not sample true NVT and is not
    # visible to atoms.get_temperature()), so we always pass fixcm=False.
    existing = list(atoms.constraints or [])
    position_freezing = any(isinstance(c, _freezing_types) for c in existing)
    if position_freezing:
        print("[md] input already has position-freezing constraints; "
              "keeping them and skipping FixCom")
    else:
        if not any(isinstance(c, FixCom) for c in existing):
            atoms.set_constraint(existing + [FixCom()])

    # Validate remaining degrees of freedom (ASE ≥3.23 exposes this helper).
    try:
        n_dof = int(atoms.get_number_of_degrees_of_freedom())
    except AttributeError:  # very old ASE fallback
        n_dof = 3 * n_atoms - (3 if not position_freezing else 0)
    if n_dof <= 0:
        raise SystemExit(
            f"ERROR: input structure has {n_dof} remaining degrees of freedom "
            "after constraints. MD is not meaningful. Increase --supercell or "
            "relax the constraints in the input file."
        )
    print(f"[md] degrees of freedom: {n_dof} (n_atoms={n_atoms})")

    # Initialize velocities to a Maxwell-Boltzmann distribution at target T.
    np.random.seed(args.seed)
    MaxwellBoltzmannDistribution(atoms, temperature_K=args.temperature, rng=np.random)

    dyn = Langevin(
        atoms,
        timestep=args.timestep_fs * units.fs,
        temperature_K=args.temperature,
        friction=args.friction_inv_fs / units.fs,
        fixcm=False,
    )

    # Recorders (populated inside the step-callback).
    temps: list[float] = []
    e_pots: list[float] = []
    e_kins: list[float] = []
    traj_path = args.output / "md.traj"
    traj_writer = Trajectory(str(traj_path), "w", atoms)

    def record() -> None:
        step = dyn.nsteps
        if step % args.save_every == 0:
            traj_writer.write()
            e_pot = float(atoms.get_potential_energy())
            e_kin = float(atoms.get_kinetic_energy())
            # atoms.get_temperature() correctly accounts for constrained DoF
            # (e.g. Langevin's default fixcm=True removes 3 CoM DoF).
            t_inst = float(atoms.get_temperature())
            temps.append(t_inst)
            e_pots.append(e_pot)
            e_kins.append(e_kin)
            if step % (args.save_every * 20) == 0:
                total_time_ps = step * args.timestep_fs / 1000.0
                print(f"[md] step {step:>6d} ({total_time_ps:6.2f} ps) "
                      f"T={t_inst:6.1f} K  E_pot={e_pot:.4f}  E_kin={e_kin:.4f}")

    dyn.attach(record, interval=1)
    dyn.run(args.steps)
    traj_writer.close()

    metrics = {
        "input": str(args.input),
        "n_atoms": n_atoms,
        "formula": atoms.get_chemical_formula(),
        "device": args.device,
        "dtype": args.dtype,
        "model": args.model,
        "temperature_target_K": args.temperature,
        "timestep_fs": args.timestep_fs,
        "friction_inv_fs": args.friction_inv_fs,
        "n_steps": args.steps,
        "total_time_ps": args.steps * args.timestep_fs / 1000.0,
        "save_every": args.save_every,
        "n_frames_saved": len(temps),
        "temperature_mean_K": float(np.mean(temps)) if temps else None,
        "temperature_std_K": float(np.std(temps)) if temps else None,
        "e_pot_mean_eV": float(np.mean(e_pots)) if e_pots else None,
        "e_pot_std_eV": float(np.std(e_pots)) if e_pots else None,
        "e_kin_mean_eV": float(np.mean(e_kins)) if e_kins else None,
        "seed": args.seed,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    metrics_path = args.output / "md_metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"[md] wrote {traj_path} ({len(temps)} frames), {metrics_path.name}")
    if temps:
        print(f"[md] ⟨T⟩ = {metrics['temperature_mean_K']:.1f} ± "
              f"{metrics['temperature_std_K']:.1f} K "
              f"(target {args.temperature:.0f} K)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
