"""Optionally regenerate synthetic Japanese short texts via gpt-5.4-mini.

The repository already ships hand-curated CC0 synthetic CSVs under data/.
Only run this script if you want to *expand* or *regenerate* the dataset.

Usage:
    python scripts/generate_synthetic_texts.py --task sentiment --n-per-class 20
    python scripts/generate_synthetic_texts.py --task topic --n-per-class 15
    python scripts/generate_synthetic_texts.py --task disinformation --n-per-class 20

Output: appends to data/synthetic_<task>.csv (or writes if missing),
        updates data/manifest.json with generation provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aoai_client import make_client, require_env  # noqa: E402

TASKS: dict[str, dict] = {
    "sentiment": {
        "classes": ["positive", "negative", "neutral"],
        "instruction": (
            "以下は日本国内の観光地・宿泊・飲食に関する架空のレビュー文です。"
            "指定されたクラス ({label}) の感情を持つ 30〜80 字の日本語短文を、"
            "口語と敬体を混ぜて生成してください。実在の地名・店名・人名を使わないでください。"
        ),
    },
    "topic": {
        "classes": ["観光", "食事", "宿泊", "交通"],
        "instruction": (
            "以下は架空の旅行日記の断片です。指定されたトピック ({label}) について、"
            "30〜80 字の日本語で書いてください。実在の地名・店名を使わず、他のトピックが混ざらないように。"
        ),
    },
    "disinformation": {
        "classes": ["fact", "misinformation"],
        "instruction": (
            "以下は SNS 上の短い投稿を模した架空の日本語文です。"
            "指定ラベル ({label}) が 'fact' なら誰でも検証可能な自明な事実 (例: 一般常識、確立した科学) を、"
            "'misinformation' なら典型的な誤情報パターン (例: 根拠なき因果、陰謀論的表現) を"
            "30〜80 字で 1 文だけ書いてください。実在の人物名・組織名は使わないでください。"
            "misinformation の場合も研究教育目的の架空例であり、実害を与える具体的助言 (医療投薬量など) は避けてください。"
        ),
    },
}


class SyntheticText(BaseModel):
    text: str = Field(..., description="生成された日本語短文 (30〜80 字)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--task", required=True, choices=list(TASKS.keys()))
    p.add_argument("--n-per-class", type=int, default=15)
    p.add_argument("--out-dir", type=Path, default=Path("data"))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    deployment = require_env("AZURE_OPENAI_LABEL_DEPLOYMENT")
    client = make_client()
    conf = TASKS[args.task]

    rows: list[dict] = []
    for label in conf["classes"]:
        for _ in range(args.n_per_class):
            prompt = conf["instruction"].format(label=label)
            completion = client.chat.completions.parse(
                model=deployment,
                messages=[
                    {"role": "system", "content": "架空データ生成用途。実在情報や個人特定情報は含めない。"},
                    {"role": "user", "content": prompt},
                ],
                response_format=SyntheticText,
                reasoning_effort="low",
                max_completion_tokens=200,
            )
            msg = completion.choices[0].message
            if msg.refusal:
                print(f"[gen] refusal on {label}: {msg.refusal}", file=sys.stderr)
                continue
            rows.append({
                "id": uuid.uuid4().hex[:12],
                "label": label,
                "text": msg.parsed.text.strip(),
                "synthetic": True,
                "generator_model": "gpt-5.4-mini",
                "generator_version": "2026-03-17",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
            print(f"[gen] {label}: {rows[-1]['text']}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = args.out_dir / f"synthetic_{args.task}.csv"
    new_df = pd.DataFrame(rows)
    if out_csv.exists():
        existing = pd.read_csv(out_csv)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_csv(out_csv, index=False)
    print(f"[gen] wrote {out_csv} ({len(combined)} rows total)")

    manifest_path = args.out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest.setdefault("runs", []).append({
        "task": args.task,
        "n_new_rows": len(rows),
        "generator_model": "gpt-5.4-mini",
        "generator_version": "2026-03-17",
        "csv_sha256_16": hashlib.sha256(out_csv.read_bytes()).hexdigest()[:16],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"[gen] updated {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
