"""Batch-embed a CSV of texts and write vectors + provenance manifest.

Usage:
    python src/embed.py --input data/synthetic_sentiment.csv \
        --text-col text --id-col id \
        --output data/embeddings/sentiment.npy

Outputs:
    <output>.npy           — float32 (N, dim) matrix
    <output>.ids.csv       — [row, id] per row, same order as npy (id-col REQUIRED)
    <output>.cleaned.csv   — cleaned/truncated text actually sent to AOAI
    <output>.manifest.json — model, deployment, dim, sha256(input), timestamps
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Allow `python src/embed.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aoai_client import make_client, require_env  # noqa: E402
from text_cleaning import clean_for_embedding  # noqa: E402


# Excel/Sheets/LibreOffice execute a cell if it starts with any of these,
# so any user-supplied value written into a CSV must be prefixed with "'"
# to disable formula parsing on open.
_FORMULA_INJECTION_PREFIX = ("=", "+", "-", "@", "\t", "\r")


def excel_safe(value: str) -> str:
    return "'" + value if value.startswith(_FORMULA_INJECTION_PREFIX) else value


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", required=True, type=Path, help="Input CSV path")
    p.add_argument("--text-col", default="text")
    p.add_argument("--id-col", required=True,
                   help="ID column name (REQUIRED). Downstream scripts join on this to prevent silent misalignment.")
    p.add_argument("--output", required=True, type=Path, help="Output .npy path")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--max-chars", type=int, default=6000,
                   help="Truncate each text to this many chars before embed (character-level safety net; "
                        "does NOT guarantee the 8192-token model limit for Japanese/emoji-heavy text — use --max-tokens for that).")
    p.add_argument("--max-rows", type=int, default=10000,
                   help="Cost safety cap. Refuses to run if the input has more rows (use --yes to override).")
    p.add_argument("--max-cost-usd", type=float, default=1.0,
                   help="Cost safety cap in USD (pre-flight estimate; use --yes to override).")
    p.add_argument("--yes", action="store_true", help="Skip cost/row confirmation.")
    p.add_argument("--dimensions", type=int, default=None,
                   help="Optional embedding truncation via `dimensions` param (Embedding-3 only).")
    p.add_argument("--no-mask", action="store_true", help="Disable URL/mention masking during cleaning.")
    p.add_argument("--force", action="store_true", help="Allow overwriting existing outputs.")
    return p.parse_args()


def batched(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return ""


def main() -> int:
    args = parse_args()
    deployment = require_env("AZURE_OPENAI_EMBED_DEPLOYMENT")
    location = require_env("AZURE_OPENAI_LOCATION")
    deployment_type = require_env("AZURE_OPENAI_EMBED_DEPLOYMENT_TYPE")
    model_name = require_env("AZURE_OPENAI_EMBED_MODEL_NAME")
    model_version = require_env("AZURE_OPENAI_EMBED_MODEL_VERSION")

    if not args.input.exists():
        raise SystemExit(f"ERROR: input CSV not found: {args.input}")
    for out in (args.output, args.output.with_suffix(".ids.csv"),
                args.output.with_suffix(".cleaned.csv"),
                args.output.with_suffix(".manifest.json")):
        if out.exists() and not args.force:
            raise SystemExit(f"ERROR: {out} already exists. Use --force to overwrite.")

    df = pd.read_csv(args.input)
    if args.text_col not in df.columns:
        raise SystemExit(f"ERROR: --text-col {args.text_col!r} not in {list(df.columns)}")
    if args.id_col not in df.columns:
        raise SystemExit(f"ERROR: --id-col {args.id_col!r} not in {list(df.columns)}")

    # Refuse missing text/ids: pandas would silently coerce NaN to the literal 'nan' string.
    for col in (args.id_col, args.text_col):
        na_mask = df[col].isna()
        if na_mask.any():
            bad_rows = df.index[na_mask].tolist()[:10]
            raise SystemExit(f"ERROR: column {col!r} has {int(na_mask.sum())} missing values "
                             f"(first rows: {bad_rows}). Fix the input CSV.")

    ids = df[args.id_col].astype(str).tolist()
    if len(set(ids)) != len(ids):
        raise SystemExit(f"ERROR: --id-col {args.id_col!r} contains duplicate values; ids must be unique.")

    raw_texts = df[args.text_col].astype(str).tolist()
    cleaned = [clean_for_embedding(t, mask_urls=not args.no_mask, mask_mentions=not args.no_mask)[: args.max_chars]
               for t in raw_texts]

    empty_idx = [i for i, t in enumerate(cleaned) if not t]
    if empty_idx:
        raise SystemExit(f"ERROR: {len(empty_idx)} rows became empty after cleaning (rows {empty_idx[:5]}...).")

    if len(cleaned) > args.max_rows and not args.yes:
        raise SystemExit(
            f"ERROR: input has {len(cleaned)} rows, exceeds --max-rows={args.max_rows}. "
            "Re-run with --yes or lower the input size to avoid unexpected cost."
        )
    # Rough pre-flight cost estimate. Japanese averages ~1.3 tokens/char; be conservative.
    est_tokens = sum(len(t) for t in cleaned) * 2
    est_cost = est_tokens * 0.02 / 1_000_000  # $0.02 / 1M input tokens for text-embedding-3-small (verify at runtime)
    if est_cost > args.max_cost_usd and not args.yes:
        raise SystemExit(
            f"ERROR: pre-flight cost estimate ~${est_cost:.4f} > --max-cost-usd={args.max_cost_usd}. "
            "Re-run with --yes to override after verifying current pricing."
        )
    print(f"[embed] pre-flight: {len(cleaned)} rows, est_tokens<={est_tokens}, est_cost<=${est_cost:.4f}",
          file=sys.stderr)

    client = make_client()
    dim: int | None = None
    all_vecs: list[np.ndarray] = []

    t_start = time.time()
    total_input_tokens = 0

    # Checkpoint: write per-batch progress so an interrupted run can resume without
    # re-billing already-completed batches. Simple file-based scheme keeps deps minimal.
    ckpt = args.output.with_suffix(".checkpoint.jsonl")
    completed = set()
    if ckpt.exists() and not args.force:
        for line in ckpt.read_text().splitlines():
            try:
                completed.add(int(json.loads(line).get("batch_idx", -1)))
            except Exception:
                pass
        if completed:
            print(f"[embed] resuming: {len(completed)} batches already completed", file=sys.stderr)
    if args.force and ckpt.exists():
        ckpt.unlink()

    for batch_idx, batch in enumerate(batched(cleaned, args.batch_size)):
        if batch_idx in completed:
            # Rehydrate from checkpoint file
            vecs = np.load(args.output.with_suffix(f".batch{batch_idx}.npy"))
        else:
            kwargs = {"model": deployment, "input": batch, "encoding_format": "float"}
            if args.dimensions is not None:
                kwargs["dimensions"] = args.dimensions
            resp = client.embeddings.create(**kwargs)
            # Sort by index to guarantee same order as input list
            ordered = sorted(resp.data, key=lambda x: x.index)
            vecs = np.array([e.embedding for e in ordered], dtype=np.float32)
            np.save(args.output.with_suffix(f".batch{batch_idx}.npy"), vecs)
            with ckpt.open("a") as f:
                f.write(json.dumps({"batch_idx": batch_idx,
                                    "n": len(batch),
                                    "prompt_tokens": resp.usage.prompt_tokens}) + "\n")
            total_input_tokens += resp.usage.prompt_tokens
            print(f"[embed] batch {batch_idx}: {len(batch)} texts, prompt_tokens={resp.usage.prompt_tokens}",
                  file=sys.stderr)
        if dim is None:
            dim = vecs.shape[1]
        elif vecs.shape[1] != dim:
            raise SystemExit(f"ERROR: batch {batch_idx} dimension mismatch: {vecs.shape[1]} vs {dim}")
        all_vecs.append(vecs)

    matrix = np.vstack(all_vecs)
    assert matrix.shape[0] == len(cleaned)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output, matrix)

    # Cleanup batch checkpoints
    for batch_idx in range(len(all_vecs)):
        p = args.output.with_suffix(f".batch{batch_idx}.npy")
        if p.exists():
            p.unlink()
    if ckpt.exists():
        ckpt.unlink()

    ids_csv = args.output.with_suffix(".ids.csv")
    pd.DataFrame({
        "row": list(range(len(ids))),
        "id": [excel_safe(i) for i in ids],
    }).to_csv(ids_csv, index=False)

    cleaned_csv = args.output.with_suffix(".cleaned.csv")
    # The cleaned/truncated text is what actually reached AOAI — save it so
    # downstream label generation cannot silently leak the original unmasked text.
    pd.DataFrame({
        "row": list(range(len(ids))),
        "id": [excel_safe(i) for i in ids],
        "cleaned_text": [excel_safe(t) for t in cleaned],
    }).to_csv(cleaned_csv, index=False)

    manifest_path = args.output.with_suffix(".manifest.json")
    input_sha = hashlib.sha256(args.input.read_bytes()).hexdigest()
    output_sha = hashlib.sha256(args.output.read_bytes()).hexdigest()
    manifest = {
        "input_csv": str(args.input),
        "input_sha256": input_sha,
        "output_npy_sha256": output_sha,
        "text_col": args.text_col,
        "id_col": args.id_col,
        "n_rows": len(cleaned),
        "embedding_model": model_name,
        "embedding_model_version": model_version,
        "aoai_deployment": deployment,
        "aoai_deployment_type": deployment_type,
        "aoai_location": location,
        "dimensions": dim,
        "dimensions_requested": args.dimensions,
        "batch_size": args.batch_size,
        "max_chars": args.max_chars,
        "masking_applied": not args.no_mask,
        "total_input_tokens": total_input_tokens,
        # Standard-tier pricing for text-embedding-3-small (verify at run time)
        "estimated_cost_usd": round(total_input_tokens * 0.02 / 1_000_000, 6),
        "pricing_reference": "https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/",
        "pricing_effective_date": "2026-07 (verify with current Azure Pricing)",
        "elapsed_seconds": round(time.time() - t_start, 2),
        "package_versions": {
            "openai": __import__("openai").__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "python_version": sys.version.split()[0],
        "git_commit": _git_commit(),
        "user": os.environ.get("USER", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    print(f"[embed] wrote {args.output} shape={matrix.shape}")
    print(f"[embed] wrote {ids_csv}")
    print(f"[embed] wrote {cleaned_csv}")
    print(f"[embed] wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
