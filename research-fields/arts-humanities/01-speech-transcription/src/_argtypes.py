"""Shared argparse type validators for Speech scenario scripts."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


def existing_file(value: str) -> Path:
    """Validate that the argument is an existing regular file."""
    p = Path(value)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"File not found: {value}")
    if not p.is_file():
        raise argparse.ArgumentTypeError(f"Not a regular file: {value}")
    return p


def positive_int(value: str) -> int:
    try:
        v = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Expected integer, got: {value}")
    if v <= 0:
        raise argparse.ArgumentTypeError(f"Must be > 0, got: {v}")
    return v


def positive_float(value: str) -> float:
    try:
        v = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Expected number, got: {value}")
    if v <= 0 or not _is_finite(v):
        raise argparse.ArgumentTypeError(f"Must be a finite positive number, got: {value}")
    return v


def bounded_int(lo: int, hi: int):
    def _check(value: str) -> int:
        v = int(value)
        if not (lo <= v <= hi):
            raise argparse.ArgumentTypeError(f"Must be between {lo} and {hi}, got: {v}")
        return v
    _check.__name__ = f"bounded_int({lo},{hi})"
    return _check


def bounded_float(lo: float, hi: float):
    def _check(value: str) -> float:
        v = float(value)
        if not (lo <= v <= hi):
            raise argparse.ArgumentTypeError(f"Must be between {lo} and {hi}, got: {v}")
        return v
    _check.__name__ = f"bounded_float({lo},{hi})"
    return _check


def finite_float(value: str) -> float:
    try:
        v = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Expected number, got: {value}")
    if not _is_finite(v):
        raise argparse.ArgumentTypeError(f"Must be a finite number, got: {value}")
    return v


_LOCALE_RE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")


def locale_string(value: str) -> str:
    """Validate BCP-47 locale tag (e.g. ja-JP, en-US)."""
    if not _LOCALE_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"Locale must match ^[a-z]{{2}}-[A-Z]{{2}}$ (e.g. ja-JP), got: {value}"
        )
    return value


def _is_finite(v: float) -> bool:
    import math
    return math.isfinite(v)


# Maximum audio duration before --allow-long-run is required (30 min)
DURATION_CAP_SEC = 1800.0


def check_audio_duration(audio_path: Path, allow_long_run: bool) -> float | None:
    """Return audio duration in seconds (best-effort). Raises if over cap."""
    duration = _probe_duration(audio_path)
    if duration is not None and duration > DURATION_CAP_SEC and not allow_long_run:
        raise argparse.ArgumentTypeError(
            f"Audio duration {duration / 60:.1f} min exceeds {DURATION_CAP_SEC / 60:.0f}-min cap. "
            "Pass --allow-long-run to proceed (Batch Transcription API recommended for long files)."
        )
    return duration


def _probe_duration(audio_path: Path) -> float | None:
    """Try ffprobe, then soundfile to get duration. Returns None if unavailable."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        val = result.stdout.strip()
        if val:
            return float(val)
    except Exception:
        pass

    try:
        import soundfile as sf  # type: ignore
        info = sf.info(str(audio_path))
        return info.duration
    except Exception:
        pass

    return None
