"""AOAI Embedding client — used by embed.py and label_clusters.py."""
from __future__ import annotations

import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI


def require_env(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        raise SystemExit(
            f"ERROR: environment variable {key} is not set. "
            f"Run infra/deploy.sh to generate .env, then `source .env` or use python-dotenv."
        )
    return val


def make_client() -> OpenAI:
    """Return an OpenAI client authenticated with Managed Identity / AAD."""
    endpoint = require_env("AZURE_OPENAI_ENDPOINT").rstrip("/")
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://ai.azure.com/.default",
    )
    # v1 API endpoint — no dated api-version needed as of Aug 2025.
    return OpenAI(
        base_url=f"{endpoint}/openai/v1/",
        api_key=token_provider,
        max_retries=5,
    )
