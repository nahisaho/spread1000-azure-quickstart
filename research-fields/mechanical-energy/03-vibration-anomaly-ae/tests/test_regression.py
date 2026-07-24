"""
回帰テスト: seed=42 でのデータ生成 → 30 エポック学習 → 評価が
ROC-AUC ≥ 0.95、F1 ≥ 0.85 を満たすことを確認する.

実行:
  cd research-fields/mechanical-energy/03-vibration-anomaly-ae
  python -m pytest tests/test_regression.py -v
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

# src/ を import パスに追加
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))


@pytest.fixture(scope="module")
def pipeline_outputs(tmp_path_factory: pytest.TempPathFactory):
    """Generate data, train for 30 epochs, and evaluate. Returns metrics dict."""
    import torch
    import json

    from generate_data import main as gen_main, parse_args as gen_args
    from train import main as train_main, parse_args as train_args
    from evaluate import main as eval_main, parse_args as eval_args

    work = tmp_path_factory.mktemp("regression")
    data_path  = work / "vibration.npz"
    output_dir = work / "outputs"

    # 1. Generate data
    sys.argv = [
        "generate_data.py",
        "--out", str(data_path),
        "--seed", "42",
    ]
    gen_main()

    # 2. Train 30 epochs
    sys.argv = [
        "train.py",
        "--data", str(data_path),
        "--epochs", "30",
        "--seed", "42",
        "--output-dir", str(output_dir),
    ]
    train_main()

    # 3. Evaluate
    sys.argv = [
        "evaluate.py",
        "--data", str(data_path),
        "--model", str(output_dir / "best_ae.pt"),
        "--output-dir", str(output_dir),
    ]
    eval_main()

    with (output_dir / "eval_metrics.json").open(encoding="utf-8") as f:
        return json.load(f)


def test_roc_auc_meets_threshold(pipeline_outputs: dict) -> None:
    """ROC-AUC must be ≥ 0.95 on the default seed-42 run."""
    auc = pipeline_outputs["roc_auc"]
    assert auc >= 0.95, (
        f"ROC-AUC={auc:.4f} is below the required 0.95. "
        "Check that generate_data.py uses amp=rng.uniform(3.0, 6.0)."
    )


def test_f1_meets_threshold(pipeline_outputs: dict) -> None:
    """F1 must be ≥ 0.85 on the default seed-42 run."""
    f1 = pipeline_outputs["f1"]
    assert f1 >= 0.85, (
        f"F1={f1:.4f} is below the required 0.85. "
        "Check anomaly amplitude and training parameters."
    )


def test_both_classes_evaluated(pipeline_outputs: dict) -> None:
    """Test set must contain both normal and anomaly samples."""
    n_total  = pipeline_outputs["n_test"]
    n_pos    = pipeline_outputs["n_positive"]
    assert 0 < n_pos < n_total, (
        f"Expected both classes in test set; got n_test={n_total}, n_positive={n_pos}"
    )
