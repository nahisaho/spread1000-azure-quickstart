"""Reusable argparse type validators for PINN training scripts."""
from __future__ import annotations

import argparse
import math


def bounded_int(name: str, lo: int, hi: int):
    """Return an argparse type function that validates int in [lo, hi]."""

    def _check(value: str) -> int:
        try:
            v = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} must be an integer, got {value!r}")
        if not (lo <= v <= hi):
            raise argparse.ArgumentTypeError(
                f"{name} must be in [{lo}, {hi}], got {v}"
            )
        return v

    _check.__name__ = f"bounded_int({name},{lo},{hi})"
    return _check


def bounded_float(name: str, lo: float, hi: float):
    """Return an argparse type function that validates float in [lo, hi]."""

    def _check(value: str) -> float:
        try:
            v = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} must be a float, got {value!r}")
        if not (lo <= v <= hi):
            raise argparse.ArgumentTypeError(
                f"{name} must be in [{lo}, {hi}], got {v}"
            )
        return v

    _check.__name__ = f"bounded_float({name},{lo},{hi})"
    return _check


def positive_float(name: str):
    """Return an argparse type function that validates float > 0 and finite."""

    def _check(value: str) -> float:
        try:
            v = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} must be a float, got {value!r}")
        if not math.isfinite(v) or v <= 0:
            raise argparse.ArgumentTypeError(
                f"{name} must be finite and > 0, got {v}"
            )
        return v

    _check.__name__ = f"positive_float({name})"
    return _check


def non_negative_float(name: str):
    """Return an argparse type function that validates float >= 0 and finite."""

    def _check(value: str) -> float:
        try:
            v = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} must be a float, got {value!r}")
        if not math.isfinite(v) or v < 0:
            raise argparse.ArgumentTypeError(
                f"{name} must be finite and >= 0, got {v}"
            )
        return v

    _check.__name__ = f"non_negative_float({name})"
    return _check
