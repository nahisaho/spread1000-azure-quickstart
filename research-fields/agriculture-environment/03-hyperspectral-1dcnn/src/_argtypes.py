"""CLI argument-type validators (HIGH 4).

Usage in argparse:
    ap.add_argument("--epochs", type=positive_int, ...)
"""
from __future__ import annotations
import argparse
import os
from typing import Any


def positive_int(value: Any) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer")
    if v < 1:
        raise argparse.ArgumentTypeError(f"{v} must be >= 1")
    return v


def bounded_int(lo: int, hi: int):
    def _check(value: Any) -> int:
        try:
            v = int(value)
        except (TypeError, ValueError):
            raise argparse.ArgumentTypeError(f"{value!r} is not an integer")
        if not (lo <= v <= hi):
            raise argparse.ArgumentTypeError(f"{v} must be in [{lo}, {hi}]")
        return v
    _check.__name__ = f"int[{lo},{hi}]"
    return _check


def bounded_float(lo: float, hi: float, *, inclusive_lo: bool = True, inclusive_hi: bool = True):
    def _check(value: Any) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            raise argparse.ArgumentTypeError(f"{value!r} is not a float")
        lo_ok = (v >= lo) if inclusive_lo else (v > lo)
        hi_ok = (v <= hi) if inclusive_hi else (v < hi)
        if not (lo_ok and hi_ok):
            lo_bracket = "[" if inclusive_lo else "("
            hi_bracket = "]" if inclusive_hi else ")"
            raise argparse.ArgumentTypeError(f"{v} must be in {lo_bracket}{lo}, {hi}{hi_bracket}")
        return v
    _check.__name__ = f"float[{lo},{hi}]"
    return _check


def existing_file(value: Any) -> str:
    if not os.path.isfile(str(value)):
        raise argparse.ArgumentTypeError(f"file not found: {value!r}")
    return str(value)


def existing_dir(value: Any) -> str:
    if not os.path.isdir(str(value)):
        raise argparse.ArgumentTypeError(f"directory not found: {value!r}")
    return str(value)


def finite_float(value: Any) -> float:
    import math
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"{value!r} is not a float")
    if not math.isfinite(v):
        raise argparse.ArgumentTypeError(f"{v} must be a finite float")
    return v
