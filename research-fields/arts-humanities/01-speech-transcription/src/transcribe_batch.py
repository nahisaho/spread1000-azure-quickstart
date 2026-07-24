"""Batch Transcription via Azure Speech REST API (api-version 2025-10-15).

Supports transcribing audio files stored in Azure Blob Storage.
Auth: DefaultAzureCredential (Entra) with fallback to AZURE_SPEECH_KEY.

S0-only limits:
  - 1 GB per content URL
  - 1000 content URLs per job
  - 10000 blobs per container SAS URL
  - 240-minute diarization limit per file

使い方:
  SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
  cd "$SCENARIO_DIR"
  python src/transcribe_batch.py \\
      --urls https://your-storage.blob.core.windows.net/audio/file.wav?<SAS> \\
      --locale ja-JP \\
      --diarization
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests  # type: ignore
from dotenv import load_dotenv

from _argtypes import locale_string, positive_int

API_VERSION = "2025-10-15"
MAX_POLL_MINUTES = 60


def _get_endpoint_and_headers() -> tuple[str, dict[str, str]]:
    region = os.environ.get("AZURE_SPEECH_REGION") or os.environ.get("SPEECH_REGION", "")
    if not region:
        sys.exit("[error] AZURE_SPEECH_REGION not set")

    # Entra preferred
    key = os.environ.get("AZURE_SPEECH_KEY") or os.environ.get("SPEECH_KEY", "")
    if key:
        headers = {"Ocp-Apim-Subscription-Key": key}
    else:
        try:
            from azure.identity import DefaultAzureCredential  # type: ignore
        except ImportError:
            sys.exit("[error] azure-identity not installed. Run: pip install azure-identity")
        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default").token
        headers = {"Authorization": f"Bearer {token}"}

    headers["Content-Type"] = "application/json"
    base = f"https://{region}.api.cognitive.microsoft.com/speechtotext"
    return base, headers


def submit_transcription(
    base_url: str,
    headers: dict[str, str],
    content_urls: list[str],
    locale: str,
    diarization: bool,
    ttl_hours: int,
    display_name: str,
) -> str:
    url = f"{base_url}/transcriptions:submit?api-version={API_VERSION}"
    payload: dict[str, Any] = {
        "contentUrls": content_urls,
        "locale": locale,
        "displayName": display_name,
        "properties": {
            "timeToLiveHours": ttl_hours,
            "diarizationEnabled": diarization,
            "wordLevelTimestampsEnabled": True,
            "punctuationMode": "DictatedAndAutomatic",
            "profanityFilterMode": "None",
        },
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    job_id = data.get("self", "").rstrip("/").split("/")[-1]
    if not job_id:
        sys.exit(f"[error] Could not extract job ID from response: {data}")
    print(f"[batch] Submitted transcription job: {job_id}")
    return job_id


def poll_transcription(
    base_url: str,
    headers: dict[str, str],
    job_id: str,
    max_minutes: int,
) -> dict:
    url = f"{base_url}/transcriptions/{job_id}?api-version={API_VERSION}"
    deadline = time.time() + max_minutes * 60
    delay = 5.0

    while time.time() < deadline:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "")
        print(f"[batch] Status: {status}")
        if status in ("Succeeded", "Failed"):
            return data
        # Exponential backoff capped at 60 s
        time.sleep(min(delay, 60.0))
        delay = min(delay * 1.5, 60.0)

    raise TimeoutError(f"Batch transcription job {job_id} did not complete within {max_minutes} minutes.")


def fetch_results(base_url: str, headers: dict[str, str], job_id: str) -> list[dict]:
    url = f"{base_url}/transcriptions/{job_id}/files?api-version={API_VERSION}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    files = resp.json().get("values", [])

    results: list[dict] = []
    for f in files:
        if f.get("kind") == "Transcription":
            dl_url = f.get("links", {}).get("contentUrl")
            if dl_url:
                r = requests.get(dl_url, timeout=60)
                r.raise_for_status()
                results.append(r.json())
    return results


def delete_transcription(base_url: str, headers: dict[str, str], job_id: str) -> None:
    url = f"{base_url}/transcriptions/{job_id}?api-version={API_VERSION}"
    try:
        resp = requests.delete(url, headers=headers, timeout=30)
        resp.raise_for_status()
        print(f"[batch] Deleted service-side job {job_id}")
    except Exception as exc:
        print(f"[warn] Could not delete job {job_id}: {exc}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Batch-transcribe audio files in Blob Storage using Azure Speech REST API."
    )
    ap.add_argument("--urls", nargs="+", required=True, metavar="URL",
                    help="SAS URLs to audio files in Blob Storage (max 1000, max 1 GB each)")
    ap.add_argument("--locale", default="ja-JP", type=locale_string,
                    help="BCP-47 locale (e.g. ja-JP)")
    ap.add_argument("--diarization", action="store_true",
                    help="Enable speaker diarization (240-min limit per file; S0 only)")
    ap.add_argument("--ttl-hours", type=positive_int, default=24,
                    help="Service-side result retention (hours, max 720). Default: 24")
    ap.add_argument("--max-poll-minutes", type=positive_int, default=MAX_POLL_MINUTES,
                    help="Maximum minutes to poll for completion. Default: 60")
    ap.add_argument("--display-name", default="spread1000-batch",
                    help="Human-readable job name")
    ap.add_argument("--retain-service-side", action="store_true",
                    help="Skip DELETE of the service-side transcription job on completion")
    args = ap.parse_args()

    if len(args.urls) > 1000:
        ap.error("Batch Transcription supports at most 1000 content URLs per job.")
    if args.ttl_hours > 720:
        ap.error("Maximum timeToLiveHours is 720.")

    load_dotenv()

    base_url, headers = _get_endpoint_and_headers()
    job_id = submit_transcription(
        base_url, headers, args.urls, args.locale, args.diarization,
        args.ttl_hours, args.display_name,
    )

    try:
        job_data = poll_transcription(base_url, headers, job_id, args.max_poll_minutes)
        if job_data.get("status") != "Succeeded":
            err = job_data.get("properties", {}).get("error", {})
            sys.exit(f"[error] Batch job failed: {err}")

        results = fetch_results(base_url, headers, job_id)

        outputs = Path(__file__).resolve().parent.parent / "outputs"
        outputs.mkdir(exist_ok=True)
        out_path = outputs / "transcript_batch.json"
        out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[done] {len(results)} result file(s) → {out_path}")

    finally:
        if not args.retain_service_side:
            delete_transcription(base_url, headers, job_id)


if __name__ == "__main__":
    main()
