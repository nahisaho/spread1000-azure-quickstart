"""Prepare databricks-dolly-15k-ja for LoRA fine-tuning.

Downloads the dataset, samples N rows, converts to chat-messages JSONL, and
writes the file. Also emits a small `eval_prompts.json` with fixed prompts for
before/after comparison in `compare.py`.

Usage:
    python src/prepare_data.py                          # 1000 samples, seed 42
    python src/prepare_data.py --n 100                  # smoke-test size
    python src/prepare_data.py --output data/train.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_SYSTEM = "あなたは丁寧で正確な日本語アシスタントです。"

EVAL_PROMPTS = [
    "研究論文の要約を書くときに気をつけるべき点を 3 つ挙げてください。",
    "教師なし学習と教師あり学習の違いを高校生向けに説明してください。",
    "Python でリスト内包表記が普通の for 文よりも速い理由を教えてください。",
    "Azure と AWS の主要な違いを 5 つ挙げてください。",
    "『粒界』とは何ですか？材料科学の観点から説明してください。",
    "COVID-19 と季節性インフルエンザの症状の違いは？",
    "強化学習における報酬設計の落とし穴を教えてください。",
    "「持続可能性」を科学論文で使う場合の定義を明確化してください。",
    "GPT-4 と Phi-4-mini の想定される用途の違いを教えてください。",
    "Transformer アーキテクチャの Self-Attention の計算量を教えてください。",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--n", type=int, default=1000,
                   help="Number of samples to keep (default 1000)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output", type=Path, default=Path("data/train.jsonl"))
    p.add_argument("--eval-output", type=Path, default=Path("data/eval_prompts.json"))
    p.add_argument("--dataset", default="kunishou/databricks-dolly-15k-ja",
                   help="HuggingFace dataset ID")
    return p.parse_args()


def format_sample(example: dict) -> dict:
    """Map dolly-ja fields into TRL prompt/completion (conversational) format.

    We use TRL's prompt/completion pair rather than a single `messages` field so
    that ``SFTTrainer`` applies **completion-only loss** — i.e. the model is only
    trained to predict the assistant response, not the (already-known) system
    prompt or user instruction. This matches how you would prompt the model at
    inference time and avoids wasting capacity on memorising the input.

    Dolly's ``input``/``context`` field is a *passage* (not a system directive),
    so we concatenate it with the instruction inside the user turn rather than
    promoting it to a system message. This preserves the instruction hierarchy
    (system = fixed persona, user = task + context, assistant = answer).

    Handles both ``context``/``response`` (older dolly-ja) and ``input``/``output``
    (newer mirrors) field naming.
    """
    instruction = example.get("instruction", "").strip()
    ctx = (example.get("input") or example.get("context") or "").strip()
    response = (example.get("output") or example.get("response") or "").strip()

    user_content = f"{instruction}\n\n[参考情報]\n{ctx}" if ctx else instruction
    prompt = [
        {"role": "system", "content": DEFAULT_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    completion = [{"role": "assistant", "content": response}]
    return {"prompt": prompt, "completion": completion}


def main() -> int:
    args = parse_args()

    try:
        from datasets import load_dataset
    except ImportError:
        print("[error] `datasets` not installed. Run: pip install -r requirements-cpu.txt",
              file=sys.stderr)
        return 1

    print(f"[data] loading {args.dataset} …")
    ds = load_dataset(args.dataset, split="train")
    print(f"[data] total rows available: {len(ds)}")

    n = min(args.n, len(ds))
    ds = ds.shuffle(seed=args.seed).select(range(n))
    print(f"[data] sampled {n} rows with seed={args.seed}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with args.output.open("w", encoding="utf-8") as f:
        for row in ds:
            formatted = format_sample(row)
            if not formatted["prompt"][1]["content"] or not formatted["completion"][0]["content"]:
                continue  # skip rows with empty instruction or response
            f.write(json.dumps(formatted, ensure_ascii=False) + "\n")
            kept += 1
    print(f"[data] wrote {kept} prompt/completion samples → {args.output}")

    args.eval_output.parent.mkdir(parents=True, exist_ok=True)
    with args.eval_output.open("w", encoding="utf-8") as f:
        json.dump(EVAL_PROMPTS, f, ensure_ascii=False, indent=2)
    print(f"[data] wrote {len(EVAL_PROMPTS)} eval prompts → {args.eval_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
