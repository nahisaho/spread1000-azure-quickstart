"""Ask gpt-5.4-mini for a short Japanese label per cluster (Structured Outputs).

Usage:
    python src/label_clusters.py \
        --clusters data/output/topic-clusters.json

Outputs:
    data/output/<stem>-labels.json — {cluster_id: {label, summary, confidence}}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aoai_client import make_client, require_env  # noqa: E402


class ClusterLabel(BaseModel):
    label: str = Field(..., description="クラスタを 2〜10 文字の日本語名詞句で表現")
    summary: str = Field(..., description="このクラスタの共通テーマを 30〜80 字で説明")
    confidence: float = Field(..., ge=0.0, le=1.0, description="ラベル妥当性の自己評価 (0.0-1.0)")


SYSTEM_PROMPT = (
    "あなたは日本語テキストクラスタリング結果にラベルを付ける専門家です。"
    "与えられた同一クラスタの代表テキストのみを根拠に、共通テーマを 2〜10 文字の日本語名詞句 (label) と"
    "30〜80 字の説明 (summary) にまとめてください。テキストにない情報を推測しないでください。"
    "共通テーマが弱ければ confidence を 0.3 以下にしてください。"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--clusters", required=True, type=Path,
                   help="Output JSON produced by src/cluster.py")
    p.add_argument("--reasoning-effort", default="low", choices=["low", "medium", "high"])
    p.add_argument("--max-completion-tokens", type=int, default=200)
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    deployment = require_env("AZURE_OPENAI_LABEL_DEPLOYMENT")

    payload = json.loads(args.clusters.read_text())
    examples: dict[str, list[dict]] = payload["cluster_examples"]
    client = make_client()

    labels_out: dict[str, dict] = {}
    for cluster_id, items in examples.items():
        if not items:
            labels_out[cluster_id] = {"label": "(空)", "summary": "メンバーなし", "confidence": 0.0}
            continue
        bullet_texts = "\n".join(f"- {it['text']}" for it in items)
        user_msg = (
            f"以下はクラスタ {cluster_id} の重心近傍テキストです:\n"
            f"{bullet_texts}\n\n"
            "共通テーマの label / summary / confidence を返してください。"
        )
        # GPT-5 series: no temperature; use reasoning_effort + max_completion_tokens.
        completion = client.chat.completions.parse(
            model=deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format=ClusterLabel,
            reasoning_effort=args.reasoning_effort,
            max_completion_tokens=args.max_completion_tokens,
        )
        msg = completion.choices[0].message
        if msg.refusal:
            labels_out[cluster_id] = {"label": "(拒否)", "summary": msg.refusal, "confidence": 0.0}
        else:
            parsed: ClusterLabel = msg.parsed
            labels_out[cluster_id] = parsed.model_dump()
        print(f"[label] cluster {cluster_id}: {labels_out[cluster_id]!r}")

    out_path = args.output or args.clusters.with_name(args.clusters.stem.replace("-clusters", "") + "-labels.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "source_clusters": str(args.clusters),
        "aoai_deployment": deployment,
        "reasoning_effort": args.reasoning_effort,
        "labels": labels_out,
    }, ensure_ascii=False, indent=2))
    print(f"[label] wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
