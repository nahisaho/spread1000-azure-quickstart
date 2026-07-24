"""Prepare databricks-dolly-15k-ja for LoRA fine-tuning.

Downloads the dataset, samples N rows, converts to chat-messages JSONL, and
writes the file. Also emits a small `eval_prompts.json` with fixed prompts for
before/after comparison in `compare.py`.

Usage:
    python src/prepare_data.py \
        --builtin-dataset dolly-ja \
        --dataset-revision 6391034b0126850543299cda071dc6281c31a6fb

    python src/prepare_data.py \
        --dataset my-org/my-dataset \
        --dataset-revision abc123 \
        --data-provenance data/my-dataset.provenance.json

    python src/prepare_data.py --n 100   # smoke-test size (requires one of above)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_SYSTEM = "あなたは丁寧で正確な日本語アシスタントです。"

# Built-in dataset aliases and their provenance
_BUILTIN_DATASETS: dict[str, dict] = {
    "dolly-ja": {
        "hf_id": "kunishou/databricks-dolly-15k-ja",
        "provenance": {
            "source": "kunishou/databricks-dolly-15k-ja on HuggingFace Hub; "
                      "derived from databricks/databricks-dolly-15k (CC BY-SA 3.0) "
                      "translated to Japanese.",
            "license": "CC BY-SA 3.0",
            "purpose": "Instruction-following fine-tuning for Japanese language models.",
            "lawful_basis": "Publicly released under CC BY-SA 3.0 license.",
            "contains_user_text": False,
            "pii_reviewed": True,
            "content_safety_reviewed": True,
        },
    },
}

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

_PROVENANCE_REQUIRED_KEYS = frozenset([
    "source", "license", "purpose", "lawful_basis",
    "contains_user_text", "pii_reviewed", "content_safety_reviewed",
])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # Dataset source (exactly one of --builtin-dataset or --dataset required)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--builtin-dataset", choices=list(_BUILTIN_DATASETS.keys()),
                       help="Use a pre-approved built-in dataset alias.")
    group.add_argument("--dataset",
                       help="HuggingFace dataset ID for custom data.")
    p.add_argument("--dataset-revision", required=True,
                   help="Pinned dataset commit SHA (required for reproducibility).")
    p.add_argument("--data-provenance", type=Path, default=None,
                   help="Path to provenance sidecar JSON (required for --dataset).")
    p.add_argument("--n", type=int, default=1000,
                   help="Number of samples to keep (default 1000)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output", type=Path, default=Path("data/train.jsonl"))
    p.add_argument("--eval-output", type=Path, default=Path("data/eval_prompts.json"))
    return p.parse_args()


def _resolve_dataset_and_provenance(args: argparse.Namespace) -> tuple[str, dict]:
    """Return (hf_dataset_id, provenance_dict). Fails if provenance is missing."""
    if args.builtin_dataset:
        info = _BUILTIN_DATASETS[args.builtin_dataset]
        return info["hf_id"], info["provenance"]

    # Custom dataset — require provenance sidecar
    if args.data_provenance is None:
        raise SystemExit(
            "[error] --dataset requires --data-provenance <path-to-provenance.json>.\n"
            "Create a JSON file with fields: "
            + ", ".join(sorted(_PROVENANCE_REQUIRED_KEYS))
            + "\n"
            "See docs/07-ethics-and-limits.md for guidance on data governance."
        )
    if not args.data_provenance.exists():
        raise SystemExit(
            f"[error] provenance sidecar not found: {args.data_provenance}\n"
            "Create it before running data preparation. "
            "See docs/07-ethics-and-limits.md."
        )
    try:
        provenance = json.loads(args.data_provenance.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"[error] cannot read provenance sidecar: {exc}")

    missing = _PROVENANCE_REQUIRED_KEYS - set(provenance.keys())
    if missing:
        raise SystemExit(
            f"[error] provenance sidecar missing required fields: {sorted(missing)}\n"
            "See docs/07-ethics-and-limits.md."
        )
    return args.dataset, provenance


def format_sample(example: dict) -> dict:
    """Map dolly-ja fields into TRL prompt/completion (conversational) format."""
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

    dataset_id, provenance = _resolve_dataset_and_provenance(args)
    print(f"[data] dataset: {dataset_id} @ {args.dataset_revision}")
    print(f"[data] license: {provenance.get('license', 'unknown')}")
    if provenance.get("contains_user_text"):
        print("[data] WARNING: provenance indicates this dataset contains user text. "
              "Ensure PII review is complete before training.", file=sys.stderr)

    print(f"[data] loading {dataset_id} …")
    ds = load_dataset(dataset_id, revision=args.dataset_revision, split="train")
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
                continue
            f.write(json.dumps(formatted, ensure_ascii=False) + "\n")
            kept += 1
    print(f"[data] wrote {kept} prompt/completion samples → {args.output}")

    # Save provenance alongside output for traceability
    prov_out = args.output.with_suffix(".provenance.json")
    prov_out.write_text(
        json.dumps({
            "dataset_id": dataset_id,
            "dataset_revision": args.dataset_revision,
            "n_samples": kept,
            "seed": args.seed,
            **provenance,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[data] wrote provenance → {prov_out}")

    args.eval_output.parent.mkdir(parents=True, exist_ok=True)
    with args.eval_output.open("w", encoding="utf-8") as f:
        json.dump(EVAL_PROMPTS, f, ensure_ascii=False, indent=2)
    print(f"[data] wrote {len(EVAL_PROMPTS)} eval prompts → {args.eval_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
