"""Create Azure AI Search index, then ingest and embed docs from Blob Storage.

Usage:
    python scripts/index_docs.py

Env (from .env):
    SEARCH_ENDPOINT, SEARCH_INDEX (default: ehr-notes)
    STORAGE_ACCOUNT, DOCS_CONTAINER
    OPENAI_ENDPOINT, OPENAI_EMBED_DEPLOYMENT (default: text-embedding-3-large)

Approach:
- Simple chunk-and-embed pipeline (~ 512-token chunks with 64-token overlap).
- Uses Azure OpenAI embeddings via API key-less AAD auth (DefaultAzureCredential).
- Creates a vector + BM25 hybrid index with per-chunk fields.
- For production, consider AI Search built-in indexer + skillsets (see docs/).
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Iterable

import tiktoken
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI


CHUNK_TOKENS = 512
CHUNK_OVERLAP = 64
EMBEDDING_DIM = 3072  # text-embedding-3-large

INDEX_NAME_DEFAULT = "ehr-notes"


def env(key: str, default: str | None = None, required: bool = True) -> str:
    v = os.environ.get(key, default)
    if required and not v:
        print(f"ERROR: env var {key} not set. Did you `source .env`?", file=sys.stderr)
        sys.exit(1)
    return v  # type: ignore[return-value]


def build_index(index_client: SearchIndexClient, name: str) -> None:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="source_blob", type=SearchFieldDataType.String, filterable=True, facetable=True, analyzer_name="ja.microsoft"),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="ja.microsoft"),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIM,
            vector_search_profile_name="default-hnsw",
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="default-algorithm",
                parameters=HnswParameters(m=4, ef_construction=400, ef_search=500, metric="cosine"),
            )
        ],
        profiles=[VectorSearchProfile(name="default-hnsw", algorithm_configuration_name="default-algorithm")],
    )
    semantic = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="default-semantic",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")],
                    title_field=SemanticField(field_name="source_blob"),
                ),
            )
        ]
    )
    idx = SearchIndex(name=name, fields=fields, vector_search=vector_search, semantic_search=semantic)
    try:
        index_client.create_or_update_index(idx)
        print(f"  [ok] index '{name}' created/updated")
    except Exception as e:
        print(f"ERROR creating index: {e}", file=sys.stderr)
        raise


def chunk_text(text: str, encoder: tiktoken.Encoding) -> Iterable[str]:
    tokens = encoder.encode(text)
    step = CHUNK_TOKENS - CHUNK_OVERLAP
    for start in range(0, len(tokens), step):
        piece = tokens[start : start + CHUNK_TOKENS]
        if not piece:
            break
        yield encoder.decode(piece)
        if start + CHUNK_TOKENS >= len(tokens):
            break


def embed(client: AzureOpenAI, deployment: str, texts: list[str]) -> list[list[float]]:
    # Azure OpenAI embeddings support up to 2048 inputs per call; here we send small batches.
    resp = client.embeddings.create(model=deployment, input=texts)
    return [d.embedding for d in resp.data]


def blob_id(blob_name: str) -> str:
    """Deterministic, collision-resistant ID for a source blob.

    AI Search keys accept letters/digits/underscore/dash/equal only, so we combine
    an ASCII-slug prefix (for human readability) with a short SHA-256 suffix of the
    full blob name (for collision resistance with non-ASCII filenames like
    ``肺炎.md`` and ``心筋梗塞.md`` that would otherwise slugify to the same ``_md``).
    """
    slug = re.sub(r"[^A-Za-z0-9_\-=]+", "_", blob_name).strip("_") or "doc"
    digest = hashlib.sha256(blob_name.encode("utf-8")).hexdigest()[:12]
    return f"{slug}_{digest}"


def main() -> int:
    search_endpoint = env("SEARCH_ENDPOINT")
    index_name = env("SEARCH_INDEX", INDEX_NAME_DEFAULT, required=False) or INDEX_NAME_DEFAULT
    storage_account = env("STORAGE_ACCOUNT")
    container = env("DOCS_CONTAINER", "documents", required=False) or "documents"
    openai_endpoint = env("OPENAI_ENDPOINT")
    embed_deployment = env("OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-large", required=False) \
        or "text-embedding-3-large"

    credential = DefaultAzureCredential()

    # --- Build index ---
    print(f"==> Creating/updating index '{index_name}'...")
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    build_index(index_client, index_name)

    # --- Fetch docs from blob ---
    print(f"==> Downloading blobs from {storage_account}/{container} ...")
    blob_client = BlobServiceClient(
        account_url=f"https://{storage_account}.blob.core.windows.net",
        credential=credential,
    )
    container_client = blob_client.get_container_client(container)

    documents = []
    for blob in container_client.list_blobs():
        raw = container_client.download_blob(blob.name).readall().decode("utf-8", errors="replace")
        documents.append((blob.name, raw))
        print(f"  [read] {blob.name} ({len(raw)} chars)")

    if not documents:
        print("ERROR: no blobs found. Run `python scripts/upload_docs.py` first.", file=sys.stderr)
        return 1

    # --- Chunk + embed ---
    print("==> Chunking and embedding...")
    encoder = tiktoken.get_encoding("cl100k_base")

    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
    openai_client = AzureOpenAI(
        azure_endpoint=openai_endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2024-10-21",
    )

    docs_to_upload: list[dict] = []
    for blob_name, text in documents:
        chunks = list(chunk_text(text, encoder))
        vectors = embed(openai_client, embed_deployment, chunks)
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
            docs_to_upload.append(
                {
                    "id": f"{blob_id(blob_name)}__{idx}",
                    "source_blob": blob_name,
                    "chunk_index": idx,
                    "content": chunk,
                    "content_vector": vec,
                }
            )
        print(f"  [embed] {blob_name}: {len(chunks)} chunks")

    # --- Compute deterministic new IDs so we can delete only truly-stale entries AFTER upload ---
    new_ids_by_blob: dict[str, set[str]] = {}
    for d in docs_to_upload:
        new_ids_by_blob.setdefault(d["source_blob"], set()).add(d["id"])

    search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
    current_blob_names = {blob_name for blob_name, _ in documents}

    # --- Upload (mergeOrUpload semantics: same IDs are overwritten atomically) ---
    print(f"==> Uploading {len(docs_to_upload)} chunks to index '{index_name}' (merge-or-upload)...")
    BATCH = 500
    upload_failures = 0
    for i in range(0, len(docs_to_upload), BATCH):
        batch = docs_to_upload[i : i + BATCH]
        result = search_client.merge_or_upload_documents(batch)
        succeeded = sum(1 for r in result if r.succeeded)
        for r in result:
            if not r.succeeded:
                upload_failures += 1
                print(f"  ERROR uploading id={r.key}: {r.error_message}", file=sys.stderr)
        print(f"  batch {i // BATCH + 1}: {succeeded}/{len(batch)} succeeded")

    if upload_failures:
        # Fail fast: do NOT delete anything if uploads were incomplete — better to have
        # duplicate chunks than to destroy valid data before its replacement lands.
        print(
            f"\nFAILED. upload_failures={upload_failures}. "
            "No stale/orphan deletions performed (index left in pre-upload+new-uploads state).",
            file=sys.stderr,
        )
        return 1

    # --- Purge chunks for CURRENT blobs whose IDs no longer appear (e.g., blob shrank) ---
    print("==> Purging stale chunks whose IDs are no longer produced by current source blobs...")
    purge_failures = 0
    stale_total = 0
    for blob_name in current_blob_names:
        indexed_ids: list[str] = []
        # OData: escape single quotes by doubling them per OData v4 rules
        odata_blob = blob_name.replace("'", "''")
        for hit in search_client.search(
            search_text="*",
            filter=f"source_blob eq '{odata_blob}'",
            select=["id"],
            top=1000,
            include_total_count=False,
        ):
            indexed_ids.append(hit["id"])
        stale = [{"id": i} for i in indexed_ids if i not in new_ids_by_blob.get(blob_name, set())]
        if stale:
            for i in range(0, len(stale), 500):
                res = search_client.delete_documents(stale[i : i + 500])
                for r in res:
                    if not r.succeeded:
                        purge_failures += 1
                        print(f"  ERROR purging id={r.key}: {r.error_message}", file=sys.stderr)
            stale_total += len(stale)
            print(f"  [purged] {blob_name}: {len(stale)} stale chunk(s)")

    # --- Reconcile: delete chunks whose source_blob no longer exists in inputs/sample-notes/ ---
    print("==> Reconciling: removing chunks for source blobs no longer present locally...")
    all_indexed_blobs: set[str] = set()
    for hit in search_client.search(
        search_text="*",
        select=["source_blob"],
        top=1000,
        include_total_count=False,
    ):
        all_indexed_blobs.add(hit["source_blob"])
    orphaned_blobs = all_indexed_blobs - current_blob_names
    orphan_total = 0
    for blob_name in orphaned_blobs:
        orphan_ids: list[dict] = []
        odata_blob = blob_name.replace("'", "''")
        for hit in search_client.search(
            search_text="*",
            filter=f"source_blob eq '{odata_blob}'",
            select=["id"],
            top=1000,
            include_total_count=False,
        ):
            orphan_ids.append({"id": hit["id"]})
        if orphan_ids:
            for i in range(0, len(orphan_ids), 500):
                res = search_client.delete_documents(orphan_ids[i : i + 500])
                for r in res:
                    if not r.succeeded:
                        purge_failures += 1
                        print(f"  ERROR reconciling id={r.key}: {r.error_message}", file=sys.stderr)
            orphan_total += len(orphan_ids)
            print(f"  [reconciled] {blob_name}: {len(orphan_ids)} orphan chunk(s) removed")

    if purge_failures:
        print(f"\nFAILED. purge_failures={purge_failures} (uploads succeeded but cleanup failed)", file=sys.stderr)
        return 1

    print(f"\nDone. uploaded={len(docs_to_upload)}, stale_purged={stale_total}, orphans_removed={orphan_total}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
