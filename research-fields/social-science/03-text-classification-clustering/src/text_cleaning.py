"""Text cleaning utilities.

We intentionally keep preprocessing minimal because Embedding-3 handles
raw Japanese text well. Only Unicode normalization + optional URL/mention
masking + whitespace tidying is applied. Do NOT tokenize / stem / lowercase
before embedding.
"""
from __future__ import annotations

import re
import unicodedata

URL_RE = re.compile(r"https?://\S+")
MENTION_RE = re.compile(r"@[A-Za-z0-9_]+")
WS_RE = re.compile(r"[ \t\u3000]+")


def clean_for_embedding(text: str, mask_urls: bool = True, mask_mentions: bool = True) -> str:
    """Normalize Japanese text for embedding.

    - Unicode NFKC (半角/全角の整合、合字の展開)
    - Optional URL / mention masking (retains signal via placeholder)
    - Whitespace collapse
    - Strip leading/trailing whitespace only; preserve internal newlines
    """
    if text is None:
        return ""
    t = unicodedata.normalize("NFKC", str(text))
    if mask_urls:
        t = URL_RE.sub("<URL>", t)
    if mask_mentions:
        t = MENTION_RE.sub("<USER>", t)
    # Collapse runs of spaces / tabs but keep newlines
    lines = [WS_RE.sub(" ", line).strip() for line in t.splitlines()]
    return "\n".join(line for line in lines if line)
