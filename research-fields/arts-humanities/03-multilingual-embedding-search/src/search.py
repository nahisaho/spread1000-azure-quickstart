"""任意言語のクエリで多言語インデックスを検索。

デフォルト: Azure AI Search (ベクトル検索 + BM25 ハイブリッド)
--fallback-faiss: ローカル FAISS フォールバック

使用例:
    # Azure AI Search:
    python src/search.py --query "紫式部の物語" --k 5

    # FAISS フォールバック:
    python src/search.py --query "紫式部の物語" --fallback-faiss
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from openai import AzureOpenAI

MAX_QUERY_CHARS = 4096
DEFAULT_MAX_K = 50


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="多言語インデックス検索")
    ap.add_argument("--query", required=True, help="検索クエリ (任意の言語)")
    ap.add_argument(
        "--k",
        type=int,
        default=5,
        help=f"取得件数 [1-{DEFAULT_MAX_K}] (デフォルト: 5)",
    )
    ap.add_argument(
        "--max-k",
        type=int,
        default=DEFAULT_MAX_K,
        help=f"k の最大値 (デフォルト: {DEFAULT_MAX_K})",
    )
    ap.add_argument(
        "--search-endpoint",
        default=os.environ.get("AZURE_SEARCH_ENDPOINT", ""),
        help="Azure AI Search エンドポイント",
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
        help="埋め込み次元数 (デフォルト: 3072)",
    )
    ap.add_argument(
        "--hybrid",
        action="store_true",
        default=True,
        help="BM25 + ベクトルのハイブリッド検索 (デフォルト: 有効)",
    )
    ap.add_argument(
        "--no-hybrid",
        dest="hybrid",
        action="store_false",
        help="ベクトル検索のみ (BM25 なし)",
    )
    ap.add_argument(
        "--fallback-faiss",
        action="store_true",
        help="Azure AI Search の代わりにローカル FAISS を使用",
    )
    return ap.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    if not args.query.strip():
        sys.exit("[error] クエリが空白のみです。検索文字列を指定してください。")
    if len(args.query) > MAX_QUERY_CHARS:
        sys.exit(
            f"[error] クエリが長すぎます: {len(args.query)} 文字 > 上限 {MAX_QUERY_CHARS} 文字"
        )
    if args.k < 1 or args.k > args.max_k:
        sys.exit(f"[error] --k は [1, {args.max_k}] の範囲で指定してください (指定値: {args.k})")
    if not args.fallback_faiss and not args.search_endpoint:
        sys.exit(
            "[error] --search-endpoint (or AZURE_SEARCH_ENDPOINT) が未設定。\n"
            "  FAISS を使う場合は --fallback-faiss を指定してください。"
        )


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


def _embed_query(client: AzureOpenAI, query: str, deployment: str, dim: int) -> list[float]:
    kwargs: dict[str, Any] = {"model": deployment, "input": [query]}
    if dim != 3072:
        kwargs["dimensions"] = dim
    resp = client.embeddings.create(**kwargs)
    return resp.data[0].embedding


def _search_azure(args: argparse.Namespace) -> None:
    aoai_client = _make_aoai_client()
    qvec = _embed_query(aoai_client, args.query, args.embed_deployment, args.embed_dim)

    credential = DefaultAzureCredential()
    search_client = SearchClient(
        endpoint=args.search_endpoint,
        index_name=args.index_name,
        credential=credential,
    )

    vector_query = VectorizedQuery(
        vector=qvec,
        k_nearest_neighbors=args.k,
        fields="content_vector",
    )

    search_kwargs: dict[str, Any] = {
        "search_text": args.query if args.hybrid else None,
        "vector_queries": [vector_query],
        "select": ["id", "lang", "text"],
        "top": args.k,
    }

    results = search_client.search(**search_kwargs)

    print(f"\nクエリ: {args.query!r}  (mode: {'hybrid' if args.hybrid else 'vector'})\n")
    print(f"{'順位':>3} {'スコア':>8} {'ID':<8} {'言語':<4} テキスト")
    print("-" * 100)
    for rank, result in enumerate(results, 1):
        score = result.get("@search.score", 0.0)
        doc_id = result.get("id", "")
        lang = result.get("lang", "")
        text = result.get("text", "")
        if len(text) > 80:
            text = text[:77] + "..."
        print(f"{rank:>3} {score:>8.4f} {doc_id:<8} {lang:<4} {text}")


def _search_faiss(args: argparse.Namespace) -> None:
    """FAISS ローカルフォールバック検索。"""
    try:
        import faiss
        import numpy as np
    except ImportError:
        sys.exit("[error] faiss-cpu / numpy が未インストール。pip install faiss-cpu numpy")

    data_dir = Path(__file__).resolve().parent.parent / "data"
    index_path = data_dir / "index.faiss"
    meta_path = data_dir / "index_meta.json"

    if not index_path.exists():
        sys.exit(
            "[error] FAISS インデックスが未作成。"
            "先に python src/build_index.py --fallback-faiss を実行してください。"
        )
    if not meta_path.exists():
        sys.exit("[error] index_meta.json が見つかりません")

    index = faiss.read_index(str(index_path))
    meta: list[dict] = json.loads(meta_path.read_text(encoding="utf-8"))

    if index.ntotal == 0:
        sys.exit("[error] FAISS インデックスが空です")
    if len(meta) != index.ntotal:
        sys.exit(
            f"[error] メタデータ件数 ({len(meta)}) と "
            f"インデックスベクトル数 ({index.ntotal}) が一致しません"
        )

    # k を ntotal に制限 (FAISS は k > ntotal で -1 ID を返す)
    k = min(args.k, index.ntotal)
    if k < args.k:
        print(f"[warn] --k={args.k} > インデックス件数 {index.ntotal}。k={k} で検索します。")

    aoai_client = _make_aoai_client()
    qvec = _embed_query(aoai_client, args.query, args.embed_deployment, args.embed_dim)

    expected_dim = index.d
    if len(qvec) != expected_dim:
        sys.exit(
            f"[error] 埋め込み次元数が一致しません: "
            f"クエリ={len(qvec)}, インデックス={expected_dim}"
        )

    qvec_np = np.array([qvec], dtype=np.float32)
    faiss.normalize_L2(qvec_np)

    scores, ids = index.search(qvec_np, k)

    print(f"\nクエリ: {args.query!r}  (FAISS fallback)\n")
    print(f"{'順位':>3} {'スコア':>8} {'ID':<8} {'言語':<4} メタデータ")
    print("-" * 100)
    rank = 0
    for i, s in zip(ids[0], scores[0]):
        if i == -1:
            continue  # FAISS が k > ntotal で返す無効 ID
        if not (0 <= i < len(meta)):
            print(f"[warn] 無効なインデックス ID={i} をスキップ", file=sys.stderr)
            continue
        rank += 1
        m = meta[i]
        doc_id = m.get("id", str(i))
        lang = m.get("lang", "")
        # ハッシュ保存モード (--store-full-text なし) では text フィールドなし
        text_info = m.get("text", f"[sha256: {m.get('text_sha256', '')[:16]}...]")
        if isinstance(text_info, str) and len(text_info) > 80:
            text_info = text_info[:77] + "..."
        print(f"{rank:>3} {s:>8.4f} {doc_id:<8} {lang:<4} {text_info}")


def main() -> None:
    load_dotenv()
    args = _parse_args()
    _validate_args(args)

    if args.fallback_faiss:
        _search_faiss(args)
    else:
        _search_azure(args)


if __name__ == "__main__":
    main()
