"""Custom argparse types for numeric validation."""
from __future__ import annotations

import argparse


def positive_int(v: str) -> int:
    try:
        x = int(v)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be an integer, got {v!r}")
    if x <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer (>0), got {x}")
    return x


def positive_float(v: str) -> float:
    try:
        x = float(v)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a float, got {v!r}")
    if x <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive float (>0), got {x}")
    return x


def nonnegative_float(v: str) -> float:
    try:
        x = float(v)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a float, got {v!r}")
    if x < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {x}")
    return x
