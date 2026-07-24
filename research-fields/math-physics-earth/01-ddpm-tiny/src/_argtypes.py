"""Argument type factories for bounded integer validation (HIGH 5)."""
from __future__ import annotations

import argparse


def bounded_int(name: str, lo: int, hi: int):
    """Return an argparse ``type`` callable that enforces ``lo <= value <= hi``."""
    def _check(value: str) -> int:
        n = int(value)
        if n < lo or n > hi:
            raise argparse.ArgumentTypeError(
                f"--{name} must be in [{lo}, {hi}], got {n}"
            )
        return n
    _check.__name__ = f"bounded_int_{name}"
    return _check
