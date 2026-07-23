"""Batch-embed a CSV of texts and write vectors + provenance manifest.

Usage:
    python src/embed.py --input data/synthetic_sentiment.csv \
        --text-col text --id-col id \
        --output data/embeddings/sentiment.npy

Outputs:
    <output>.npy      — float32 (N, dim) matrix
    <output>.ids.csv  — original id (or row index) per row, same order as npy
    <output>.manifest.json — model, deployment, dim, sha256(input), timestamps
"""
from __future__ import annotations

import argparse
import hashlib
import json
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", required=True, type=Path, help="Input CSV path")
    p.add_argument("--text-col", default="text")
    p.add_argument("--id-col", default=None, help="Optional id column; falls back to row index.")
    p.add_argument("--output", required=True, type=Path, help="Output .npy path")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--max-chars", type=int, default=6000,
                   help="Truncate each text to this many chars before embed (safety net vs 8192-token limit).")
    p.add_argument("--dimensions", type=int, default=None,
                   help="Optional embedding truncation via `dimensions` param (Embedding-3 only).")
    p.add_argument("--no-mask", action="store_true", help="Disable URL/mention masking during cleaning.")
    return p.parse_args()


def batched(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def main() -> int:
    args = parse_args()
    deployment = require_env("AZURE_OPENAI_EMBED_DEPLOYMENT")
    location = require_env("AZURE_OPENAI_LOCATION")
    deployment_type = require_env("AZURE_OPENAI_EMBED_DEPLOYMENT_TYPE")

    if not args.input.exists():
        raise SystemExit(f"ERROR: input CSV not found: {args.input}")
    df = pd.read_csv(args.input)
    if args.text_col not in df.columns:
        raise SystemExit(f"ERROR: --text-col {args.text_col!r} not in {list(df.columns)}")

    ids = (
        df[args.id_col].astype(str).tolist()
        if args.id_col and args.id_col in df.columns
        else [str(i) for i in range(len(df))]
    )
    raw_texts = df[args.text_col].astype(str).tolist()
    cleaned = [clean_for_embedding(t, mask_urls=not args.no_mask, mask_mentions=not args.no_mask)[: args.max_chars]
               for t in raw_texts]

    empty_idx = [i for i, t in enumerate(cleaned) if not t]
    if empty_idx:
        raise SystemExit(f"ERROR: {len(empty_idx)} rows became empty after cleaning (rows {empty_idx[:5]}...).")

    client = make_client()
    dim: int | None = None
    all_vecs: list[np.ndarray] = []

    t_start = time.time()
    total_input_tokens = 0

    for batch_idx, batch in enumerate(batched(cleaned, args.batch_size)):
        kwargs = {"model": deployment, "input": batch, "encoding_format": "float"}
        if args.dimensions is not None:
            kwargs["dimensions"] = args.dimensions
        resp = client.embeddings.create(**kwargs)
        # Sort by index to guarantee same order as input list
        ordered = sorted(resp.data, key=lambda x: x.index)
        vecs = np.array([e.embedding for e in ordered], dtype=np.float32)
        if dim is None:
            dim = vecs.shape[1]
        elif vecs.shape[1] != dim:
            raise SystemExit(f"ERROR: batch {batch_idx} dimension mismatch: {vecs.shape[1]} vs {dim}")
        all_vecs.append(vecs)
        total_input_tokens += resp.usage.prompt_tokens
        print(f"[embed] batch {batch_idx}: {len(batch)} texts, prompt_tokens={resp.usage.prompt_tokens}",
              file=sys.stderr)

    matrix = np.vstack(all_vecs)
    assert matrix.shape[0] == len(cleaned)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output, matrix)

    ids_csv = args.output.with_suffix(".ids.csv")
    pd.DataFrame({"row": range(len(ids)), "id": ids}).to_csv(ids_csv, index=False)

    manifest_path = args.output.with_suffix(".manifest.json")
    input_sha = hashlib.sha256(args.input.read_bytes()).hexdigest()[:16]
    manifest = {
        "input_csv": str(args.input),
        "input_sha256_16": input_sha,
        "text_col": args.text_col,
        "id_col": args.id_col,
        "n_rows": len(cleaned),
        "embedding_model": "text-embedding-3-small",
        "aoai_deployment": deployment,
        "aoai_deployment_type": deployment_type,
        "aoai_location": location,
        "dimensions": dim,
        "dimensions_requested": args.dimensions,
        "batch_size": args.batch_size,
        "total_input_tokens": total_input_tokens,
        # Standard tier pricing $0.02/1M input tokens for text-embedding-3-small (verify at run time)
        "estimated_cost_usd": round(total_input_tokens * 0.02 / 1_000_000, 6),
        "elapsed_seconds": round(time.time() - t_start, 2),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    print(f"[embed] wrote {args.output} shape={matrix.shape}")
    print(f"[embed] wrote {ids_csv}")
    print(f"[embed] wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
