"""Verify a completed AML job has expected metrics and output files.

Usage:
  pip install "azure-ai-ml==1.34.1" "azure-identity>=1.19.0" \
              "mlflow==2.16.2" "azureml-mlflow==1.57.0"
  python scripts/verify-output.py <job_name> [--min-macro-f1 0.35]

Env vars required: AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_WORKSPACE_NAME.

Checks:
  1. job status == "Completed"
  2. `test_macro_f1` metric present via MLflow, and >= --min-macro-f1 (default 0.35)
  3. Downloads named output `model` and verifies expected files exist:
     model.pt, classification_report.json, confusion_matrix.csv, confusion_matrix.png
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential


EXPECTED_FILES = [
    "model.pt",
    "classification_report.json",
    "confusion_matrix.csv",
    "confusion_matrix.png",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_name")
    parser.add_argument("--min-macro-f1", type=float, default=0.35,
                        help="Lower bound for acceptable test_macro_f1 (default 0.35)")
    args = parser.parse_args()

    required = ("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "AZURE_WORKSPACE_NAME")
    missing = [e for e in required if not os.environ.get(e)]
    if missing:
        print(f"🛑 環境変数が未設定: {missing}", file=sys.stderr)
        return 2

    client = MLClient(
        DefaultAzureCredential(),
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
        resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
        workspace_name=os.environ["AZURE_WORKSPACE_NAME"],
    )

    job = client.jobs.get(args.job_name)
    print(f"job         : {job.name}")
    print(f"status      : {job.status}")
    print(f"studio_url  : {job.studio_url}")

    failed = False
    if job.status != "Completed":
        print(f"🛑 ジョブが Completed ではありません (status={job.status})", file=sys.stderr)
        failed = True

    # 2. test_macro_f1 metric via MLflow (requires azureml-mlflow plugin)
    import mlflow
    ws = client.workspaces.get(os.environ["AZURE_WORKSPACE_NAME"])
    mlflow.set_tracking_uri(ws.mlflow_tracking_uri)
    run = mlflow.get_run(job.name)
    metrics = run.data.metrics
    print(f"metrics     : {sorted(metrics.keys())}")
    if "test_macro_f1" not in metrics:
        print("🛑 test_macro_f1 メトリクスが記録されていません", file=sys.stderr)
        failed = True
    else:
        f1 = metrics["test_macro_f1"]
        print(f"test_macro_f1: {f1:.4f} (min={args.min_macro_f1})")
        if f1 < args.min_macro_f1:
            print(f"🛑 test_macro_f1={f1:.4f} が下限 {args.min_macro_f1} 未満です", file=sys.stderr)
            failed = True

    # 3. Download named output "model" and verify expected files exist
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            client.jobs.download(
                name=job.name,
                output_name="model",
                download_path=tmpdir,
            )
        except Exception as e:  # noqa: BLE001
            print(f"🛑 outputs.model のダウンロードに失敗: {e}", file=sys.stderr)
            return 1

        # SDK v2 stores under <tmpdir>/named-outputs/model/...
        root = Path(tmpdir)
        candidates = list(root.rglob("model.pt"))
        if not candidates:
            print(f"🛑 model.pt が output 中に存在しません (download_path={tmpdir})",
                  file=sys.stderr)
            failed = True
        else:
            base = candidates[0].parent
            print(f"output_dir  : {base}")
            for fname in EXPECTED_FILES:
                fpath = base / fname
                if fpath.exists():
                    print(f"  ✓ {fname} ({fpath.stat().st_size} bytes)")
                else:
                    print(f"  🛑 {fname} が見つかりません", file=sys.stderr)
                    failed = True

    if failed:
        return 1
    print("✅ すべての検証をパスしました")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
