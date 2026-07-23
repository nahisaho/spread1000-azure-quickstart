"""Featurize structures with Matminer ElementProperty (magpie preset).

Composition-only features (132-d) — no DFT required, fast on CPU.

Usage:
    python src/featurize.py --input data/mp-bandgap.parquet --output data/features.parquet
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--preset", default="magpie", choices=["magpie", "megnet_el", "matminer"])
    p.add_argument("--drop-nan-rows", action="store_true", default=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
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

    featurizer = ElementProperty.from_preset(args.preset)
    feature_names = featurizer.feature_labels()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        feats = [featurizer.featurize(c) for c in compositions]
    feat_arr = np.array(feats, dtype=np.float32)

    out_df = pd.DataFrame(feat_arr, columns=feature_names)
    out_df.insert(0, "material_id", df["material_id"].values)
    out_df.insert(1, "formula_pretty", df["formula_pretty"].values)
    out_df["band_gap"] = df["band_gap"].values.astype(np.float32)

    n_before = len(out_df)
    if args.drop_nan_rows:
        out_df = out_df.dropna()
        n_after = len(out_df)
        if n_after < n_before:
            print(f"[featurize] dropped {n_before - n_after} rows containing NaN features "
                  "(likely elements without Magpie entries)", file=sys.stderr)

    if len(out_df) < 100:
        raise SystemExit(f"ERROR: only {len(out_df)} usable rows after cleaning. Fetch more data.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(args.output, index=False)
    print(f"[featurize] wrote {args.output} shape=({len(out_df)}, {len(feature_names)} features + 3 meta)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
