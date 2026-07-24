"""Custom argparse types used by the quickstart scripts."""
from __future__ import annotations

import argparse


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {value!r}")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive float, got {value!r}")
    return parsed


def nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError(f"expected a non-negative float, got {value!r}")
    return parsed


def bounded_probability(value: str) -> float:
    parsed = float(value)
    if not 0.0 <= parsed <= 1.0:
        raise argparse.ArgumentTypeError(
            f"expected a probability in [0.0, 1.0], got {value!r}"
        )
    return parsed


def positive_odd_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0 or parsed % 2 == 0:
        raise argparse.ArgumentTypeError(
            f"expected a positive odd integer, got {value!r}"
        )
    return parsed
