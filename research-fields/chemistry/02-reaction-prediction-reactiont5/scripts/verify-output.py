"""Verify a completed reaction-t5 job: check status, MLflow metrics, and output files.

Usage:
  python scripts/verify-output.py <RUN_NAME>
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from subprocess import check_output

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

EXPECTED_FILES = ["predictions.csv"]


def _cli(cmd: str) -> str:
    return check_output(cmd, shell=True, text=True).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_name", help="AML job name (e.g., bright_ocean_abc123)")
    ap.add_argument("--subscription-id", default=None)
    ap.add_argument("--resource-group", default=None)
    ap.add_argument("--workspace-name", default=None)
    args = ap.parse_args()

    sub = args.subscription_id or _cli("az account show --query id -o tsv")
    rg = args.resource_group or _cli(
        "az configure -l --query \"[?name=='group'].value|[0]\" -o tsv"
    )
    ws = args.workspace_name or _cli(
        "az configure -l --query \"[?name=='workspace'].value|[0]\" -o tsv"
    )
    if not rg or not ws:
        print(
            "ERROR: could not resolve default RG/workspace. "
            "Run 'az configure --defaults group=... workspace=...' first, "
            "or pass --resource-group/--workspace-name.",
            file=sys.stderr,
        )
        return 2

    client = MLClient(DefaultAzureCredential(), sub, rg, ws)
    job = client.jobs.get(args.run_name)
    print(f"Job status: {job.status}")
    if job.status != "Completed":
        print("Job is not Completed; nothing else to check.", file=sys.stderr)
        return 1

    import mlflow

    mlflow.set_tracking_uri(client.workspaces.get(ws).mlflow_tracking_uri)
    run = mlflow.get_run(args.run_name)
    metrics = run.data.metrics
    print("MLflow metrics:")
    missing_metrics: list[str] = []
    # top1_accuracy is only expected when the reference CSV actually contained
    # at least one non-empty reference_product. Detect that via num_scored so
    # the no-reference workflow (which docs/03-prepare-data.md explicitly
    # allows) doesn't fail verification.
    num_scored = metrics.get("num_scored")
    required = ["num_reactions", "valid_ratio"]
    if num_scored is not None and num_scored > 0:
        required.append("top1_accuracy")
    for k in ("num_reactions", "num_scored", "num_unscored", "valid_ratio", "top1_accuracy"):
        if k in metrics:
            print(f"  {k:<15} = {metrics[k]}")
        elif k in required:
            print(f"  {k:<15} = (missing)")
            missing_metrics.append(k)
        else:
            print(f"  {k:<15} = (not applicable — no scored rows)")

    print("Output files:")
    with tempfile.TemporaryDirectory() as tmp:
        client.jobs.download(
            name=args.run_name,
            output_name="predictions",
            download_path=tmp,
        )
        base = Path(tmp)
        ok = True
        for fname in EXPECTED_FILES:
            found = list(base.rglob(fname))
            if not found:
                print(f"  ✗ {fname} (missing)")
                ok = False
                continue
            fpath = found[0]
            size = fpath.stat().st_size
            if size == 0:
                print(f"  ✗ {fname} (empty)")
                ok = False
                continue
            try:
                lines = sum(1 for _ in fpath.open())
                print(f"  ✓ {fname:<20} ({lines - 1} rows)")
            except Exception:
                print(f"  ✓ {fname:<20} ({size} bytes)")
        if missing_metrics:
            print(
                f"ERROR: expected MLflow metrics not logged: {', '.join(missing_metrics)}",
                file=sys.stderr,
            )
            return 1
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
