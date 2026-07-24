"""Argument type validators for argparse (HIGH-3)."""
from __future__ import annotations

import argparse
import math


def positive_int(name: str = "value"):
    """Return an argparse type that accepts integers > 0."""
    def _check(v: str) -> int:
        try:
            iv = int(v)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name}: expected int, got {v!r}")
        if iv <= 0:
            raise argparse.ArgumentTypeError(f"{name}: must be > 0, got {iv}")
        return iv
    _check.__name__ = f"positive_int({name})"
    return _check


def positive_float(name: str = "value"):
    """Return an argparse type that accepts finite floats > 0."""
    def _check(v: str) -> float:
        fv = finite_float(name)(v)
        if fv <= 0:
            raise argparse.ArgumentTypeError(f"{name}: must be > 0, got {fv}")
        return fv
    _check.__name__ = f"positive_float({name})"
    return _check


def bounded_int(name: str, lo: int, hi: int):
    """Return an argparse type that accepts integers in [lo, hi]."""
    def _check(v: str) -> int:
        try:
            iv = int(v)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name}: expected int, got {v!r}")
        if not (lo <= iv <= hi):
            raise argparse.ArgumentTypeError(
                f"{name}: must be in [{lo}, {hi}], got {iv}"
            )
        return iv
    _check.__name__ = f"bounded_int({name},{lo},{hi})"
    return _check


def finite_float(name: str = "value"):
    """Return an argparse type that accepts finite (non-NaN, non-inf) floats."""
    def _check(v: str) -> float:
        try:
            fv = float(v)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name}: expected float, got {v!r}")
        if not math.isfinite(fv):
            raise argparse.ArgumentTypeError(f"{name}: must be finite, got {fv}")
        return fv
    _check.__name__ = f"finite_float({name})"
    return _check
