"""Post-run verification. Fails (nonzero exit) on any invariant violation.

Usage:
    python src/verify.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


DATA = Path("data")


def _die(msg: str) -> None:
    print(f"[verify] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"[verify] ok:  {msg}")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    import numpy as np
    import pandas as pd

    fetch_pq = DATA / "mp-bandgap.parquet"
    fetch_mf = DATA / "mp-bandgap.manifest.json"
    feats_pq = DATA / "features.parquet"
    feats_mf = DATA / "features.manifest.json"
    metrics = DATA / "metrics.json"
    preds = DATA / "predictions.parquet"
    model = DATA / "model_xgboost.ubj"
    split = DATA / "split_ids.json"

    for p in (fetch_pq, fetch_mf, feats_pq, feats_mf, metrics, preds, model, split):
        if not p.exists():
            _die(f"missing artifact: {p}")

    # 1. fetch manifest sha256 matches file
    fmf = json.loads(fetch_mf.read_text())
    if fmf.get("parquet_sha256") != _sha(fetch_pq):
        _die("fetch parquet sha256 does not match manifest")
    _ok(f"fetch sha256 verified ({fmf['n_records']} rows)")

    # 2. featurize manifest sha256 chain
    ffmf = json.loads(feats_mf.read_text())
    if ffmf.get("input_sha256") != _sha(fetch_pq):
        _die("features.manifest.input_sha256 != fetch parquet sha256")
    if ffmf.get("output_sha256") != _sha(feats_pq):
        _die("features.manifest.output_sha256 != features parquet sha256")
    _ok("featurize input/output sha256 chain verified")

    # 3. feature matrix: no NaN, expected width, band_gap present
    fdf = pd.read_parquet(feats_pq)
    meta = {"material_id", "formula_pretty", "band_gap"}
    feat_cols = [c for c in fdf.columns if c not in meta]
    if len(feat_cols) != ffmf["n_features"]:
        _die(f"feature width mismatch: parquet has {len(feat_cols)} vs manifest {ffmf['n_features']}")
    if fdf[feat_cols].isna().any().any():
        _die("features.parquet contains NaN (drop_nan_rows should have removed them)")
    if not np.isfinite(fdf[feat_cols].to_numpy()).all():
        _die("features.parquet contains non-finite values (inf)")
    if "band_gap" not in fdf.columns:
        _die("features.parquet missing band_gap column")
    _ok(f"features matrix ok: {len(fdf)} rows x {len(feat_cols)} features")

    # 4. train/test split disjoint by material_id and predictions match test ids
    sp = json.loads(split.read_text())
    tr = set(sp["train_material_ids"])
    te = set(sp["test_material_ids"])
    if tr & te:
        _die(f"train/test id overlap: {len(tr & te)} ids in both")
    pdf = pd.read_parquet(preds)
    if set(pdf["material_id"].astype(str)) != te:
        _die("predictions material_ids != split_ids.test_material_ids")
    _ok(f"split disjoint and predictions cover full test set ({len(te)} rows)")

    # 5. metrics structure and features sha chain
    mj = json.loads(metrics.read_text())
    if mj.get("features_sha256") != _sha(feats_pq):
        _die("metrics.features_sha256 != features parquet sha256")
    for name in ("dummy_mean", "linear", "xgboost"):
        if name not in mj["results"]:
            _die(f"metrics.results missing model '{name}'")
        for k in ("cv_mae_mean", "cv_mae_std", "holdout_mae", "holdout_rmse", "holdout_r2"):
            v = mj["results"][name].get(k)
            if not isinstance(v, (int, float)) or v != v:  # NaN check
                _die(f"metrics.results.{name}.{k} is not a finite number")
    _ok("metrics structure and sha chain verified")

    print("[verify] ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
