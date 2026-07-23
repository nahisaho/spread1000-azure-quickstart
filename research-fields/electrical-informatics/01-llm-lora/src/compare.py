"""Compare base model vs LoRA-adapted model on a fixed prompt set.

Loads the base model once, then loads the same base + LoRA adapter, and prints
the two responses side-by-side for each prompt in `eval_prompts.json`.

Usage:
    python src/compare.py --adapter data/adapter/final --prompts data/eval_prompts.json
    python src/compare.py --adapter data/adapter/final --model Qwen/Qwen2.5-0.5B-Instruct \\
        --device cpu --max-new-tokens 200
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--adapter", type=Path, required=True,
                   help="Path to LoRA adapter (e.g. data/adapter/final)")
    p.add_argument("--model", default=None,
                   help="Base model. If omitted, read from adapter_config.json.")
    p.add_argument("--prompts", type=Path, default=Path("data/eval_prompts.json"))
    p.add_argument("--output", type=Path, default=Path("data/comparison.json"))
    p.add_argument("--max-new-tokens", type=int, default=200)
    p.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def resolve_device(pref: str) -> str:
    import torch
    if pref == "cpu":
        return "cpu"
    if pref == "cuda":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


def resolve_base_model(adapter_dir: Path, cli_model: str | None) -> str:
    if cli_model:
        return cli_model
    cfg = adapter_dir / "adapter_config.json"
    if cfg.exists():
        data = json.loads(cfg.read_text(encoding="utf-8"))
        base = data.get("base_model_name_or_path")
        if base:
            return base
    raise SystemExit(f"[error] cannot determine base model. Pass --model or ensure "
                     f"{cfg} contains 'base_model_name_or_path'.")


def generate(model, tokenizer, prompt: str, device: str, max_new_tokens: int) -> str:
    import torch
    messages = [
        {"role": "system", "content": "あなたは丁寧で正確な日本語アシスタントです。"},
        {"role": "user", "content": prompt},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(device)
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,          # deterministic for reproducible comparison
            temperature=1.0,
            pad_token_id=tokenizer.pad_token_id,
        )
    prompt_len = inputs["input_ids"].shape[1]
    generated = output_ids[0, prompt_len:]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def main() -> int:
    args = parse_args()
    if not args.adapter.exists():
        print(f"[error] adapter dir not found: {args.adapter}", file=sys.stderr)
        return 1
    if not args.prompts.exists():
        print(f"[error] prompts file not found: {args.prompts}", file=sys.stderr)
        return 1

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base_model_id = resolve_base_model(args.adapter, args.model)
    device = resolve_device(args.device)
    torch.manual_seed(args.seed)

    print(f"[compare] base model: {base_model_id}")
    print(f"[compare] adapter:    {args.adapter}")
    print(f"[compare] device:     {device}")

    tokenizer = AutoTokenizer.from_pretrained(args.adapter, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.unk_token or tokenizer.eos_token

    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"[compare] loading base model (device={device}, dtype={dtype}) …")
    base = AutoModelForCausalLM.from_pretrained(
        base_model_id, torch_dtype=dtype, trust_remote_code=True,
        device_map=None,
    ).to(device)
    base.eval()

    print(f"[compare] attaching LoRA adapter …")
    lora = PeftModel.from_pretrained(base, str(args.adapter))
    lora.eval()

    prompts = json.loads(args.prompts.read_text(encoding="utf-8"))
    results: list[dict] = []
    for i, prompt in enumerate(prompts, 1):
        print(f"\n{'=' * 70}\n[{i}/{len(prompts)}] {prompt}\n{'=' * 70}")

        # Base = disable adapter; LoRA = enable
        with lora.disable_adapter():
            base_out = generate(lora, tokenizer, prompt, device, args.max_new_tokens)
        lora_out = generate(lora, tokenizer, prompt, device, args.max_new_tokens)

        print(f"\n--- Base ({base_model_id}) ---\n{base_out}")
        print(f"\n--- LoRA-adapted ---\n{lora_out}")
        results.append({"prompt": prompt, "base": base_out, "lora": lora_out})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[compare] wrote {len(results)} paired responses → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
