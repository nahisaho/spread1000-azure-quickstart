"""Descriptive analysis + optional per-question χ² test for LLM persona responses.

Usage:
  # Descriptive only (default)
  python analyze.py --responses data/responses.csv --by age_group --output-dir data/analysis/

  # Per-question χ² test (single question at a time to avoid pseudoreplication)
  python analyze.py --responses data/responses.csv --by age_group --output-dir data/analysis/ \\
      --chi2 --question q001

The χ² test is DISABLED by default. Even when enabled it requires --question to
restrict analysis to ONE question, because pooling multiple questions from the
same persona introduces within-persona correlation (pseudoreplication).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency


def cramers_v(chi2: float, n: int, r: int, k: int) -> float:
    denom = n * max(min(r - 1, k - 1), 1)
    return float(np.sqrt(chi2 / denom)) if denom > 0 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True, help="Joined responses CSV from simulate.py.")
    ap.add_argument(
        "--by",
        required=True,
        help="Demographic column to group by (age_group / gender / region / ...).",
    )
    ap.add_argument("--output-dir", required=True)
    ap.add_argument(
        "--score-col",
        default="score",
        help="Response score column (default: score).",
    )
    ap.add_argument(
        "--chi2",
        action="store_true",
        help="Also run χ² test on a SINGLE question (requires --question).",
    )
    ap.add_argument(
        "--question",
        default=None,
        help="question_id to restrict χ² analysis to (required with --chi2).",
    )
    args = ap.parse_args()

    df = pd.read_csv(args.responses)
    if len(df) == 0:
        print(
            f"ERROR: '{args.responses}' has 0 rows. Did simulate.py fail? "
            f"Check the sidecar '.manifest.json' for errors/refusals.",
            file=sys.stderr,
        )
        return 2
    if args.by not in df.columns:
        print(f"ERROR: column '{args.by}' not found. Available: {list(df.columns)}", file=sys.stderr)
        return 2

    df = df.dropna(subset=[args.score_col, args.by])
    if len(df) == 0:
        print(
            f"ERROR: after dropping rows with NaN in {args.score_col}/{args.by}, 0 rows remain.",
            file=sys.stderr,
        )
        return 2
    df[args.score_col] = df[args.score_col].astype(int)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Diagnostics: how many personas contribute to each group?
    if "persona_id" in df.columns:
        personas_per_group = df.groupby(args.by)["persona_id"].nunique()
        print(f"=== Personas per {args.by} ===")
        print(personas_per_group.to_string())
        print()
        min_personas = int(personas_per_group.min())
    else:
        min_personas = None

    # 1. Distribution (row-normalized crosstab)
    dist = pd.crosstab(df[args.by], df[args.score_col], normalize="index")
    dist_path = out_dir / f"distribution_{args.by}.csv"
    dist.to_csv(dist_path)
    print(f"[analyze] wrote {dist_path}")
    print(dist)
    print()

    # 2. Mean score by group (descriptive)
    means = df.groupby(args.by)[args.score_col].agg(["mean", "std", "count"])
    means_path = out_dir / f"mean_{args.by}.csv"
    means.to_csv(means_path)
    print(f"[analyze] wrote {means_path}")
    print(means)
    print()

    # 3. Chi-square (optional, per-question to avoid within-persona correlation)
    if args.chi2:
        if "question_id" not in df.columns:
            print(
                "ERROR: --chi2 requires a 'question_id' column in the responses CSV.",
                file=sys.stderr,
            )
            return 2
        if "persona_id" not in df.columns:
            print(
                "ERROR: --chi2 requires a 'persona_id' column in the responses CSV.",
                file=sys.stderr,
            )
            return 2
        if not args.question:
            qs = sorted(df["question_id"].dropna().unique().tolist())
            print(
                "ERROR: --chi2 must be paired with --question <question_id> "
                "to analyze one question at a time and avoid within-persona "
                "response correlation (pseudoreplication). "
                f"Available questions: {qs}",
                file=sys.stderr,
            )
            return 2
        qdf = df[df["question_id"] == args.question]
        if len(qdf) == 0:
            print(f"ERROR: no responses for question_id='{args.question}'.", file=sys.stderr)
            return 2

        # Reject duplicate persona responses for the selected question — those
        # would reintroduce within-persona correlation the per-question filter is
        # designed to eliminate.
        dup_mask = qdf["persona_id"].duplicated(keep=False)
        if dup_mask.any():
            dups = sorted(qdf.loc[dup_mask, "persona_id"].unique().tolist())
            print(
                f"ERROR: question_id='{args.question}' has multiple responses from "
                f"the same persona(s): {dups}. χ² would be invalid.",
                file=sys.stderr,
            )
            return 2

        # Recompute personas-per-group specifically from the selected question,
        # not the full dataset (so refused/missing responses lower the count).
        q_personas_per_group = qdf.groupby(args.by)["persona_id"].nunique()
        q_min_personas = int(q_personas_per_group.min()) if len(q_personas_per_group) else 0
        print(f"=== Personas per {args.by} (question={args.question}) ===")
        print(q_personas_per_group.to_string())
        print()

        counts = pd.crosstab(qdf[args.by], qdf[args.score_col])
        if counts.shape[0] < 2 or counts.shape[1] < 2:
            print(
                f"ERROR: not enough variation for χ² (shape={counts.shape}).",
                file=sys.stderr,
            )
            return 2
        chi2, p, dof, expected = chi2_contingency(counts)
        v = cramers_v(chi2, int(counts.to_numpy().sum()), *counts.shape)
        low_cells = int((expected < 5).sum())
        total_cells = expected.size

        underpowered = q_min_personas < 5
        result = {
            "grouping": args.by,
            "question_id": args.question,
            "n_responses": int(len(qdf)),
            "n_groups": int(counts.shape[0]),
            "n_score_levels": int(counts.shape[1]),
            "min_personas_per_group": q_min_personas,
            "chi2": float(chi2),
            "p_value": float(p),
            "dof": int(dof),
            "cramers_v": v,
            "cramers_v_effect": (
                "small" if v < 0.1 else "medium" if v < 0.3 else "large"
            ),
            "low_expected_cells": low_cells,
            "total_cells": total_cells,
            "underpowered_warning": underpowered,
        }
        chi2_path = out_dir / f"chi2_{args.by}_{args.question}.json"
        chi2_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"[analyze] wrote {chi2_path}")

        print(f"=== Chi-square: {args.by} × {args.score_col}  (question={args.question}) ===")
        print(f"chi2:       {chi2:.3f}")
        print(f"p-value:    {p:.4f}")
        print(f"dof:        {dof}")
        print(f"cramers_v:  {v:.3f}  ({result['cramers_v_effect']} effect)")
        if underpowered:
            print(
                f"WARNING: only {q_min_personas} persona(s) per group for this question. "
                "χ² p-value is unreliable; treat as descriptive only. "
                "See docs/06-ethics-and-limits.md."
            )
        if low_cells > 0:
            print(
                f"WARNING: {low_cells}/{total_cells} expected cell counts < 5; "
                "χ² asymptotic p-value may be inaccurate. Consider Fisher's exact test."
            )
    else:
        print(
            "[analyze] χ² test skipped (default). Re-run with '--chi2 --question <qid>' to "
            "run χ² on a single question. Pooling multiple questions is invalid because "
            "responses within a persona are correlated (pseudoreplication)."
        )

    # 4. Histogram
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 5))
        for group in dist.index:
            ax.plot(dist.columns, dist.loc[group].values, marker="o", label=str(group))
        ax.set_xlabel("Likert score")
        ax.set_ylabel("proportion (row-normalized)")
        ax.set_title(f"Response distribution by {args.by}")
        ax.legend(title=args.by, fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        hist_path = out_dir / f"histogram_{args.by}.png"
        fig.savefig(hist_path, dpi=120)
        plt.close(fig)
        print(f"[analyze] wrote {hist_path}")
    except ImportError:
        print("[analyze] matplotlib not installed; skipping histogram plot.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
