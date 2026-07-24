"""Fail-hard verification for D-2 MACE-MP relaxation/MD outputs.

Usage:
    # Verify relaxation output only
    python src/verify.py --relax data/relax_metrics.json

    # Verify MD output only
    python src/verify.py --md data/md_metrics.json

    # Verify both (typical after the quickstart flow)
    python src/verify.py --relax data/relax_metrics.json --md data/md_metrics.json \
        --expected-lattice-a-Ang 5.43 --lattice-tol 0.05

Exit codes:
    0 — all checks passed
    1 — one or more checks failed (details on stderr)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--relax", type=Path, default=None,
                   help="Path to data/relax_metrics.json")
    p.add_argument("--md", type=Path, default=None,
                   help="Path to data/md_metrics.json")
    p.add_argument("--expected-lattice-a-Ang", type=float, default=None,
                   help="Reference conventional-cell lattice a (Å) for the relaxed structure.")
    p.add_argument("--lattice-tol", type=float, default=0.05,
                   help="Relative tolerance on lattice a (default: 5%).")
    p.add_argument("--temperature-tol-K", type=float, default=30.0,
                   help="Max |⟨T⟩ - target_T| in K (default: 30).")
    p.add_argument("--e-drift-tol-eV-per-atom", type=float, default=0.01,
                   help="Max acceptable |E_pot std| per atom in eV (default: 0.01).")
    p.add_argument("--reference-checkpoint-sha256", default=None,
                   help="If given, the model_sha256_expected recorded in the metrics "
                        "must equal this value.")
    return p.parse_args()


def _fail(msg: str, failures: list[str]) -> None:
    print(f"[verify] FAIL: {msg}", file=sys.stderr)
    failures.append(msg)


def verify_relax(path: Path, args: argparse.Namespace, failures: list[str]) -> None:
    if not path.exists():
        _fail(f"relax metrics not found: {path}", failures)
        return
    m = json.loads(path.read_text())

    for k in ("final_energy_eV", "final_fmax_eV_per_Ang", "final_volume_Ang3",
              "final_energy_per_atom_eV", "n_atoms", "converged"):
        if k not in m:
            _fail(f"{path.name} missing key {k!r}", failures)
            return

    # 1. Convergence flag.
    if not m["converged"]:
        _fail(f"{path.name}: converged=False (F_max={m.get('final_fmax_eV_per_Ang')})", failures)

    # 2. Finite outputs.
    for k in ("final_energy_eV", "final_energy_per_atom_eV", "final_fmax_eV_per_Ang",
              "final_volume_Ang3"):
        v = m[k]
        if not (isinstance(v, (int, float)) and math.isfinite(v)):
            _fail(f"{path.name}: non-finite {k}={v!r}", failures)

    # 3. Positive volume.
    if float(m["final_volume_Ang3"]) <= 0:
        _fail(f"{path.name}: non-positive final_volume_Ang3={m['final_volume_Ang3']}", failures)

    # 4. Optional lattice sanity: recover conventional 'a' from cell.
    if args.expected_lattice_a_Ang is not None and "final_cell_Ang" in m:
        cell = m["final_cell_Ang"]
        try:
            a = sum((cell[0][i] ** 2 for i in range(3))) ** 0.5
        except Exception:
            _fail(f"{path.name}: malformed final_cell_Ang", failures)
            return
        rel = abs(a - args.expected_lattice_a_Ang) / args.expected_lattice_a_Ang
        if rel > args.lattice_tol:
            _fail(f"{path.name}: |a_final - a_ref|/a_ref={rel:.4f} exceeds tolerance "
                  f"{args.lattice_tol} (a_final={a:.4f}, a_ref={args.expected_lattice_a_Ang})",
                  failures)

    # 5. Stress check if reported.
    if not m.get("stress_ok", True):
        _fail(f"{path.name}: stress_ok=False (final_pressure_GPa={m.get('final_pressure_GPa')})",
              failures)

    # 6. Reproducibility manifest.
    for k in ("package_versions", "git_commit"):
        if k not in m:
            _fail(f"{path.name}: missing reproducibility key {k!r}", failures)

    _check_reference_ckpt(m, path.name, args, failures)


def verify_md(path: Path, args: argparse.Namespace, failures: list[str]) -> None:
    if not path.exists():
        _fail(f"MD metrics not found: {path}", failures)
        return
    m = json.loads(path.read_text())

    for k in ("temperature_mean_K", "temperature_std_K",
              "e_pot_mean_eV", "e_pot_std_eV", "n_atoms",
              "temperature_target_K", "n_frames_saved_production"):
        if k not in m:
            _fail(f"{path.name} missing key {k!r}", failures)
            return

    n_frames = int(m["n_frames_saved_production"])
    if n_frames <= 0:
        _fail(f"{path.name}: no production frames recorded", failures)
        return

    # 1. Finite production statistics.
    for k in ("temperature_mean_K", "temperature_std_K", "e_pot_mean_eV",
              "e_pot_std_eV", "e_kin_mean_eV"):
        v = m.get(k)
        if v is None or not math.isfinite(v):
            _fail(f"{path.name}: non-finite {k}={v!r}", failures)

    # 2. Temperature within tolerance of target (production only).
    t_target = float(m["temperature_target_K"])
    t_mean = float(m["temperature_mean_K"])
    if abs(t_mean - t_target) > args.temperature_tol_K:
        _fail(f"{path.name}: |⟨T⟩ - target|={abs(t_mean - t_target):.1f} K > "
              f"{args.temperature_tol_K} K tolerance (⟨T⟩={t_mean:.1f}, target={t_target:.1f})",
              failures)

    # 3. Bounded energy drift per atom.
    n_atoms = int(m["n_atoms"])
    e_std = float(m["e_pot_std_eV"])
    per_atom = e_std / max(n_atoms, 1)
    if per_atom > args.e_drift_tol_eV_per_atom:
        _fail(f"{path.name}: E_pot std/atom={per_atom:.5f} eV > "
              f"{args.e_drift_tol_eV_per_atom} eV tolerance (n_atoms={n_atoms})",
              failures)

    # 4. Reproducibility manifest.
    for k in ("package_versions", "git_commit", "seed"):
        if k not in m:
            _fail(f"{path.name}: missing reproducibility key {k!r}", failures)

    _check_reference_ckpt(m, path.name, args, failures)


def _check_reference_ckpt(m: dict, label: str, args: argparse.Namespace, failures: list[str]) -> None:
    if args.reference_checkpoint_sha256:
        expected = m.get("model_sha256_expected")
        if not expected:
            _fail(f"{label}: --reference-checkpoint-sha256 requested but metrics has no "
                  "'model_sha256_expected'", failures)
        elif expected.lower() != args.reference_checkpoint_sha256.lower():
            _fail(f"{label}: model_sha256_expected={expected} != "
                  f"--reference-checkpoint-sha256={args.reference_checkpoint_sha256}", failures)


def main() -> int:
    args = parse_args()
    if args.relax is None and args.md is None:
        raise SystemExit("ERROR: pass --relax and/or --md (at least one is required).")

    failures: list[str] = []
    if args.relax is not None:
        verify_relax(args.relax, args, failures)
    if args.md is not None:
        verify_md(args.md, args, failures)

    if failures:
        print(f"[verify] {len(failures)} failure(s).", file=sys.stderr)
        return 1
    print("[verify] OK: all checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
