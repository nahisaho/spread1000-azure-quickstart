"""QLoRA supervised fine-tuning (SFT) with `trl.SFTTrainer` and `peft`.

Primary path: Azure ML T4 (NCasT4_v3) + Phi-4-mini-instruct + QLoRA 4-bit + fp16.
Smoke-test path: CPU + Qwen2.5-0.5B-Instruct + LoRA (no quantization).

Usage — GPU (T4):
    python src/train_lora.py --data data/train.jsonl --output data/adapter/

Usage — CPU smoke test (Qwen2.5-0.5B, 100 samples, 1 epoch):
    python src/train_lora.py \\
        --model Qwen/Qwen2.5-0.5B-Instruct \\
        --data data/train.jsonl \\
        --epochs 1 --device cpu --no-quant \\
        --output data/adapter/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", default="microsoft/Phi-4-mini-instruct",
                   help="HuggingFace model ID. Use Qwen/Qwen2.5-0.5B-Instruct for CPU.")
    p.add_argument("--data", type=Path, default=Path("data/train.jsonl"),
                   help="Chat-formatted JSONL from prepare_data.py")
    p.add_argument("--output", type=Path, default=Path("data/adapter/"))
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=2,
                   help="per-device batch size; keep 1-2 on T4 16GB")
    p.add_argument("--grad-accum", type=int, default=4,
                   help="gradient accumulation steps (effective batch = batch-size * grad-accum)")
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--max-seq-length", type=int, default=512)
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=32)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    p.add_argument("--no-quant", action="store_true",
                   help="Disable 4-bit quantization (required for CPU or non-CUDA GPU)")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def resolve_device(pref: str) -> str:
    import torch
    if pref == "cpu":
        return "cpu"
    if pref == "cuda":
        if not torch.cuda.is_available():
            print("[warn] --device cuda requested but no CUDA. Falling back to CPU.",
                  file=sys.stderr)
            return "cpu"
        return "cuda"
    return "cuda" if torch.cuda.is_available() else "cpu"


def main() -> int:
    args = parse_args()
    if not args.data.exists():
        print(f"[error] Data file not found: {args.data}. Run src/prepare_data.py first.",
              file=sys.stderr)
        return 1

    import torch
    from datasets import load_dataset
    from peft import LoraConfig, TaskType
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    device = resolve_device(args.device)
    use_quant = (not args.no_quant) and device == "cuda"
    torch.manual_seed(args.seed)

    # ── 1. Tokenizer ───────────────────────────────────────────────
    print(f"[model] loading tokenizer for {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        # Prefer unk over eos to avoid the well-known bug where the model learns
        # padding == end-of-sequence and never stops generating at inference.
        if tokenizer.unk_token is not None:
            tokenizer.pad_token = tokenizer.unk_token
        else:
            tokenizer.add_special_tokens({"pad_token": "[PAD]"})
    tokenizer.padding_side = "right"

    # ── 2. Model ───────────────────────────────────────────────────
    # Force fp16 dtype throughout on GPU. Phi-4-mini's config declares bf16 by
    # default, but T4 (Turing) has no native bf16 support, so we override.
    model_kwargs: dict = {"trust_remote_code": True}
    if use_quant:
        from transformers import BitsAndBytesConfig
        # QLoRA 4-bit NF4. compute_dtype MUST be float16 on T4 (no bf16 support).
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        model_kwargs["device_map"] = "auto"
        model_kwargs["dtype"] = torch.float16   # override model config default (may be bf16)
    elif device == "cuda":
        model_kwargs["dtype"] = torch.float16
        model_kwargs["device_map"] = "auto"
    else:  # CPU
        model_kwargs["dtype"] = torch.float32

    print(f"[model] loading {args.model} (device={device}, 4-bit={use_quant})")
    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
    if tokenizer.pad_token_id is not None and tokenizer.pad_token_id != model.config.pad_token_id:
        model.config.pad_token_id = tokenizer.pad_token_id

    if not use_quant and device == "cpu":
        # ensure model is on CPU
        model.to("cpu")

    n_params = sum(p.numel() for p in model.parameters())
    print(f"[model] total parameters: {n_params:,}")

    # ── 3. Dataset ─────────────────────────────────────────────────
    print(f"[data] loading {args.data}")
    ds = load_dataset("json", data_files=str(args.data), split="train")
    print(f"[data] {len(ds)} prompt/completion samples")

    # ── 4. LoRA config ─────────────────────────────────────────────
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        # target_modules="all-linear" applies LoRA to every nn.Linear — works for
        # both Phi-4-mini and Qwen2.5 without hardcoding model-specific names.
        target_modules="all-linear",
    )

    # ── 5. Training config ─────────────────────────────────────────
    args.output.mkdir(parents=True, exist_ok=True)
    training_config = SFTConfig(
        output_dir=str(args.output),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        fp16=(device == "cuda"),           # T4: fp16 only, never bf16
        bf16=False,
        gradient_checkpointing=(device == "cuda"),
        logging_steps=25,
        save_strategy="epoch",
        max_length=args.max_seq_length,
        report_to="none",
        seed=args.seed,
    )

    print(f"[train] starting: epochs={args.epochs}, batch={args.batch_size}x{args.grad_accum}, "
          f"lr={args.lr}, LoRA r={args.lora_r}")
    trainer = SFTTrainer(
        model=model,
        args=training_config,
        train_dataset=ds,
        peft_config=lora_config,
        processing_class=tokenizer,
    )

    if device == "cuda":
        # TRL 1.9 auto-casts trainable QLoRA adapter parameters to bf16 when it
        # detects Ampere+. On T4 (Turing, sm_75) there is no native bf16, AND
        # HuggingFace AMP requires master weights in fp32 (GradScaler rejects
        # fp16 gradients). So force every trainable parameter to fp32; the
        # forward/backward runs fp16 via autocast, gradients are unscaled to fp32.
        for _n, p in trainer.model.named_parameters():
            if p.requires_grad and p.dtype != torch.float32:
                p.data = p.data.to(torch.float32)
        bad = [n for n, p in trainer.model.named_parameters()
               if p.requires_grad and p.dtype != torch.float32]
        assert not bad, f"non-fp32 trainable params remain (AMP requires fp32 master weights): {bad[:3]}"

    train_result = trainer.train()

    # ── 6. Save adapter + tokenizer ───────────────────────────────
    final_dir = args.output / "final"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(final_dir)
    print(f"[train] saved LoRA adapter → {final_dir}")

    metrics = {
        "train_runtime_sec": train_result.metrics.get("train_runtime"),
        "train_samples_per_second": train_result.metrics.get("train_samples_per_second"),
        "train_loss": train_result.metrics.get("train_loss"),
        "epochs": args.epochs,
        "n_train_samples": len(ds),
        "model": args.model,
        "device": device,
        "quantized_4bit": use_quant,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
    }
    (args.output / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[train] metrics: {metrics}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
