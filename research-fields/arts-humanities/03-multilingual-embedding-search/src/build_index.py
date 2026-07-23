"""多言語コーパスを Azure OpenAI text-embedding-3-large で埋め込み、
FAISS インデックスに保存する。
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from openai import AzureOpenAI

from corpus import CORPUS


def main() -> None:
    load_dotenv()
    for v in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY", "AZURE_OPENAI_EMBED_DEPLOYMENT"):
        if not os.environ.get(v):
            sys.exit(f"[error] {v} not set (see .env.example)")

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )
    deployment = os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"]

    print(f"[embed] embedding {len(CORPUS)} docs with {deployment}")
    texts = [d["text"] for d in CORPUS]
    resp = client.embeddings.create(model=deployment, input=texts)
    vectors = np.array([e.embedding for e in resp.data], dtype=np.float32)
    print(f"[embed] shape={vectors.shape}")

    # L2 normalize → inner product ≈ cosine similarity
    faiss.normalize_L2(vectors)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    faiss.write_index(index, str(data_dir / "index.faiss"))
    meta = [{"id": d["id"], "lang": d["lang"], "text": d["text"]} for d in CORPUS]
    (data_dir / "index_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] wrote data/index.faiss ({index.ntotal} vectors, dim={dim})")


if __name__ == "__main__":
    main()
