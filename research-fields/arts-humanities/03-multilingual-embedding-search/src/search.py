"""任意言語のクエリで多言語 FAISS インデックスを検索"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from openai import AzureOpenAI


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True, help="検索クエリ (任意の言語)")
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    load_dotenv()
    data_dir = Path(__file__).resolve().parent.parent / "data"
    if not (data_dir / "index.faiss").exists():
        sys.exit("[error] インデックスが未作成。先に python src/build_index.py を実行")

    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )
    deployment = os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"]

    resp = client.embeddings.create(model=deployment, input=[args.query])
    qvec = np.array([resp.data[0].embedding], dtype=np.float32)
    faiss.normalize_L2(qvec)

    index = faiss.read_index(str(data_dir / "index.faiss"))
    meta = json.loads((data_dir / "index_meta.json").read_text(encoding="utf-8"))

    scores, ids = index.search(qvec, args.k)
    print(f"\nクエリ: {args.query!r}\n")
    print(f"{'順位':>3} {'類似度':>7} {'ID':<6} {'言語':<3} テキスト")
    print("-" * 90)
    for rank, (i, s) in enumerate(zip(ids[0], scores[0]), 1):
        m = meta[i]
        print(f"{rank:>3} {s:>7.4f} {m['id']:<6} {m['lang']:<3} {m['text']}")


if __name__ == "__main__":
    main()
