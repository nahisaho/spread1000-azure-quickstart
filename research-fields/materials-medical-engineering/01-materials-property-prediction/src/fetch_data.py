"""Fetch band-gap structures from Materials Project and cache to Parquet.

Requires MP_API_KEY environment variable.
Get one at https://next-gen.materialsproject.org/dashboard

Usage:
    python src/fetch_data.py --output data/mp-bandgap.parquet
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--num-elements-min", type=int, default=1)
    p.add_argument("--num-elements-max", type=int, default=3)
    p.add_argument("--band-gap-min", type=float, default=0.1)
    p.add_argument("--band-gap-max", type=float, default=5.0)
    p.add_argument("--chunk-size", type=int, default=1000)
    p.add_argument("--num-chunks", type=int, default=2)
    p.add_argument("--limit", type=int, default=1500, help="Slice result to first N rows.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("MP_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "ERROR: MP_API_KEY is not set. Get one at "
            "https://next-gen.materialsproject.org/dashboard and `export MP_API_KEY=...`"
        )

    import pandas as pd
    from mp_api.client import MPRester

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with MPRester(api_key) as mpr:
        db_version = getattr(mpr, "db_version", "unknown")
        # include_gnome=False: GNoME data is CC BY-NC, unsuitable for educational redistribution.
        # deprecated=False: exclude entries marked deprecated by MP.
        docs = mpr.materials.summary.search(
            fields=["material_id", "formula_pretty", "band_gap", "structure", "nsites", "nelements"],
            num_elements=(args.num_elements_min, args.num_elements_max),
            band_gap=(args.band_gap_min, args.band_gap_max),
            include_gnome=False,
            deprecated=False,
            chunk_size=args.chunk_size,
            num_chunks=args.num_chunks,
        )

    if not docs:
        raise SystemExit("ERROR: MP query returned 0 records. Try loosening filters.")

    docs = docs[: args.limit]
    rows = []
    for d in docs:
        rows.append({
            "material_id": str(d.material_id),
            "formula_pretty": d.formula_pretty,
            "band_gap": float(d.band_gap),
            "nsites": int(d.nsites),
            "nelements": int(d.nelements),
            # Store structure as JSON string, NOT pickle, for portability.
            "structure_json": json.dumps(d.structure.as_dict()),
        })
    df = pd.DataFrame(rows)
    df.to_parquet(args.output, index=False)

    from importlib.metadata import version as _pkg_version
    manifest = {
        "source": "Materials Project (https://next-gen.materialsproject.org)",
        "license": "CC BY 4.0 (excludes GNoME which is CC BY-NC)",
        "citation": "Jain et al., APL Materials 1, 011002 (2013). DOI:10.1063/1.4812323",
        "mp_api_version": _pkg_version("mp-api"),
        "mp_database_version": db_version,
        "query": {
            "num_elements": [args.num_elements_min, args.num_elements_max],
            "band_gap": [args.band_gap_min, args.band_gap_max],
            "include_gnome": False,
            "deprecated": False,
        },
        "n_records": len(df),
        "parquet_sha256_16": hashlib.sha256(args.output.read_bytes()).hexdigest()[:16],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    print(f"[fetch] wrote {args.output} ({len(df)} rows)")
    print(f"[fetch] wrote {manifest_path}")
    print(f"[fetch] band_gap stats (eV): mean={df.band_gap.mean():.3f} "
          f"min={df.band_gap.min():.3f} max={df.band_gap.max():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
