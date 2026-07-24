"""CLI argument type validators for analyze.py."""
from __future__ import annotations

import argparse
import math


def bounded_float(lo: float, hi: float, allow_lo: bool = False) -> callable:
    """Return an argparse type that validates a finite float in (lo, hi] or [lo, hi]."""
    def _validate(value: str) -> float:
        try:
            v = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected float, got {value!r}")
        if not math.isfinite(v):
            raise argparse.ArgumentTypeError(f"value must be finite, got {v}")
        lower_ok = (v >= lo) if allow_lo else (v > lo)
        if not (lower_ok and v <= hi):
            lo_bracket = "[" if allow_lo else "("
            raise argparse.ArgumentTypeError(
                f"value {v} out of range {lo_bracket}{lo}, {hi}]"
            )
        return v
    return _validate


def bounded_int(lo: int, hi: int) -> callable:
    """Return an argparse type that validates an integer in [lo, hi]."""
    def _validate(value: str) -> int:
        try:
            v = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected int, got {value!r}")
        if not (lo <= v <= hi):
            raise argparse.ArgumentTypeError(
                f"value {v} out of range [{lo}, {hi}]"
            )
        return v
    return _validate


def finite_float(value: str) -> float:
    """Argparse type: finite float (no nan/inf)."""
    try:
        v = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected float, got {value!r}")
    if not math.isfinite(v):
        raise argparse.ArgumentTypeError(f"value must be finite, got {v}")
    return v
