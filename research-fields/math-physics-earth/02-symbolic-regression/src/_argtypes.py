"""Reusable argparse type validators for train.py."""
from __future__ import annotations
import argparse
import math


def bounded_int(name: str, lo: int, hi: int):
    """Return an argparse type function that validates int in [lo, hi]."""
    def _check(value: str) -> int:
        try:
            v = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"{name} must be an integer, got {value!r}"
            )
        if not (lo <= v <= hi):
            raise argparse.ArgumentTypeError(
                f"{name} must be in [{lo}, {hi}], got {v}"
            )
        return v
    _check.__name__ = name
    return _check


def finite_nonneg_float(name: str):
    """Return an argparse type function that validates finite float >= 0."""
    def _check(value: str) -> float:
        try:
            v = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"{name} must be a number, got {value!r}"
            )
        if not math.isfinite(v):
            raise argparse.ArgumentTypeError(
                f"{name} must be finite, got {value!r}"
            )
        if v < 0:
            raise argparse.ArgumentTypeError(
                f"{name} must be >= 0, got {v}"
            )
        return v
    _check.__name__ = name
    return _check
