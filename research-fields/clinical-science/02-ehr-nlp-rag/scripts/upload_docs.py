"""Upload synthetic clinical notes to Azure Blob Storage.

Usage:
    python scripts/upload_docs.py

Reads config from environment (set with `set -a && source .env && set +a`):
    STORAGE_ACCOUNT, DOCS_CONTAINER

Uses DefaultAzureCredential (falls back to `az login`).
Skips files that already exist in the container.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "inputs" / "sample-notes"


def main() -> int:
    storage_account = os.environ.get("STORAGE_ACCOUNT")
    container = os.environ.get("DOCS_CONTAINER", "documents")
    if not storage_account:
        print("ERROR: STORAGE_ACCOUNT env var not set. Did you `source .env`?", file=sys.stderr)
        return 1

    if not SAMPLE_DIR.is_dir():
        print(f"ERROR: sample notes dir not found: {SAMPLE_DIR}", file=sys.stderr)
        return 1

    endpoint = f"https://{storage_account}.blob.core.windows.net"
    credential = DefaultAzureCredential()
    client = BlobServiceClient(account_url=endpoint, credential=credential)
    container_client = client.get_container_client(container)

    files = sorted(SAMPLE_DIR.glob("*.md"))
    if not files:
        print(f"WARN: no .md files found under {SAMPLE_DIR}")
        return 0

    local_names = {f.name for f in files}
    uploaded = 0
    updated = 0
    unchanged = 0
    for f in files:
        blob_name = f.name
        blob_client = container_client.get_blob_client(blob_name)
        data = f.read_bytes()
        exists = blob_client.exists()
        if exists:
            # Overwrite only if content changed so downstream reindex stays consistent.
            props = blob_client.get_blob_properties()
            remote_len = props.size
            if remote_len == len(data):
                # Compare bytes to avoid needless re-upload (small files here).
                remote = blob_client.download_blob().readall()
                if remote == data:
                    print(f"  [unchanged] {blob_name}")
                    unchanged += 1
                    continue
            blob_client.upload_blob(data, overwrite=True)
            print(f"  [updated] {blob_name} ({len(data)} bytes)")
            updated += 1
        else:
            blob_client.upload_blob(data, overwrite=False)
            print(f"  [uploaded] {blob_name} ({len(data)} bytes)")
            uploaded += 1

    # Sync deletions: any blob in the container that is not in inputs/sample-notes/ is stale
    # (soft-delete keeps them for 7 days per infra/main.bicep — recoverable via `az storage blob undelete`).
    deleted = 0
    for blob in container_client.list_blobs():
        if blob.name.endswith(".md") and blob.name not in local_names:
            container_client.delete_blob(blob.name)
            print(f"  [deleted] {blob.name} (no longer present locally; recoverable for 7 days)")
            deleted += 1

    print(f"\nDone. uploaded={uploaded}, updated={updated}, unchanged={unchanged}, deleted={deleted}, total_local={len(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
