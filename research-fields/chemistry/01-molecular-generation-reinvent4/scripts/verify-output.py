"""Verify a completed AML molecular generation job.

Usage:
  pip install "azure-ai-ml==1.34.1" "azure-identity>=1.19.0" \
              "mlflow==2.16.2" "azureml-mlflow==1.57.0"
  python scripts/verify-output.py <job_name> [--min-valid-ratio 0.5]

Env vars required: AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_WORKSPACE_NAME.

Checks:
  1. job status == "Completed"
  2. `valid_ratio`, `unique_ratio`, `mean_qed` metrics present via MLflow
  3. Downloads named output `molecules` and verifies `sampled.csv`,
     `scored.csv`, `top20.png` all exist and are non-empty.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

EXPECTED_FILES = ["sampled.csv", "scored.csv", "top20.png"]
EXPECTED_METRICS = ["valid_ratio", "unique_ratio", "mean_qed"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_name")
    parser.add_argument("--min-valid-ratio", type=float, default=0.5,
                        help="Lower bound for valid_ratio (default 0.5)")
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

    # Metric verification (requires azureml-mlflow plugin to speak azureml:// URI)
    import mlflow
    ws = client.workspaces.get(os.environ["AZURE_WORKSPACE_NAME"])
    mlflow.set_tracking_uri(ws.mlflow_tracking_uri)
    run = mlflow.get_run(job.name)
    metrics = run.data.metrics
    print(f"metrics     : {sorted(metrics.keys())}")
    for m in EXPECTED_METRICS:
        if m not in metrics:
            print(f"🛑 メトリクス '{m}' が未記録", file=sys.stderr)
            failed = True
    if "valid_ratio" in metrics:
        vr = metrics["valid_ratio"]
        print(f"valid_ratio : {vr:.3f} (min={args.min_valid_ratio})")
        if vr < args.min_valid_ratio:
            print(f"🛑 valid_ratio={vr:.3f} が下限 {args.min_valid_ratio} 未満", file=sys.stderr)
            failed = True

    # Output file verification
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            client.jobs.download(
                name=job.name,
                output_name="molecules",
                download_path=tmpdir,
            )
        except Exception as e:  # noqa: BLE001
            print(f"🛑 outputs.molecules ダウンロードに失敗: {e}", file=sys.stderr)
            return 1

        root = Path(tmpdir)
        # SDK v2 stores under <tmpdir>/named-outputs/molecules/...
        found_any = list(root.rglob(EXPECTED_FILES[0]))
        if not found_any:
            print(f"🛑 sampled.csv が output 中に存在しません (download_path={tmpdir})",
                  file=sys.stderr)
            failed = True
        else:
            base = found_any[0].parent
            print(f"output_dir  : {base}")
            for fname in EXPECTED_FILES:
                fp = base / fname
                if fp.exists() and fp.stat().st_size > 0:
                    print(f"  ✓ {fname} ({fp.stat().st_size} bytes)")
                else:
                    print(f"  🛑 {fname} が見つからないか空", file=sys.stderr)
                    failed = True

    if failed:
        return 1
    print("✅ すべての検証をパスしました")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
