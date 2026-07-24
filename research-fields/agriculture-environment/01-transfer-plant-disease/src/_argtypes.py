"""CLI argument type validators (HIGH 3)."""
from __future__ import annotations
import argparse
import math


def bounded_int(name: str, min_val: int, max_val: int):
    """Return an argparse type that checks int is in [min_val, max_val]."""
    def _check(value: str) -> int:
        try:
            v = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"--{name}: expected int, got {value!r}")
        if not (min_val <= v <= max_val):
            raise argparse.ArgumentTypeError(
                f"--{name}: must be in [{min_val}, {max_val}], got {v}"
            )
        return v
    _check.__name__ = f"bounded_int({name},{min_val},{max_val})"
    return _check


def bounded_float(
    name: str,
    min_val: float,
    max_val: float,
    inclusive_min: bool = True,
    inclusive_max: bool = True,
):
    """Return an argparse type that checks float is finite and in bounds."""
    def _check(value: str) -> float:
        try:
            v = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"--{name}: expected float, got {value!r}")
        if not math.isfinite(v):
            raise argparse.ArgumentTypeError(f"--{name}: must be finite, got {value!r}")
        lo_ok = v >= min_val if inclusive_min else v > min_val
        hi_ok = v <= max_val if inclusive_max else v < max_val
        lo_sym = "[" if inclusive_min else "("
        hi_sym = "]" if inclusive_max else ")"
        if not (lo_ok and hi_ok):
            raise argparse.ArgumentTypeError(
                f"--{name}: must be in {lo_sym}{min_val}, {max_val}{hi_sym}, got {v}"
            )
        return v
    _check.__name__ = f"bounded_float({name})"
    return _check


def finite_float(name: str):
    """Return an argparse type that checks float is finite."""
    def _check(value: str) -> float:
        try:
            v = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"--{name}: expected float, got {value!r}")
        if not math.isfinite(v):
            raise argparse.ArgumentTypeError(f"--{name}: must be finite, got {value!r}")
        return v
    _check.__name__ = f"finite_float({name})"
    return _check


def positive_int(name: str):
    """Return an argparse type that checks int >= 1."""
    def _check(value: str) -> int:
        try:
            v = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"--{name}: expected int, got {value!r}")
        if v < 1:
            raise argparse.ArgumentTypeError(f"--{name}: must be >= 1, got {v}")
        return v
    _check.__name__ = f"positive_int({name})"
    return _check
