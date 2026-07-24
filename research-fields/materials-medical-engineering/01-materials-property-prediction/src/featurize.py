"""Featurize structures with Matminer ElementProperty (magpie preset).

Composition-only features — no DFT required, fast on CPU.

Feature dimensions depend on preset:
  - magpie:    132 features (22 properties x 6 statistics)
  - megnet_el:  80 features (16-d MEGNet element embedding x 5 statistics)
  - matminer:   65 features (13 properties x 5 statistics)

Usage:
    python src/featurize.py --input data/mp-bandgap.parquet --output data/features.parquet
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--preset", default="magpie", choices=["magpie", "megnet_el", "matminer"])
    p.add_argument(
        "--drop-nan-rows", default=True,
        action=argparse.BooleanOptionalAction,
        help="Drop rows containing NaN features (default) or keep them with --no-drop-nan-rows.",
    )
    p.add_argument("--impute-nan", action="store_true",
                   help="Enable matminer's built-in NaN imputation (may silently substitute "
                        "chemically meaningless mean values; disabled by default).")
    p.add_argument("--force", action="store_true", help="Allow overwriting existing output.")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.input.resolve() == args.output.resolve():
        raise SystemExit("ERROR: --input and --output must be different paths.")
    if args.output.exists() and not args.force:
        raise SystemExit(
            f"ERROR: {args.output} already exists. Use --force to overwrite."
        )

    import numpy as np
    import pandas as pd
    from matminer.featurizers.composition import ElementProperty
    from pymatgen.core import Structure

    if not args.input.exists():
        raise SystemExit(f"ERROR: {args.input} not found. Run src/fetch_data.py first.")

    df = pd.read_parquet(args.input)
    if "structure_json" not in df.columns:
        raise SystemExit("ERROR: input parquet missing 'structure_json' column.")

    print(f"[featurize] loading {len(df)} structures ...", file=sys.stderr)
    structures = [Structure.from_dict(json.loads(s)) for s in df["structure_json"]]
    compositions = [s.composition for s in structures]

    # impute_nan=False is a deliberate choice: matminer 0.10.1 defaults to True,
    # which mean-imputes missing elemental properties (e.g., radioactive elements
    # absent from Magpie). Mean-imputed features are chemically meaningless and
    # would silently poison the model. When False, missing elements produce NaN
    # rows that we then drop and log.
    featurizer = ElementProperty.from_preset(args.preset, impute_nan=args.impute_nan)
    feature_names = featurizer.feature_labels()

    feats = [featurizer.featurize(c) for c in compositions]
    feat_arr = np.array(feats, dtype=np.float32)

    out_df = pd.DataFrame(feat_arr, columns=feature_names)
    out_df.insert(0, "material_id", df["material_id"].values)
    out_df.insert(1, "formula_pretty", df["formula_pretty"].values)
    out_df["band_gap"] = df["band_gap"].values.astype(np.float32)

    n_before = len(out_df)
    dropped_ids: list[str] = []
    if args.drop_nan_rows:
        nan_mask = out_df[feature_names].isna().any(axis=1)
        dropped_ids = out_df.loc[nan_mask, "material_id"].tolist()
        out_df = out_df.loc[~nan_mask].reset_index(drop=True)
        if dropped_ids:
            print(f"[featurize] dropped {len(dropped_ids)} rows containing NaN features "
                  "(elements without Magpie entries)", file=sys.stderr)

    if len(out_df) < 100:
        raise SystemExit(f"ERROR: only {len(out_df)} usable rows after cleaning. Fetch more data.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".part")
    out_df.to_parquet(tmp, index=False)
    tmp.replace(args.output)

    input_sha = hashlib.sha256(args.input.read_bytes()).hexdigest()
    output_sha = hashlib.sha256(args.output.read_bytes()).hexdigest()
    from importlib.metadata import version as _pkg_version
    manifest = {
        "input_parquet": str(args.input),
        "input_sha256": input_sha,
        "output_parquet": str(args.output),
        "output_sha256": output_sha,
        "preset": args.preset,
        "impute_nan": args.impute_nan,
        "drop_nan_rows": args.drop_nan_rows,
        "matminer_version": _pkg_version("matminer"),
        "pymatgen_version": _pkg_version("pymatgen"),
        "n_input_rows": n_before,
        "n_output_rows": len(out_df),
        "dropped_material_ids": dropped_ids,
        "n_features": len(feature_names),
        "feature_names": feature_names,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)
    )
    print(f"[featurize] wrote {args.output} shape=({len(out_df)}, {len(feature_names)} features + 3 meta)")
    print(f"[featurize] wrote {args.output.with_suffix('.manifest.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
