"""PDF → Markdown (Document Intelligence) → JSON (Azure OpenAI Structured Outputs).

Usage:
  python extract.py --input data/demo-court.pdf --schema court --output data/output/x.json

Auth: DefaultAzureCredential for both services (disableLocalAuth: true).
Env: DOCUMENT_INTELLIGENCE_ENDPOINT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT,
     AZURE_OPENAI_LOCATION, AZURE_OPENAI_DEPLOYMENT_TYPE.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (
    AnalyzeDocumentRequest,
    DocumentContentFormat,
)
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from schemas import SCHEMAS, SYSTEM_PROMPTS


DOC_INTEL_PRICE_PER_PAGE = 0.010  # USD, japaneast S0 prebuilt-layout, 2026 list
AOAI_INPUT_PRICE_PER_M = 0.75     # USD/1M tokens, gpt-5.4-mini list (verify at billing time)
AOAI_OUTPUT_PRICE_PER_M = 4.50


def sha256_short(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_pdf(path: Path) -> bytes:
    data = path.read_bytes()
    if not data.startswith(b"%PDF"):
        raise SystemExit(f"ERROR: '{path}' is not a PDF (missing %PDF header).")
    if len(data) > 50 * 1024 * 1024:
        raise SystemExit(
            f"ERROR: '{path}' is >50 MB. Doc Intelligence S0 limit is 500 MB but this "
            "quickstart's cost estimate assumes small documents."
        )
    return data


def analyze_layout(client: DocumentIntelligenceClient, pdf_bytes: bytes) -> dict:
    poller = client.begin_analyze_document(
        "prebuilt-layout",
        AnalyzeDocumentRequest(bytes_source=pdf_bytes),
        output_content_format=DocumentContentFormat.MARKDOWN,
    )
    result = poller.result()
    return {
        "markdown": result.content or "",
        "n_pages": len(result.pages or []),
        "n_tables": len(result.tables or []),
    }


def make_aoai_client() -> OpenAI:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    if not endpoint:
        raise SystemExit("ERROR: AZURE_OPENAI_ENDPOINT is not set.")
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    return OpenAI(
        base_url=f"{endpoint}/openai/v1/",
        api_key=token_provider,
        max_retries=5,
    )


def extract_structured(
    client: OpenAI,
    deployment: str,
    schema_name: str,
    markdown: str,
    reasoning_effort: str,
    max_completion_tokens: int,
) -> tuple[dict, dict]:
    schema_cls = SCHEMAS[schema_name]
    system_prompt = SYSTEM_PROMPTS[schema_name]

    # GPT-5 series does not accept temperature. We deliberately omit it.
    result = client.beta.chat.completions.parse(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": markdown},
        ],
        response_format=schema_cls,
        reasoning_effort=reasoning_effort,
        max_completion_tokens=max_completion_tokens,
    )
    message = result.choices[0].message
    if message.refusal:
        raise RuntimeError(f"AOAI refusal: {message.refusal}")
    if message.parsed is None:
        raise RuntimeError("AOAI returned no parsed output (possible truncation).")

    usage = {
        "model": result.model,
        "system_fingerprint": result.system_fingerprint,
        "input_tokens": result.usage.prompt_tokens if result.usage else None,
        "output_tokens": result.usage.completion_tokens if result.usage else None,
    }
    return message.parsed.model_dump(), usage


def estimate_cost(n_pages: int, input_tokens: int | None, output_tokens: int | None) -> dict:
    doc_cost = n_pages * DOC_INTEL_PRICE_PER_PAGE
    aoai_input = (input_tokens or 0) * AOAI_INPUT_PRICE_PER_M / 1_000_000
    aoai_output = (output_tokens or 0) * AOAI_OUTPUT_PRICE_PER_M / 1_000_000
    return {
        "doc_intel_usd": round(doc_cost, 6),
        "aoai_input_usd": round(aoai_input, 6),
        "aoai_output_usd": round(aoai_output, 6),
        "total_usd": round(doc_cost + aoai_input + aoai_output, 6),
        "note": "List price estimate; verify with Azure Pricing Calculator.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to input PDF.")
    ap.add_argument("--schema", required=True, choices=sorted(SCHEMAS.keys()))
    ap.add_argument("--output", required=True, help="Path to output JSON.")
    ap.add_argument(
        "--reasoning-effort",
        default="low",
        choices=["low", "medium", "high"],
    )
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    doc_endpoint = os.environ.get("DOCUMENT_INTELLIGENCE_ENDPOINT", "").rstrip("/")
    if not doc_endpoint:
        print("ERROR: DOCUMENT_INTELLIGENCE_ENDPOINT is not set.", file=sys.stderr)
        return 2
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip()
    if not deployment:
        print("ERROR: AZURE_OPENAI_DEPLOYMENT is not set.", file=sys.stderr)
        return 2
    location = os.environ.get("AZURE_OPENAI_LOCATION", "").strip()
    deployment_type = os.environ.get("AZURE_OPENAI_DEPLOYMENT_TYPE", "").strip()
    if not location or not deployment_type:
        print(
            "ERROR: AZURE_OPENAI_LOCATION and AZURE_OPENAI_DEPLOYMENT_TYPE must be set "
            "(data-residency metadata). See docs/02-provision.md for how to derive them.",
            file=sys.stderr,
        )
        return 2

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[extract] loading {input_path}", flush=True)
    pdf_bytes = load_pdf(input_path)

    print("[extract] calling Document Intelligence (prebuilt-layout)...", flush=True)
    started_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
    doc_client = DocumentIntelligenceClient(
        endpoint=doc_endpoint,
        credential=DefaultAzureCredential(),
    )
    layout = analyze_layout(doc_client, pdf_bytes)
    print(f"[extract]   pages={layout['n_pages']}  tables={layout['n_tables']}")

    # Save markdown intermediate for debugging + audit
    md_path = output_path.with_suffix(".markdown.txt")
    md_path.write_text(layout["markdown"], encoding="utf-8")
    print(f"[extract]   wrote {md_path} ({len(layout['markdown'])} chars)")

    if args.verbose:
        print("--- MARKDOWN (first 500 chars) ---")
        print(layout["markdown"][:500])
        print("---")

    print(f"[extract] calling Azure OpenAI ({deployment}, effort={args.reasoning_effort})...", flush=True)
    aoai = make_aoai_client()
    parsed, usage = extract_structured(
        aoai,
        deployment,
        args.schema,
        layout["markdown"],
        args.reasoning_effort,
        args.max_tokens,
    )
    finished_at = _dt.datetime.now(_dt.timezone.utc).isoformat()

    output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2))
    print(f"[extract] wrote {output_path}")

    cost = estimate_cost(layout["n_pages"], usage["input_tokens"], usage["output_tokens"])
    manifest = {
        "input_pdf": str(input_path),
        "input_pdf_sha256_16": hashlib.sha256(pdf_bytes).hexdigest()[:16],
        "schema_name": args.schema,
        "schema_sha256_16": sha256_short(json.dumps(SCHEMAS[args.schema].model_json_schema(), sort_keys=True)),
        "system_prompt_sha256_16": sha256_short(SYSTEM_PROMPTS[args.schema]),
        "doc_intel_endpoint": doc_endpoint,
        "aoai_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/"),
        "aoai_deployment": deployment,
        "aoai_location": location,
        "aoai_deployment_type": deployment_type,
        "reasoning_effort": args.reasoning_effort,
        "max_completion_tokens": args.max_tokens,
        "n_pages": layout["n_pages"],
        "n_tables": layout["n_tables"],
        "usage": usage,
        "cost_estimate": cost,
        "started_at": started_at,
        "finished_at": finished_at,
    }
    manifest_path = output_path.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"[extract] wrote {manifest_path}")
    print(f"[extract] estimated cost: ${cost['total_usd']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
