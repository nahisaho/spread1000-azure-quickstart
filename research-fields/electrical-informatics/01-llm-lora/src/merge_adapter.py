"""Merge a LoRA adapter into the base model and save as a standalone fp16 model.

Refuses to merge quantized (4-bit) models; use a fp16 base load instead.

Usage:
    python src/merge_adapter.py \
        --adapter data/adapter/final \
        --output data/merged_model/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--adapter", type=Path, required=True,
                   help="Path to LoRA adapter directory (e.g. data/adapter/final)")
    p.add_argument("--output", type=Path, required=True,
                   help="Output directory for the merged model")
    p.add_argument("--model", default=None,
                   help="Base model ID. If omitted, read from adapter_config.json.")
    p.add_argument("--model-revision", default=None,
                   help="Pinned Git revision (commit SHA) for the base model.")
    p.add_argument("--trust-remote-code", action="store_true",
                   help="Allow remote code in model repo. Off by default.")
    return p.parse_args()


def resolve_base_model(adapter_dir: Path, cli_model: str | None) -> str:
    if cli_model:
        return cli_model
    cfg = adapter_dir / "adapter_config.json"
    if cfg.exists():
        data = json.loads(cfg.read_text(encoding="utf-8"))
        base = data.get("base_model_name_or_path")
        if base:
            return base
    raise SystemExit(
        f"[error] cannot determine base model. Pass --model or ensure "
        f"{cfg} contains 'base_model_name_or_path'."
    )


def main() -> int:
    args = parse_args()

    if not args.adapter.exists():
        print(f"[error] adapter directory not found: {args.adapter}", file=sys.stderr)
        return 1

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base_model_id = resolve_base_model(args.adapter, args.model)
    revision = args.model_revision

    print(f"[merge] base model: {base_model_id}" + (f" @ {revision}" if revision else ""))
    print(f"[merge] adapter:    {args.adapter}")
    print(f"[merge] output:     {args.output}")

    load_kwargs: dict = {
        "torch_dtype": torch.float16,
        "device_map": "cpu",
        "trust_remote_code": args.trust_remote_code,
    }
    if revision:
        load_kwargs["revision"] = revision

    print("[merge] loading base model in fp16 on CPU …")
    base = AutoModelForCausalLM.from_pretrained(base_model_id, **load_kwargs)

    if getattr(base, "is_loaded_in_4bit", False) or getattr(base, "is_loaded_in_8bit", False):
        print(
            "[error] base model is quantized. Merge requires a non-quantized fp16 load. "
            "Re-run without quantization flags.",
            file=sys.stderr,
        )
        return 1

    print("[merge] attaching LoRA adapter …")
    model = PeftModel.from_pretrained(
        base, str(args.adapter),
        is_trainable=False,
    )

    print("[merge] merging adapter weights (safe_merge=True) …")
    merged = model.merge_and_unload(safe_merge=True)

    args.output.mkdir(parents=True, exist_ok=True)
    print(f"[merge] saving merged model → {args.output}")
    merged.save_pretrained(str(args.output), safe_serialization=True)

    tokenizer = AutoTokenizer.from_pretrained(
        str(args.adapter),
        trust_remote_code=args.trust_remote_code,
    )
    tokenizer.save_pretrained(str(args.output))
    print(f"[merge] tokenizer saved → {args.output}")
    print("[merge] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
