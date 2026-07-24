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
    p.add_argument("--limit", type=int, default=1500, help="Slice result to first N rows (>=100).")
    p.add_argument("--force", action="store_true",
                   help="Allow overwriting an existing output file.")
    p.add_argument("--expected-sha256", default=None,
                   help="Optional: full 64-char SHA-256 of the produced parquet to verify.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 100:
        raise SystemExit("ERROR: --limit must be >= 100 to keep the pipeline meaningful.")
    if args.output.exists() and not args.force:
        raise SystemExit(
            f"ERROR: {args.output} already exists. Use --force to overwrite, "
            "or choose a different --output path."
        )
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
        # include_gnome=False: GNoME data is CC BY-NC. Excluding it keeps the produced
        # dataset uniformly CC BY 4.0. Users who need GNoME must consult its own terms.
        # deprecated=False: exclude entries marked deprecated by MP.
        # nelements: 'num_elements' is a deprecated alias in mp-api >=0.46.
        docs = mpr.materials.summary.search(
            fields=["material_id", "formula_pretty", "band_gap", "structure", "nsites", "nelements"],
            nelements=(args.num_elements_min, args.num_elements_max),
            band_gap=(args.band_gap_min, args.band_gap_max),
            include_gnome=False,
            deprecated=False,
            chunk_size=args.chunk_size,
            num_chunks=args.num_chunks,
        )

    if not docs:
        raise SystemExit("ERROR: MP query returned 0 records. Try loosening filters.")

    # Deterministic ordering: sort by material_id BEFORE slicing so two independent
    # runs (with the same DB version and filters) return the same subset.
    docs = sorted(docs, key=lambda d: str(d.material_id))
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

    # Atomic write: stage as *.part then rename, so an interrupted run cannot
    # leave a corrupted parquet that later steps would silently load.
    tmp_path = args.output.with_suffix(args.output.suffix + ".part")
    df.to_parquet(tmp_path, index=False)
    tmp_path.replace(args.output)

    from importlib.metadata import version as _pkg_version
    parquet_sha256 = hashlib.sha256(args.output.read_bytes()).hexdigest()
    if args.expected_sha256 and parquet_sha256 != args.expected_sha256.lower():
        args.output.unlink(missing_ok=True)
        raise SystemExit(
            f"ERROR: parquet SHA-256 mismatch. expected={args.expected_sha256} "
            f"got={parquet_sha256}. This can happen when the MP database version "
            f"changes. Update --expected-sha256 after verifying manually."
        )
    manifest = {
        "source": "Materials Project (https://next-gen.materialsproject.org)",
        "license": "CC BY 4.0 (excludes GNoME which is CC BY-NC and has its own terms)",
        "citation": "Jain et al., APL Materials 1, 011002 (2013). DOI:10.1063/1.4812323",
        "attribution_required": [
            "Materials Project — https://next-gen.materialsproject.org",
            "matminer — Ward, L. et al. Comput. Mater. Sci. 152, 60-69 (2018). DOI:10.1016/j.commatsci.2018.05.018",
            "Magpie descriptors — Ward, L. et al. npj Comput. Mater. 2, 16028 (2016). DOI:10.1038/npjcompumats.2016.28",
        ],
        "mp_api_version": _pkg_version("mp-api"),
        "mp_database_version": db_version,
        "query": {
            "nelements": [args.num_elements_min, args.num_elements_max],
            "band_gap": [args.band_gap_min, args.band_gap_max],
            "include_gnome": False,
            "deprecated": False,
            "chunk_size": args.chunk_size,
            "num_chunks": args.num_chunks,
            "limit": args.limit,
            "sort": "material_id ASC (client-side)",
        },
        "n_records": len(df),
        "material_ids": [r["material_id"] for r in rows],
        "parquet_sha256": parquet_sha256,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    print(f"[fetch] wrote {args.output} ({len(df)} rows)")
    print(f"[fetch] wrote {manifest_path}")
    print(f"[fetch] sha256={parquet_sha256}")
    print(f"[fetch] band_gap stats (eV): mean={df.band_gap.mean():.3f} "
          f"min={df.band_gap.min():.3f} max={df.band_gap.max():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
