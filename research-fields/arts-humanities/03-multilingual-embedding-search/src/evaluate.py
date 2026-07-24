"""多言語検索の評価スクリプト。

per-language + macro NDCG@10, MRR@10, Recall@10 を計算。
data/eval_queries.jsonl に評価クエリ + 正解 ID を用意。

使用例:
    # Azure AI Search:
    python src/evaluate.py

    # FAISS フォールバック:
    python src/evaluate.py --fallback-faiss
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from openai import AzureOpenAI

# 合格しきい値 (デモ用。本番は labeled validation set から決定)
PASS_THRESHOLD_NDCG = 0.5
EVAL_K = 10


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="多言語検索 NDCG/MRR/Recall 評価")
    ap.add_argument(
        "--eval-file",
        default=str(Path(__file__).resolve().parent.parent / "data" / "eval_queries.jsonl"),
        help="評価クエリファイル (JSONL: {query, lang, relevant_ids})",
    )
    ap.add_argument(
        "--search-endpoint",
        default=os.environ.get("AZURE_SEARCH_ENDPOINT", ""),
    )
    ap.add_argument(
        "--index-name",
        default=os.environ.get("AZURE_SEARCH_INDEX_NAME", "multilingual-docs"),
    )
    ap.add_argument(
        "--embed-deployment",
        default=os.environ.get("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-large"),
    )
    ap.add_argument(
        "--embed-dim",
        type=int,
        default=int(os.environ.get("AZURE_OPENAI_EMBED_DIM", "3072")),
    )
    ap.add_argument("--k", type=int, default=EVAL_K, help=f"評価カットオフ (デフォルト: {EVAL_K})")
    ap.add_argument("--fallback-faiss", action="store_true")
    return ap.parse_args()


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
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )


def _embed(client: AzureOpenAI, text: str, deployment: str, dim: int) -> list[float]:
    kwargs: dict[str, Any] = {"model": deployment, "input": [text]}
    if dim != 3072:
        kwargs["dimensions"] = dim
    return client.embeddings.create(**kwargs).data[0].embedding


def _dcg(rel_list: list[int]) -> float:
    return sum(r / math.log2(i + 2) for i, r in enumerate(rel_list))


def _ndcg(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    rel = [1 if doc_id in relevant_ids else 0 for doc_id in retrieved_ids[:k]]
    ideal = sorted(rel, reverse=True)
    dcg = _dcg(rel)
    idcg = _dcg(ideal)
    return dcg / idcg if idcg > 0 else 0.0


def _mrr(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    for rank, doc_id in enumerate(retrieved_ids[:k], 1):
        if doc_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def _recall(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    hit = sum(1 for doc_id in retrieved_ids[:k] if doc_id in relevant_ids)
    return hit / len(relevant_ids)


def _retrieve_azure(
    query: str,
    k: int,
    search_client: SearchClient,
    aoai_client: AzureOpenAI,
    embed_deployment: str,
    embed_dim: int,
) -> list[str]:
    qvec = _embed(aoai_client, query, embed_deployment, embed_dim)
    results = search_client.search(
        search_text=query,
        vector_queries=[VectorizedQuery(vector=qvec, k_nearest_neighbors=k, fields="content_vector")],
        select=["id"],
        top=k,
    )
    return [r["id"] for r in results]


def _retrieve_faiss(
    query: str,
    k: int,
    index: Any,
    meta: list[dict],
    aoai_client: AzureOpenAI,
    embed_deployment: str,
    embed_dim: int,
) -> list[str]:
    import numpy as np
    import faiss as faiss_lib

    qvec = _embed(aoai_client, query, embed_deployment, embed_dim)
    qvec_np = np.array([qvec], dtype=np.float32)
    faiss_lib.normalize_L2(qvec_np)
    eff_k = min(k, index.ntotal)
    scores, ids = index.search(qvec_np, eff_k)
    retrieved = []
    for i in ids[0]:
        if i == -1 or not (0 <= i < len(meta)):
            continue
        retrieved.append(meta[i]["id"])
    return retrieved


def main() -> None:
    load_dotenv()
    args = _parse_args()

    eval_path = Path(args.eval_file)
    if not eval_path.exists():
        sys.exit(f"[error] 評価ファイルが見つかりません: {eval_path}")

    queries: list[dict] = []
    with eval_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                queries.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.exit(f"[error] {eval_path}:{lineno}: {e}")

    if not queries:
        sys.exit("[error] 評価クエリが空です")

    aoai_client = _make_aoai_client()

    # 検索クライアント準備
    search_client: Any = None
    faiss_index: Any = None
    faiss_meta: list[dict] = []

    if args.fallback_faiss:
        try:
            import faiss as faiss_lib
        except ImportError:
            sys.exit("[error] faiss-cpu が未インストール")
        data_dir = Path(__file__).resolve().parent.parent / "data"
        faiss_index = faiss_lib.read_index(str(data_dir / "index.faiss"))
        faiss_meta = json.loads((data_dir / "index_meta.json").read_text(encoding="utf-8"))
    else:
        if not args.search_endpoint:
            sys.exit("[error] --search-endpoint が未設定")
        search_client = SearchClient(
            endpoint=args.search_endpoint,
            index_name=args.index_name,
            credential=DefaultAzureCredential(),
        )

    # per-language 集計
    lang_scores: dict[str, dict[str, list[float]]] = {}

    for q in queries:
        query_text = q.get("query", "")
        lang = q.get("lang", "unknown")
        relevant_ids: set[str] = set(q.get("relevant_ids", []))

        if not query_text.strip():
            continue

        if args.fallback_faiss:
            retrieved = _retrieve_faiss(
                query_text, args.k, faiss_index, faiss_meta,
                aoai_client, args.embed_deployment, args.embed_dim,
            )
        else:
            retrieved = _retrieve_azure(
                query_text, args.k, search_client,
                aoai_client, args.embed_deployment, args.embed_dim,
            )

        ndcg = _ndcg(retrieved, relevant_ids, args.k)
        mrr = _mrr(retrieved, relevant_ids, args.k)
        recall = _recall(retrieved, relevant_ids, args.k)

        if lang not in lang_scores:
            lang_scores[lang] = {"ndcg": [], "mrr": [], "recall": []}
        lang_scores[lang]["ndcg"].append(ndcg)
        lang_scores[lang]["mrr"].append(mrr)
        lang_scores[lang]["recall"].append(recall)

    # 結果表示
    print(f"\n{'言語':<8} {'クエリ数':>8} {'NDCG@k':>8} {'MRR@k':>8} {'Recall@k':>10}")
    print("-" * 50)

    macro_ndcg_all: list[float] = []
    macro_mrr_all: list[float] = []
    macro_recall_all: list[float] = []

    for lang in sorted(lang_scores):
        s = lang_scores[lang]
        n = len(s["ndcg"])
        avg_ndcg = sum(s["ndcg"]) / n
        avg_mrr = sum(s["mrr"]) / n
        avg_recall = sum(s["recall"]) / n
        print(f"{lang:<8} {n:>8} {avg_ndcg:>8.4f} {avg_mrr:>8.4f} {avg_recall:>10.4f}")
        macro_ndcg_all.extend(s["ndcg"])
        macro_mrr_all.extend(s["mrr"])
        macro_recall_all.extend(s["recall"])

    print("-" * 50)
    total = len(macro_ndcg_all)
    macro_ndcg = sum(macro_ndcg_all) / total if total else 0.0
    macro_mrr = sum(macro_mrr_all) / total if total else 0.0
    macro_recall = sum(macro_recall_all) / total if total else 0.0
    print(f"{'macro':<8} {total:>8} {macro_ndcg:>8.4f} {macro_mrr:>8.4f} {macro_recall:>10.4f}")
    print(f"\n評価カットオフ: k={args.k}")
    print(f"合格しきい値 (デモ): macro NDCG@{args.k} >= {PASS_THRESHOLD_NDCG}")
    if macro_ndcg >= PASS_THRESHOLD_NDCG:
        print(f"[PASS] macro NDCG@{args.k} = {macro_ndcg:.4f} >= {PASS_THRESHOLD_NDCG}")
    else:
        print(f"[FAIL] macro NDCG@{args.k} = {macro_ndcg:.4f} < {PASS_THRESHOLD_NDCG}")
    print()
    print("注意: このしきい値はデモ用の目安です。")
    print("実運用適用には、ドメイン特化の relevance judgments による評価が必須です。")


if __name__ == "__main__":
    main()
