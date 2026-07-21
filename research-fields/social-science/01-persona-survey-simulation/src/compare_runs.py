"""Compare two simulate.py runs and report per-cell agreement rate.

Reports coverage (missing / refused / errored) explicitly, validates key uniqueness,
and only computes agreement on the rows where BOTH runs produced a numeric score.

Usage:
  python compare_runs.py data/responses_run1.csv data/responses_run2.csv
"""
from __future__ import annotations

import sys

import pandas as pd


def _load(path: str, label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in ("persona_id", "question_id"):
        if col not in df.columns:
            print(f"ERROR: {label} ({path}) missing required column '{col}'.", file=sys.stderr)
            sys.exit(2)
    if df.duplicated(subset=["persona_id", "question_id"]).any():
        print(
            f"ERROR: {label} ({path}) has duplicate (persona_id, question_id) rows.",
            file=sys.stderr,
        )
        sys.exit(2)
    return df


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: compare_runs.py <run1.csv> <run2.csv>", file=sys.stderr)
        return 2
    a = _load(sys.argv[1], "run1")
    b = _load(sys.argv[2], "run2")

    key = ["persona_id", "question_id"]
    keys_a = set(map(tuple, a[key].values.tolist()))
    keys_b = set(map(tuple, b[key].values.tolist()))
    only_a = keys_a - keys_b
    only_b = keys_b - keys_a
    both = keys_a & keys_b

    print(f"n_run1:         {len(a)}")
    print(f"n_run2:         {len(b)}")
    print(f"in_both:        {len(both)}")
    print(f"only_in_run1:   {len(only_a)}")
    print(f"only_in_run2:   {len(only_b)}")
    if only_a or only_b:
        print(
            "WARNING: run coverage differs. Agreement below is computed only on the "
            f"overlap ({len(both)} keys).",
            file=sys.stderr,
        )

    m = a[key + ["score"]].merge(
        b[key + ["score"]], on=key, suffixes=("_a", "_b"), how="outer", indicator=True
    )
    # Coerce scores to numeric so refused/errored rows (empty strings, non-numeric)
    # become NaN and are counted as "missing" rather than mis-compared.
    m["score_a"] = pd.to_numeric(m["score_a"], errors="coerce")
    m["score_b"] = pd.to_numeric(m["score_b"], errors="coerce")

    n_scored_both = int(((m["score_a"].notna()) & (m["score_b"].notna())).sum())
    n_missing_a = int(m["score_a"].isna().sum())
    n_missing_b = int(m["score_b"].isna().sum())
    n_scored_only_a = int(((m["score_a"].notna()) & (m["score_b"].isna())).sum())
    n_scored_only_b = int(((m["score_b"].notna()) & (m["score_a"].isna())).sum())
    print(f"scored_in_both: {n_scored_both}")
    print(f"missing_a:      {n_missing_a}   (absent from run1 or refused/errored)")
    print(f"missing_b:      {n_missing_b}   (absent from run2 or refused/errored)")
    print(f"scored_only_a:  {n_scored_only_a}   (run1 scored but run2 refused/errored/absent)")
    print(f"scored_only_b:  {n_scored_only_b}   (run2 scored but run1 refused/errored/absent)")
    if n_scored_only_a > 0 or n_scored_only_b > 0:
        print(
            "WARNING: per-key score availability differs between runs. "
            "Refusal or transient errors are affecting reproducibility.",
            file=sys.stderr,
        )

    scored = m.dropna(subset=["score_a", "score_b"])
    if len(scored) == 0:
        print("ERROR: no rows are scored in both runs.", file=sys.stderr)
        return 1

    agreement_rate = float((scored["score_a"] == scored["score_b"]).mean())
    mean_abs_diff = float((scored["score_a"] - scored["score_b"]).abs().mean())
    print(f"agreement_rate: {agreement_rate:.3f}   (n={len(scored)})")
    print(f"mean_abs_diff:  {mean_abs_diff:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
