"""多言語コーパスを Azure OpenAI text-embedding-3-large で埋め込み、
Azure AI Search インデックスに保存する。

デフォルトは Azure AI Search (推奨)。
ローカル FAISS フォールバックは --fallback-faiss で有効化。

使用例:
    # Azure AI Search (Bicep でプロビジョニング済み):
    python src/build_index.py \
        --search-endpoint https://<name>.search.windows.net \
        --embed-deployment text-embedding-3-large

    # ローカル FAISS (インターネット接続不要デモ):
    python src/build_index.py --fallback-faiss
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
)
from dotenv import load_dotenv
from openai import AzureOpenAI

from corpus import CORPUS

# テキスト埋め込みモデルの料金 (illustrative — 最新は aka.ms/aoai-pricing を確認)
_COST_PER_MILLION_TOKENS = 0.13
_COST_WARN_THRESHOLD = 1.0  # $1.00 で確認プロンプト
_CHARS_PER_TOKEN = 4         # 粗い概算
MAX_BATCH_SIZE = 64


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="多言語コーパスを埋め込み、Azure AI Search (or FAISS) インデックスに保存"
    )
    ap.add_argument(
        "--search-endpoint",
        default=os.environ.get("AZURE_SEARCH_ENDPOINT", ""),
        help="Azure AI Search エンドポイント (例: https://<name>.search.windows.net)",
    )
    ap.add_argument(
        "--index-name",
        default=os.environ.get("AZURE_SEARCH_INDEX_NAME", "multilingual-docs"),
        help="インデックス名 (デフォルト: multilingual-docs)",
    )
    ap.add_argument(
        "--embed-deployment",
        default=os.environ.get("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-large"),
        help="Azure OpenAI 埋め込みデプロイメント名",
    )
    ap.add_argument(
        "--embed-dim",
        type=int,
        default=int(os.environ.get("AZURE_OPENAI_EMBED_DIM", "3072")),
        help="埋め込み次元数 (デフォルト: 3072 for text-embedding-3-large)",
    )
    ap.add_argument(
        "--corpus",
        default=None,
        help="コーパス JSONL ファイルパス (未指定時は corpus.py の CORPUS を使用)",
    )
    ap.add_argument(
        "--max-documents",
        type=int,
        default=500,
        metavar="N",
        help="インデックス上限ドキュメント数 [1-100000] (デフォルト: 500)",
    )
    ap.add_argument(
        "--max-embed-tokens",
        type=int,
        default=500_000,
        metavar="N",
        help="埋め込みトークン上限 (デフォルト: 500000)",
    )
    ap.add_argument(
        "--max-index-bytes",
        type=int,
        default=100 * 1024 * 1024,
        metavar="N",
        help="インデックスバイト上限の目安 (デフォルト: 100MB)",
    )
    ap.add_argument(
        "--batch-size",
        type=int,
        default=16,
        metavar="N",
        help="埋め込みバッチサイズ [1-64] (デフォルト: 16)",
    )
    ap.add_argument(
        "--yes",
        action="store_true",
        help="コスト確認をスキップ",
    )
    ap.add_argument(
        "--fallback-faiss",
        action="store_true",
        help="Azure AI Search の代わりにローカル FAISS を使用 (オフラインデモ向け)",
    )
    ap.add_argument(
        "--store-full-text",
        action="store_true",
        help="FAISS フォールバック時に index_meta.json へ全文テキストを保存 (プライバシー注意)",
    )
    return ap.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    if not 1 <= args.max_documents <= 100_000:
        sys.exit("[error] --max-documents は [1, 100000] の範囲で指定してください")
    if args.max_embed_tokens < 1:
        sys.exit("[error] --max-embed-tokens は 1 以上で指定してください")
    if not 1 <= args.batch_size <= MAX_BATCH_SIZE:
        sys.exit(f"[error] --batch-size は [1, {MAX_BATCH_SIZE}] の範囲で指定してください")
    if not args.fallback_faiss and not args.search_endpoint:
        sys.exit(
            "[error] --search-endpoint (or AZURE_SEARCH_ENDPOINT) が未設定。\n"
            "  Azure AI Search 使用時は必須です。\n"
            "  ローカル FAISS を使う場合は --fallback-faiss を指定してください。"
        )


def _load_corpus(corpus_path: str | None) -> list[dict]:
    if corpus_path:
        p = Path(corpus_path)
        if not p.exists():
            sys.exit(f"[error] コーパスファイルが見つかりません: {corpus_path}")
        docs: list[dict] = []
        with p.open(encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    docs.append(json.loads(line))
                except json.JSONDecodeError as e:
                    sys.exit(f"[error] コーパス {corpus_path}:{lineno} JSON parse error: {e}")
        return docs
    return list(CORPUS)


def _estimate_tokens(docs: list[dict]) -> int:
    return sum(len(d.get("text", "")) // _CHARS_PER_TOKEN for d in docs)


def _check_cost_budget(docs: list[dict], args: argparse.Namespace) -> None:
    est_tokens = _estimate_tokens(docs)
    if est_tokens > args.max_embed_tokens:
        sys.exit(
            f"[error] 推定トークン数 {est_tokens:,} が上限 {args.max_embed_tokens:,} を超えています。\n"
            "  --max-embed-tokens を増やすか --max-documents でドキュメント数を減らしてください。"
        )
    est_cost = est_tokens / 1_000_000 * _COST_PER_MILLION_TOKENS
    print(
        f"[info] ドキュメント数: {len(docs)}, 推定トークン: {est_tokens:,}, "
        f"推定コスト: ~${est_cost:.4f} (目安: text-embedding-3-large ${_COST_PER_MILLION_TOKENS}/1M tokens)"
    )
    if est_cost > _COST_WARN_THRESHOLD and not args.yes:
        resp = input(f"[confirm] 推定コスト ${est_cost:.4f} > ${_COST_WARN_THRESHOLD}。続行しますか? [y/N] ")
        if resp.strip().lower() != "y":
            sys.exit("[abort] ユーザーにより中断されました")


def _make_aoai_client() -> AzureOpenAI:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    if not endpoint:
        sys.exit("[error] AZURE_OPENAI_ENDPOINT が未設定")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    if api_key:
        return AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )
    # キーなし → DefaultAzureCredential (Bicep RBAC 推奨)
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )


def _embed_batch(
    client: AzureOpenAI, texts: list[str], deployment: str, dim: int
) -> list[list[float]]:
    kwargs: dict[str, Any] = {"model": deployment, "input": texts}
    if dim != 3072:
        kwargs["dimensions"] = dim
    resp = client.embeddings.create(**kwargs)
    return [e.embedding for e in resp.data]


def _create_or_update_index(
    index_client: SearchIndexClient,
    index_name: str,
    embed_dim: int,
    aoai_endpoint: str,
    embed_deployment: str,
) -> None:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        # text フィールドは BM25 ハイブリッド検索に必要。フルテキストはインデックス内に保存される。
        # 機密データの場合は docs/07-ethics-and-limits.md の「データガバナンス」を参照。
        SearchableField(
            name="text",
            type=SearchFieldDataType.String,
            analyzer_name="standard.lucene",
        ),
        SimpleField(name="lang", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=embed_dim,
            vector_search_profile_name="hnsw-profile",
        ),
    ]
    vector_search = VectorSearch(
        profiles=[
            VectorSearchProfile(
                name="hnsw-profile",
                algorithm_configuration_name="hnsw-config",
                vectorizer_name="embed-vectorizer",
            )
        ],
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-config",
                parameters=HnswParameters(metric="cosine"),
            )
        ],
        vectorizers=[
            AzureOpenAIVectorizer(
                vectorizer_name="embed-vectorizer",
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=aoai_endpoint,
                    deployment_name=embed_deployment,
                    model_name=embed_deployment,
                ),
            )
        ],
    )
    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    index_client.create_or_update_index(index)
    print(f"[index] '{index_name}' を作成/更新しました")


def _build_azure_search(args: argparse.Namespace, docs: list[dict]) -> None:
    credential = DefaultAzureCredential()
    aoai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    if not aoai_endpoint:
        sys.exit("[error] AZURE_OPENAI_ENDPOINT が未設定")

    index_client = SearchIndexClient(endpoint=args.search_endpoint, credential=credential)
    _create_or_update_index(
        index_client, args.index_name, args.embed_dim, aoai_endpoint, args.embed_deployment
    )

    aoai_client = _make_aoai_client()
    texts = [d["text"] for d in docs]
    all_vectors: list[list[float]] = []
    print(f"[embed] {len(docs)} ドキュメントを {args.batch_size} 件ずつ埋め込み中...")
    for i in range(0, len(texts), args.batch_size):
        batch = texts[i : i + args.batch_size]
        vecs = _embed_batch(aoai_client, batch, args.embed_deployment, args.embed_dim)
        all_vectors.extend(vecs)
        print(f"[embed]   {min(i + args.batch_size, len(texts))}/{len(docs)}")

    search_docs = [
        {
            "id": d["id"],
            "text": d["text"],
            "lang": d.get("lang", ""),
            "content_vector": vec,
        }
        for d, vec in zip(docs, all_vectors)
    ]

    search_client = SearchClient(
        endpoint=args.search_endpoint,
        index_name=args.index_name,
        credential=credential,
    )
    upload_batch_size = 100
    for i in range(0, len(search_docs), upload_batch_size):
        batch = search_docs[i : i + upload_batch_size]
        results = search_client.upload_documents(documents=batch)
        failed = [r for r in results if not r.succeeded]
        for f in failed:
            print(f"[warn] upload failed: key={f.key} error={f.error_message}", file=sys.stderr)
        print(f"[upload]   {min(i + upload_batch_size, len(search_docs))}/{len(search_docs)}")

    print(
        f"[done] Azure AI Search インデックス '{args.index_name}' に "
        f"{len(search_docs)} ドキュメントを登録しました"
    )


def _build_faiss_fallback(args: argparse.Namespace, docs: list[dict]) -> None:
    """FAISS ローカルフォールバック (--fallback-faiss 指定時のみ)。

    プライバシー: index_meta.json には id + text SHA-256 ハッシュのみ保存。
    全文が必要な場合は --store-full-text を指定 (機密データには不推奨)。
    """
    try:
        import faiss
        import numpy as np
    except ImportError:
        sys.exit("[error] faiss-cpu / numpy が未インストール。pip install faiss-cpu numpy")

    aoai_client = _make_aoai_client()
    texts = [d["text"] for d in docs]
    all_vectors: list[list[float]] = []
    print(f"[embed] {len(docs)} ドキュメントを {args.batch_size} 件ずつ埋め込み中 (FAISS fallback)...")
    for i in range(0, len(texts), args.batch_size):
        batch = texts[i : i + args.batch_size]
        vecs = _embed_batch(aoai_client, batch, args.embed_deployment, args.embed_dim)
        all_vectors.extend(vecs)
        print(f"[embed]   {min(i + args.batch_size, len(texts))}/{len(docs)}")

    vectors = np.array(all_vectors, dtype=np.float32)
    faiss.normalize_L2(vectors)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    faiss.write_index(index, str(data_dir / "index.faiss"))

    if args.store_full_text:
        print("[warn] --store-full-text: テキスト全文を index_meta.json に保存します (機密データには不推奨)")
        meta: list[dict] = [
            {"id": d["id"], "lang": d.get("lang", ""), "text": d["text"]}
            for d in docs
        ]
    else:
        # デフォルト: id と sha256 ハッシュのみ。元テキストは corpus ファイルを参照。
        meta = [
            {
                "id": d["id"],
                "lang": d.get("lang", ""),
                "text_sha256": hashlib.sha256(d["text"].encode()).hexdigest(),
            }
            for d in docs
        ]

    (data_dir / "index_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"[done] data/index.faiss ({index.ntotal} vectors, dim={dim})\n"
        "  メタデータ: id + sha256 ハッシュのみ保存 (元テキストはコーパスファイルを参照)"
        if not args.store_full_text
        else f"[done] data/index.faiss ({index.ntotal} vectors, dim={dim}) + 全文テキスト保存済み"
    )


def main() -> None:
    load_dotenv()
    args = _parse_args()
    _validate_args(args)

    docs = _load_corpus(args.corpus)
    if not docs:
        sys.exit("[error] コーパスが空です")

    if len(docs) > args.max_documents:
        print(
            f"[warn] ドキュメント数 {len(docs)} > 上限 {args.max_documents}。"
            f"先頭 {args.max_documents} 件を使用します。"
        )
        docs = docs[: args.max_documents]

    _check_cost_budget(docs, args)

    if args.fallback_faiss:
        _build_faiss_fallback(args, docs)
    else:
        _build_azure_search(args, docs)


if __name__ == "__main__":
    main()
