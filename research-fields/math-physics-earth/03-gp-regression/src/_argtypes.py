"""CLI argument type validators for train.py (HIGH-3)."""
from __future__ import annotations
import argparse
import math


def bounded_int(lo: int, hi: int):
    """Return an argparse type that accepts integers in [lo, hi]."""
    def _check(v: str) -> int:
        try:
            n = int(v)
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected integer, got {v!r}")
        if not (lo <= n <= hi):
            raise argparse.ArgumentTypeError(f"must be in [{lo}, {hi}], got {n}")
        return n
    _check.__name__ = f"int[{lo},{hi}]"
    return _check


def bounded_float(lo: float, hi: float):
    """Return an argparse type that accepts finite floats in [lo, hi]."""
    def _check(v: str) -> float:
        try:
            x = float(v)
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected float, got {v!r}")
        if not math.isfinite(x):
            raise argparse.ArgumentTypeError(f"must be finite, got {v!r}")
        if not (lo <= x <= hi):
            raise argparse.ArgumentTypeError(f"must be in [{lo}, {hi}], got {x}")
        return x
    _check.__name__ = f"float[{lo},{hi}]"
    return _check


def finite_float(lo: float = -math.inf, hi: float = math.inf):
    """Return an argparse type that accepts finite floats with optional bounds."""
    def _check(v: str) -> float:
        try:
            x = float(v)
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected float, got {v!r}")
        if not math.isfinite(x):
            raise argparse.ArgumentTypeError(f"must be finite, got {v!r}")
        if x < lo:
            raise argparse.ArgumentTypeError(f"must be >= {lo}, got {x}")
        if x > hi:
            raise argparse.ArgumentTypeError(f"must be <= {hi}, got {x}")
        return x
    _check.__name__ = "finite_float"
    return _check


def positive_int(v: str) -> int:
    """Argparse type for positive integers."""
    try:
        n = int(v)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected integer, got {v!r}")
    if n <= 0:
        raise argparse.ArgumentTypeError(f"must be positive, got {n}")
    return n
